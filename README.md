# FL4N project page

Static site: open `index.html` directly or serve the folder (`python3 -m http.server`).

- `index.html`, `static/css/style.css`, `static/js/main.js` — the page.
- `static/js/scenes.js` — scene manifest from the suppl page (kept for reference).
- `static/images/*.webp` — paper figures exported from `RELO4D_overleaf/figures/assets/*.pdf`.
- `static/figures/` + `static/js/figures.js` + `static/css/figures.css` — the paper figures that stay interactive (step-through architecture, view×time teaser explorer, static-vs-residual comparison, static feature grid). The architecture is built from `figure_ppts/mainarch.pdf` (not committed) by `tools/build_arch.py`: PyMuPDF exports the page as SVG with glyphs as paths, `tools/svg_bbox.js` (Playwright) measures every element so `region()` can tag it with its pipeline stages, and overlapping same-stage siblings are grouped so dimming stays clean. The other figures come from `figure_ppts/*.pptx` through `tools/pptx2svg.py` (generic pptx→SVG converter), `tools/extract_figures.py` (pictures + layout → `static/js/figdata.js`) and `tools/build_teaser.py` (view×time CTVS matrices of all nine NVIDIA scenes for every model, pruned to the 8 view/time indices with the best FL4N PSNR, from the raw prediction folders; MoVieS on NVIDIA comes from `ssd_symlink/sde/eunbeen/final_benchmark`, everything else from `baseline_evals_res`). The context-frame chart values are read off the paper PDF (`tools/` has no source numbers).
- `static/videos/overview.mp4` + `overview.vtt` + `static/images/overview-poster.webp` — the animated overview; source and re-render instructions in `tools/overview/`.
- Logo: `figure_ppts/flan.png` (pudding) → `static/images/flan.webp` (hero), `flan-icon.webp` (brand), `favicon.png`, `apple-touch-icon.png`. Script/CSS tags carry a `?v=` stamp; bump it (any new number) when editing JS/CSS so browsers and the Pages CDN (max-age 600 s) do not serve stale code.
- Hosting: public repo `eunbeen-hong/FL4N`, GitHub Pages from `main` → https://eunbeen-hong.github.io/FL4N/ (push to update).

To fill in before release: authors, affiliations, paper/arXiv/code links, badge text, and the BibTeX entry in `index.html`.

The hero camera-rig visualisation and its clips were removed on 2026-10-13 (user request); `tools/build_rig.py` and `tools/build_rig_grid.py` remain for reference.

`tools/teaser_ppt/build_teaser_ppt.py` builds the paper teaser deck (`tools/teaser_ppt/teaser.pptx`, also copied to `figure_ppts/`): explicit 3D Gaussians vs the FL4N latent on three NVIDIA scenes (MoVieS crop from `final_benchmark`, the rest from `baseline_evals_res`), native PowerPoint shapes in the page palette with Google Sans, plus `teaser_preview.png` rendered from an HTML twin of the same layout.

## Repository layout

This page lives on the `gh-pages` branch of [eunbeen-hong/FL4N](https://github.com/eunbeen-hong/FL4N) and GitHub Pages serves it from there; the `main` branch holds the code release (the former `~/project/eunbeen/FL4N_code` tree). Push page changes to `gh-pages` only.
