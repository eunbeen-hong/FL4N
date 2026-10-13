#!/usr/bin/env python3
"""Compose per-scene multi-camera CTVS videos: left = input monocular video, right = every static camera rendered by FL4N over time."""
import json, os, re, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont

B = "/home/cvlab20/project/eunbeen/ssd_symlink/sde/eunbeen/baseline_evals_res"
CLIPS = "/home/cvlab20/project/eunbeen/supp_html/clips"
MANIFEST = "/home/cvlab20/project/eunbeen/supp_html/scene_manifest.json"
OUT = "/home/cvlab20/project/eunbeen/FL4N_project_page/static/videos/multiview"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
DATASETS = {"nvidia": (3, 420), "kubric4d": (2, 480), "camxtime": (4, 300), "charge": (2, 520), "n3dv": (4, 360)}
FPS = {"nvidia": 4, "kubric4d": 3, "camxtime": 3, "charge": 3, "n3dv": 4}
N3DV_PRED = "/mnt/nvme1n1/eunbeen/eval/n3dv_ctvs_vggt/n3dv/ours_posed_vggt"
N3DV_CACHE = "/mnt/sde/eunbeen/baseline_evals/n3dv/_frame_cache"
GAP, BG, RED = 6, (17, 17, 23), (239, 68, 68)
FNAME_RE = re.compile(r"^v(.+)_f(\d+)\.png$")


def decode_inp(ds, scene, tmp):
    if ds == "n3dv":
        import glob
        z = np.load(sorted(glob.glob(f"{N3DV_CACHE}/{scene}_1014x1352_*c_*.npz"))[-1])
        return [Image.fromarray(a) for a in z["cond"]]
    src = f"{CLIPS}/ctvs_{ds}_{scene}__inp.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, f"{tmp}/inp_%03d.png"], check=True)
    return [Image.open(f"{tmp}/{f}").convert("RGB") for f in sorted(os.listdir(tmp)) if f.startswith("inp_")]


def small(im, size=(64, 36)):
    return np.asarray(im.resize(size, Image.BILINEAR), dtype=np.float32)


def assign_inputs(inps, views, preds):
    sig = {v: np.mean([small(Image.open(preds[v][f])) for f in list(preds[v])[:3]], axis=0) for v in views}
    out, used = {}, set()
    for i, im in enumerate(inps):
        s = small(im)
        best = min((v for v in views if v not in used), key=lambda v: np.abs(sig[v] - s).mean())
        out[best] = i
        used.add(best)
    return out


def label(draw, xy, text, font, fill=(255, 255, 255), bg=(0, 0, 0, 160)):
    x, y = xy
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    draw.rectangle([x, y, x + w + 14, y + h + 10], fill=bg)
    draw.text((x + 7, y + 4), text, font=font, fill=fill)


def fit(im, w, h):
    return im.resize((w, h), Image.LANCZOS)


def build(ds, scene):
    cols, cw = DATASETS[ds]
    pred_dir = f"{N3DV_PRED}/{scene}/pred" if ds == "n3dv" else f"{B}/ctvs/{ds}/{ds}/ours_posed/{scene}/pred"
    preds = {}
    for f in sorted(os.listdir(pred_dir)):
        m = FNAME_RE.match(f)
        if m:
            preds.setdefault(m.group(1), {})[int(m.group(2))] = f"{pred_dir}/{f}"
    views = sorted(preds)
    frames = sorted(set(fr for v in views for fr in preds[v]))
    diag = {v: next(fr for fr in frames if fr not in preds[v]) for v in views}
    tmp = tempfile.mkdtemp()
    inps = decode_inp(ds, scene, tmp)
    assert len(inps) == len(views), (scene, len(inps), len(views))
    v2inp = assign_inputs(inps, views, preds)
    w0, h0 = Image.open(next(iter(preds[views[0]].values()))).size
    ch = round(cw * h0 / w0 / 2) * 2
    rows = (len(views) + cols - 1) // cols
    gh = rows * ch + (rows - 1) * GAP
    ph = gh
    pw = round(ph * w0 / h0 / 2) * 2
    W = pw + GAP * 4 + cols * cw + (cols - 1) * GAP
    H = gh
    font = ImageFont.truetype(FONT, max(13, cw // 22))
    bigfont = ImageFont.truetype(FONT, max(15, pw // 24))
    fdir = f"{tmp}/frames"
    os.makedirs(fdir)
    time_of_input = {diag[v]: v for v in views}
    for ti, fr in enumerate(frames):
        canvas = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(canvas, "RGBA")
        vin = time_of_input[fr]
        canvas.paste(fit(inps[v2inp[vin]], pw, ph), (0, 0))
        d.rectangle([0, 0, pw - 1, ph - 1], outline=RED, width=4)
        label(d, (10, 10), f"Input video  ·  frame {ti + 1}/{len(frames)}", bigfont)
        label(d, (10, ph - 10 - bigfont.size - 10), f"camera {views.index(vin) + 1}", bigfont, fill=RED)
        for k, v in enumerate(views):
            r, c = divmod(k, cols)
            x = pw + GAP * 4 + c * (cw + GAP)
            y = r * (ch + GAP)
            is_in = fr == diag[v]
            im = inps[v2inp[v]] if is_in else Image.open(preds[v][fr]).convert("RGB")
            canvas.paste(fit(im, cw, ch), (x, y))
            if is_in:
                d.rectangle([x, y, x + cw - 1, y + ch - 1], outline=RED, width=4)
                label(d, (x + 8, y + 8), f"camera {k + 1}  ·  input", font, fill=RED)
            else:
                label(d, (x + 8, y + 8), f"camera {k + 1}", font)
        canvas.save(f"{fdir}/f_{ti:03d}.png")
        if ti == 0:
            canvas.save(f"{OUT}/mv_{ds}_{scene}.jpg", quality=85)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS[ds]), "-i", f"{fdir}/f_%03d.png",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", f"{OUT}/mv_{ds}_{scene}.mp4"], check=True)
    shutil.rmtree(tmp)
    print(f"{ds}/{scene}: {len(views)} cams x {len(frames)} frames -> {W}x{H}, input map {v2inp}")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:]
    entries = [e for e in json.load(open(MANIFEST)) if e["protocol"] == "ctvs" and e["dataset"] in DATASETS and (not only or e["dataset"] in only)]
    for e in entries:
        build(e["dataset"], e["scene"])
