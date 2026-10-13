"""Export view x time CTVS matrices (all models + GT) for the explorer as small webps; NVIDIA keeps the 8 view/time indices where FL4N scores best, CamxTime scenes are listed in CAMX."""
import os, re, json, shutil
import numpy as np
import cv2
from PIL import Image

B = "/home/cvlab20/project/eunbeen/ssd_symlink/sde/eunbeen/baseline_evals_res/ctvs"
GT_NV = "/mnt/sde/eunbeen/data/NVIDIA_x/NVIDIA"
GT_CX = "/mnt/sde/eunbeen/data/CamxTime_x/CamxTime"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "figures", "teaser")
MODELS = {"ours": "ours_posed", "4dgt": "4dgt", "movies": "movies", "neoverse": "neoverse_tto_nostatic", "c4g": "c4g_lbgt"}
NAMES = {"Teadybear": "Teddy bear", "DynamicFace": "Dynamic face"}
CAMX = ["Scene403", "Scene410", "Scene384"]
W, KEEP = 320, 8
C4G_RE = re.compile(r"^all_(\d+)_i\d+_f(\d+)\.png$")


def pred_path(ds, key, scene, v, f):
    d = f"{B}/{ds}/{ds}/{MODELS[key]}/{scene}/pred"
    p = f"{d}/v{v:02d}_f{f:02d}.png"
    if os.path.exists(p):
        return p
    for x in os.listdir(d):
        m = C4G_RE.match(x)
        if m and int(m.group(1)) == v and int(m.group(2)) == f:
            return f"{d}/{x}"
    return None


def grid_of(ds, scene):
    fs = os.listdir(f"{B}/{ds}/{ds}/ours_posed/{scene}/pred")
    views = sorted({int(m.group(1)) for f in fs if (m := re.match(r"v(\d+)_f(\d+)", f))})
    frames = sorted({int(m.group(2)) for f in fs if (m := re.match(r"v(\d+)_f(\d+)", f))})
    return views, frames


def gt_provider(ds, scene, views):
    if ds == "nvidia":
        return lambda v, f: Image.open(f"{GT_NV}/{scene}/multiview_GT/{f + 1:08d}/cam{v + 1:02d}.jpg").convert("RGB")
    tdir = f"{GT_CX}/{scene}/camera-trajectory-01"
    nums = sorted(int(f[3:6]) for f in os.listdir(tdir) if f.startswith("cam") and f.endswith("_full_motion.mp4"))
    def read(v, f):
        cap = cv2.VideoCapture(f"{tdir}/cam{nums[v]:03d}_full_motion.mp4")
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f))
        ok, bgr = cap.read()
        cap.release()
        assert ok, (scene, v, f)
        return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    return read


def psnr_keep(ds, scene, views, frames, gt):
    small = lambda im: np.asarray(im.convert("RGB").resize((240, 135)), dtype=np.float32)
    n = len(views)
    M = np.full((n, n), np.nan)
    for i, v in enumerate(views):
        for j, f in enumerate(frames):
            if i != j:
                a, g = small(Image.open(pred_path(ds, "ours", scene, v, f))), small(gt(v, f))
                M[i, j] = 10 * np.log10(255 ** 2 / np.mean((a - g) ** 2))
    score = (np.nanmean(M, 1) + np.nanmean(M, 0)) / 2
    return sorted(int(i) for i in np.argsort(-score)[:KEEP]), float(np.nanmean(M))


def save(im, path):
    im = im.convert("RGB")
    h = round(W * im.height / im.width)
    im.resize((W, h), Image.LANCZOS).save(path, "WEBP", quality=82, method=6)
    return h


def export(ds, scene, name):
    views, frames = grid_of(ds, scene)
    gt = gt_provider(ds, scene, views)
    keep, mean = psnr_keep(ds, scene, views, frames, gt)
    d = os.path.join(OUT, scene)
    os.makedirs(d, exist_ok=True)
    h = None
    for i in keep:
        for j in keep:
            v, f = views[i], frames[j]
            p = f"{d}/gt_v{i:02d}_f{j:02d}.webp"
            if not os.path.exists(p):
                h = save(gt(v, f), p)
            else:
                h = Image.open(p).height
            if i == j:
                continue
            for key in MODELS:
                p = f"{d}/{key}_v{i:02d}_f{j:02d}.webp"
                if not os.path.exists(p):
                    save(Image.open(pred_path(ds, key, scene, v, f)), p)
    print(ds, scene, keep, round(mean, 2), flush=True)
    return dict(id=scene, ds=ds, name=name, keep=keep, w=W, h=h, psnr=round(mean, 2))


def main():
    os.makedirs(OUT, exist_ok=True)
    scenes = []
    nv = f"{B}/nvidia/nvidia/ours_posed"
    for scene in sorted(d for d in os.listdir(nv) if os.path.isdir(f"{nv}/{d}")):
        scenes.append(export("nvidia", scene, NAMES.get(scene, scene)))
    for scene in CAMX:
        scenes.append(export("camxtime", scene, "CamxTime " + scene[5:]))
    json.dump(dict(models=["ours", "gt", "c4g", "neoverse", "movies", "4dgt"], scenes=scenes), open(os.path.join(OUT, "teaser.json"), "w"), indent=1)
    print("done")


if __name__ == "__main__":
    main()
