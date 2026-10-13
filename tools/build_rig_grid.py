#!/usr/bin/env python3
"""Compose each scene's per-camera rig clips into grid mp4s: `__grid_main` (GT + FL4N rows) and one single-row `__grid_<baseline>` per baseline, cols = selected cameras."""
import json, os, shutil, subprocess, sys, tempfile
import cv2
import numpy as np

RIG = "/home/cvlab20/project/eunbeen/FL4N_project_page/static/videos/rig"
BASELINES = ["c4g", "neoverse", "movies", "4dgt"]
MAX_CAMS, GAP, BG = 8, 8, (255, 255, 255)


def pick(n, k):
    k = min(n, k)
    return [round(i * (n - 1) / (k - 1)) for i in range(k)]


def frames_of(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(f)
    cap.release()
    return out


def build(key, m, name, rows, force=False):
    out = f"{RIG}/{key}__grid_{name}.mp4"
    cams = pick(m["cams"], MAX_CAMS)
    if os.path.exists(out) and not force:
        return cams, rows
    clips = {(r, c): frames_of(f"{RIG}/{key}__{r}__c{c:02d}.mp4") for r in rows for c in cams}
    n = min(len(v) for v in clips.values())
    h, w = next(iter(clips.values()))[0].shape[:2]
    W, H = len(cams) * w + (len(cams) - 1) * GAP, len(rows) * h + (len(rows) - 1) * GAP
    tmp = tempfile.mkdtemp()
    for t in range(n):
        canvas = np.full((H, W, 3), BG, np.uint8)
        for ri, r in enumerate(rows):
            for ci, c in enumerate(cams):
                y, x = ri * (h + GAP), ci * (w + GAP)
                canvas[y:y + h, x:x + w] = clips[(r, c)][t]
        cv2.imwrite(f"{tmp}/f_{t:03d}.png", canvas)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(m["fps"]), "-i", f"{tmp}/f_%03d.png", "-c:v", "libx264", "-preset", "slow",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", out], check=True)
    shutil.rmtree(tmp)
    print(f"{key}: {len(rows)} rows x {len(cams)} cams -> {W}x{H}, {os.path.getsize(out) // 1024} KB", flush=True)
    return cams, rows


if __name__ == "__main__":
    force = "--force" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    mp = f"{RIG}/manifest.json"
    m = json.load(open(mp))
    for key, e in m.items():
        if only and e["ds"] not in only:
            continue
        main = (["gt"] if e.get("gt") else []) + ["ours"]
        cams, rows = build(key, e, "main", main, force)
        for b in BASELINES:
            build(key, e, b, [b], force)
        e["grid"] = {"cams": cams, "rows": main, "baselines": BASELINES, "gap": GAP}
    json.dump(m, open(mp + ".tmp", "w"), indent=1)
    os.replace(mp + ".tmp", mp)
