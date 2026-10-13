#!/usr/bin/env python3
"""Per-camera clips for the 3D camera-rig view: for every CTVS scene, model and static camera, one short mp4 over all timestamps (observed frame on the diagonal), plus the input sweep clip and a manifest."""
import glob, json, os, re, shutil, subprocess, sys, tempfile
WANT = set()
import numpy as np
from PIL import Image

B = "/home/cvlab20/project/eunbeen/ssd_symlink/sde/eunbeen/baseline_evals_res"
NV = "/mnt/nvme1n1/eunbeen/eval"
CLIPS = "/home/cvlab20/project/eunbeen/supp_html/clips"
MANIFEST = "/home/cvlab20/project/eunbeen/supp_html/scene_manifest.json"
N3DV_CACHE = "/mnt/sde/eunbeen/baseline_evals/n3dv/_frame_cache"
OUT = "/home/cvlab20/project/eunbeen/FL4N_project_page/static/videos/rig"
FPS = {"nvidia": 4, "kubric4d": 3, "camxtime": 3, "charge": 3, "n3dv": 4}
CELL_W = 360
MODELS = ["ours", "c4g", "neoverse", "movies", "4dgt"]
NVIDIA_ROOT = "/mnt/sde/eunbeen/data/NVIDIA_x/NVIDIA"
CAMX_ROOT = "/mnt/sde/eunbeen/data/CamxTime_x/CamxTime"
FNAME_RE = re.compile(r"^v(.+)_f(\d+)\.png$")
C4G_RE = re.compile(r"^all_(\d+)_i\d+_f(\d+)\.png$")


def pred_dir(ds, scene, model):
    if ds == "n3dv":
        return {"ours": f"{NV}/n3dv_ctvs_vggt/n3dv/ours_posed_vggt", "c4g": f"{NV}/n3dv_new_protocol/ctvs/n3dv/n3dv/c4g_lbgt",
                "movies": f"{NV}/n3dv_new_protocol/ctvs/n3dv/n3dv/movies", "4dgt": f"{NV}/n3dv_new_protocol/ctvs/n3dv/n3dv/4dgt",
                "neoverse": f"{NV}/neo_ttotgt_all/ctvs/n3dv/n3dv/neoverse_ttotgt"}[model] + f"/{scene}/pred"
    d = {"ours": "ours_posed", "c4g": "c4g_lbgt", "neoverse": "neoverse_tto_nostatic", "movies": "movies", "4dgt": "4dgt"}[model]
    return f"{B}/ctvs/{ds}/{ds}/{d}/{scene}/pred"


def index_preds(d):
    out = {}
    for f in os.listdir(d):
        m = FNAME_RE.match(f) or C4G_RE.match(f)
        if m:
            out.setdefault(m.group(1), {})[int(m.group(2))] = f"{d}/{f}"
    return out


def inputs(ds, scene, tmp):
    if ds == "n3dv":
        z = np.load(sorted(glob.glob(f"{N3DV_CACHE}/{scene}_1014x1352_*c_*.npz"))[-1])
        return [Image.fromarray(a) for a in z["cond"]]
    if not os.path.exists(f"{CLIPS}/ctvs_{ds}_{scene}__inp.mp4"):
        return None
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{CLIPS}/ctvs_{ds}_{scene}__inp.mp4", f"{tmp}/inp_%03d.png"], check=True)
    return [Image.open(f"{tmp}/{f}").convert("RGB") for f in sorted(os.listdir(tmp)) if f.startswith("inp_")]


def gt_provider(ds, scene, views, frames):
    """Return f(view, frame) -> PIL image of the ground truth, or None when the dataset is unavailable."""
    if ds == "n3dv":
        z = np.load(sorted(glob.glob(f"{N3DV_CACHE}/{scene}_1014x1352_*c_*.npz"))[-1])
        cams = [int(v) for v in views]
        order = {}
        i = 0
        for ci, cam in enumerate(cams):
            own = frames[ci]
            for t in frames:
                if t != own:
                    order[(f"{cam:02d}", t)] = i
                    i += 1
        tr = z["transport"]
        assert len(tr) == len(order), (len(tr), len(order))
        return lambda v, f: Image.fromarray(tr[order[(v, f)]])
    if ds == "nvidia":
        root = f"{NVIDIA_ROOT}/{scene}/multiview_GT"
        if not os.path.isdir(root):
            return None
        return lambda v, f: Image.open(f"{root}/{f + 1:08d}/cam{int(v) + 1:02d}.jpg").convert("RGB")
    if ds == "camxtime":
        tdir = f"{CAMX_ROOT}/{scene}/camera-trajectory-01"
        if not os.path.isdir(tdir):
            return None
        import cv2
        nums = sorted(int(f[3:6]) for f in os.listdir(tdir) if f.startswith("cam") and f.endswith("_full_motion.mp4"))
        cache = {}
        def read(v, f):
            cap = cv2.VideoCapture(f"{tdir}/cam{nums[int(v)]:03d}_full_motion.mp4")
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(f))
            ok, bgr = cap.read()
            cap.release()
            assert ok, (scene, v, f)
            return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        return read
    return None


def small(im):
    return np.asarray(im.resize((64, 36), Image.BILINEAR), dtype=np.float32)


def encode(frames, path, fps):
    if os.path.exists(path):
        return
    tmp = tempfile.mkdtemp()
    for i, im in enumerate(frames):
        im.save(f"{tmp}/f_{i:03d}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", f"{tmp}/f_%03d.png", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], check=True)
    shutil.rmtree(tmp)


def build(ds, scene):
    tmp = tempfile.mkdtemp()
    ours = index_preds(pred_dir(ds, scene, "ours"))
    views = sorted(ours)
    frames = sorted(set(fr for v in views for fr in ours[v]))
    diag = {v: next(fr for fr in frames if fr not in ours[v]) for v in views}
    inps = inputs(ds, scene, tmp)
    if inps is None:
        g = gt_provider(ds, scene, views, frames)
        inps = [g(v, diag[v]).convert("RGB") for v in views]
        v2inp = {v: i for i, v in enumerate(views)}
    else:
        assert len(inps) == len(views), (scene, len(inps), len(views))
        sig = {v: np.mean([small(Image.open(ours[v][f])) for f in list(ours[v])[:3]], axis=0) for v in views}
        v2inp, used = {}, set()
        for i, im in enumerate(inps):
            s = small(im)
            best = min((v for v in views if v not in used), key=lambda v: np.abs(sig[v] - s).mean())
            v2inp[best], used = i, used | {best}
    w0, h0 = Image.open(next(iter(ours[views[0]].values()))).size
    cw, ch = CELL_W, round(CELL_W * h0 / w0 / 2) * 2
    fit = lambda im: im.resize((cw, ch), Image.LANCZOS)
    base = f"{OUT}/{ds}_{scene}"
    order = sorted(views, key=lambda v: diag[v])
    encode([fit(inps[v2inp[v]]) for v in order], f"{base}__input.mp4", FPS[ds])
    fit(inps[v2inp[order[0]]]).save(f"{base}__input.jpg", quality=80)
    gt = gt_provider(ds, scene, views, frames) if "gt" in WANT else None
    for model in (["gt"] if gt else []) + [m for m in MODELS if m in WANT]:
        if model != "gt":
            pd = pred_dir(ds, scene, model)
            preds = index_preds(pd) if os.path.isdir(pd) else {}
            if ds == "n3dv" and model == "c4g":
                preds = {f"{int(k):02d}": v for k, v in preds.items()}
        miss = 0
        for k, v in enumerate(views):
            out = f"{base}__{model}__c{k:02d}.mp4"
            if os.path.exists(out):
                continue
            seq = []
            for fr in frames:
                if fr == diag[v]:
                    seq.append(fit(inps[v2inp[v]]))
                elif model == "gt":
                    seq.append(fit(gt(v, fr)))
                elif fr in preds.get(v, {}):
                    seq.append(fit(Image.open(preds[v][fr]).convert("RGB")))
                else:
                    miss += 1
                    seq.append(Image.new("RGB", (cw, ch), (40, 40, 48)))
            encode(seq, out, FPS[ds])
        if miss:
            print(f"  {model}: {miss} missing frames")
    shutil.rmtree(tmp)
    entry = {"ds": ds, "id": scene, "cams": len(views), "frames": len(frames), "fps": FPS[ds], "w": cw, "h": ch,
             "input_cam": [order.index(v) for v in views], "gt": bool(gt) or os.path.exists(f"{base}__gt__c00.mp4")}
    print(f"{ds}/{scene}: {len(views)} cams x {len(frames)} frames, cell {cw}x{ch}", flush=True)
    return entry


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    WANT = set(MODELS + ["gt"])
    for a in args:
        if a.startswith("--only="):
            WANT = set(a[len("--only="):].split(","))
    only = [a for a in args if not a.startswith("--")]
    entries = [e for e in json.load(open(MANIFEST)) if e["protocol"] == "ctvs" and e["dataset"] in FPS and (not only or e["dataset"] in only)]
    for a in args:
        if a.startswith("--scenes="):
            entries = [{"dataset": x.split(":")[0], "scene": x.split(":")[1]} for x in a[len("--scenes="):].split(",")]
    mp = f"{OUT}/manifest.json"
    for e in entries:
        entry = build(e["dataset"], e["scene"])
        old = json.load(open(mp)) if os.path.exists(mp) else {}
        old[f"{e['dataset']}_{e['scene']}"] = entry
        json.dump(old, open(mp + ".tmp", "w"), indent=1)
        os.replace(mp + ".tmp", mp)
