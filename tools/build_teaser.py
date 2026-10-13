"""Export the full view x time CTVS matrix of the NVIDIA Skating scene (all models + GT) as small webps for the interactive teaser."""
import os, re, json
from PIL import Image

B = "/home/cvlab20/project/eunbeen/ssd_symlink/sde/eunbeen/baseline_evals_res/ctvs/nvidia/nvidia"
GT = "/mnt/sde/eunbeen/data/NVIDIA_x/NVIDIA/Skating/multiview_GT"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "figures", "teaser")
MODELS = {"ours": "ours_posed", "4dgt": "4dgt", "movies": "movies", "neoverse": "neoverse_tto_nostatic", "c4g": "c4g_lbgt"}
W = 320
C4G_RE = re.compile(r"^all_(\d+)_i\d+_f(\d+)\.png$")


def save(im, path):
    im = im.convert("RGB")
    h = round(W * im.height / im.width)
    im.resize((W, h), Image.LANCZOS).save(path, "WEBP", quality=82, method=6)
    return h


def main():
    os.makedirs(OUT, exist_ok=True)
    h = None
    for v in range(12):
        for f in range(12):
            p = os.path.join(OUT, f"gt_v{v:02d}_f{f:02d}.webp")
            if not os.path.exists(p):
                h = save(Image.open(f"{GT}/{f + 1:08d}/cam{v + 1:02d}.jpg"), p)
            if v == f:
                continue
            for key, d in MODELS.items():
                p = os.path.join(OUT, f"{key}_v{v:02d}_f{f:02d}.webp")
                if os.path.exists(p):
                    continue
                src = f"{B}/{d}/Skating/pred/v{v:02d}_f{f:02d}.png"
                if not os.path.exists(src):
                    cands = [x for x in os.listdir(f"{B}/{d}/Skating/pred") if (m := C4G_RE.match(x)) and int(m.group(1)) == v and int(m.group(2)) == f]
                    src = f"{B}/{d}/Skating/pred/{cands[0]}" if cands else None
                if src:
                    save(Image.open(src), p)
    im = Image.open(os.path.join(OUT, "gt_v00_f00.webp"))
    json.dump(dict(scene="Skating", dataset="NVIDIA", views=12, frames=12, models=["ours", "gt", "c4g", "neoverse", "movies", "4dgt"], w=im.width, h=im.height), open(os.path.join(OUT, "teaser.json"), "w"))
    print("done", len(os.listdir(OUT)), "files")


if __name__ == "__main__":
    main()
