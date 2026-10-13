# FL4N project page

Static site: open `index.html` directly or serve the folder (`python3 -m http.server`).

- `index.html`, `static/css/style.css`, `static/js/main.js` — the page.
- `static/js/scenes.js` — scene manifest driving the video gallery and the rig scene list.
- `static/images/*.webp` — paper figures exported from `RELO4D_overleaf/figures/assets/*.pdf`.
- `static/videos/compare/` — per-model clips (`{protocol}_{dataset}_{scene}__{model}.mp4`), copied from `supp_html/clips`.
- `static/videos/rig/` — hero camera-rig clips: one short mp4 per scene, model and camera (`{ds}_{scene}__{model}__c{k}.mp4`), the input sweep (`__input.mp4/.jpg`) and `manifest.json`; built by `tools/build_rig.py` (resumable, skips existing clips; `--only=gt` builds only ground-truth rows). The page plays ONE `{ds}_{scene}__grid.mp4` per scene (rows = models, cols = 8 cams), composed from the per-camera clips by `tools/build_rig_grid.py`; per-camera clips are kept only as the source for that step. GT sources: N3DV frame cache on sde, NVIDIA `multiview_GT` under `/mnt/sde/eunbeen/data/NVIDIA_x`, CamxTime trajectory-01 mp4s under `/mnt/sde/eunbeen/data/CamxTime_x`; Charge raw data is not on disk, so it has no GT row.
- `static/js/rig.js` — the 3D dome rig in the hero; sources and geometry are configured in its `CONFIG` block.

To fill in before release: authors, affiliations, paper/arXiv/code links, badge text, and the BibTeX entry in `index.html`.
