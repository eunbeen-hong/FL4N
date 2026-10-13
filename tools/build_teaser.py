"""Export view x time CTVS matrices (all models + GT) of the NVIDIA scenes as small webps for the interactive teaser, keeping the 8 view/time indices where FL4N scores best."""
import os, re, json, shutil
import numpy as np
from PIL import Image

B = "/home/cvlab20/project/eunbeen/ssd_symlink/sde/eunbeen/baseline_evals_res/ctvs/nvidia/nvidia"
GT = "/mnt/sde/eunbeen/data/NVIDIA_x/NVIDIA"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "figures", "teaser")
MODELS = {"ours": "ours_posed", "4dgt": "4dgt", "movies": "movies", "neoverse": "neoverse_tto_nostatic", "c4g": "c4g_lbgt"}
NAMES = {"Teadybear": "Teddy bear", "DynamicFace": "Dynamic face"}
W, KEEP, N = 320, 8, 12
C4G_RE = re.compile(r"^all_(\d+)_i\d+_f(\d+)\.png$")


def gt_path(scene, v, f):
    return f"{GT}/{scene}/multiview_GT/{f + 1:08d}/cam{v + 1:02d}.jpg"


def pred_path(key, scene, v, f):
    d = f"{B}/{MODELS[key]}/{scene}/pred"
    p = f"{d}/v{v:02d}_f{f:02d}.png"
    if os.path.exists(p):
        return p
    for x in os.listdir(d):
        m = C4G_RE.match(x)
        if m and int(m.group(1)) == v and int(m.group(2)) == f:
            return f"{d}/{x}"
    return None


def psnr_keep(scene):
    small = lambda p: np.asarray(Image.open(p).convert("RGB").resize((240, 135)), dtype=np.float32)
    M = np.full((N, N), np.nan)
    for v in range(N):
        for f in range(N):
            if v != f:
                a, g = small(pred_path("ours", scene, v, f)), small(gt_path(scene, v, f))
                M[v, f] = 10 * np.log10(255 ** 2 / np.mean((a - g) ** 2))
    score = (np.nanmean(M, 1) + np.nanmean(M, 0)) / 2
    return sorted(int(i) for i in np.argsort(-score)[:KEEP]), float(np.nanmean(M))


def save(src, path):
    im = Image.open(src).convert("RGB")
    h = round(W * im.height / im.width)
    im.resize((W, h), Image.LANCZOS).save(path, "WEBP", quality=82, method=6)
    return h


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    scenes = []
    for scene in sorted(d for d in os.listdir(f"{B}/ours_posed") if os.path.isdir(f"{B}/ours_posed/{d}")):
        keep, mean = psnr_keep(scene)
        d = os.path.join(OUT, scene)
        os.makedirs(d, exist_ok=True)
        h = None
        for v in keep:
            for f in keep:
                h = save(gt_path(scene, v, f), f"{d}/gt_v{v:02d}_f{f:02d}.webp")
                if v == f:
                    continue
                for key in MODELS:
                    save(pred_path(key, scene, v, f), f"{d}/{key}_v{v:02d}_f{f:02d}.webp")
        scenes.append(dict(id=scene, name=NAMES.get(scene, scene), keep=keep, w=W, h=h, psnr=round(mean, 2)))
        print(scene, keep, round(mean, 2), flush=True)
    json.dump(dict(dataset="NVIDIA", models=["ours", "gt", "c4g", "neoverse", "movies", "4dgt"], scenes=scenes), open(os.path.join(OUT, "teaser.json"), "w"), indent=1)
    print("done")


if __name__ == "__main__":
    main()
