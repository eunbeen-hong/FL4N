# FL4N project page

Static site: open `index.html` directly or serve the folder (`python3 -m http.server`).

- `index.html`, `static/css/style.css`, `static/js/main.js` — the page.
- `static/js/scenes.js` — scene manifest from the suppl page (kept for reference).
- `static/images/*.webp` — paper figures exported from `RELO4D_overleaf/figures/assets/*.pdf`.
- `static/figures/` + `static/js/figures.js` + `static/css/figures.css` — the paper figures that stay interactive (step-through architecture from slide 1 of mainarch.pptx, view×time teaser explorer, static-vs-residual comparison, auto-playing latent/gate scrubbers, SVG chart); evaluation settings, static-latent PCA and the qualitative grid are plain images exported from the paper PDFs. Built from `figure_ppts/*.pptx` (not committed) by `tools/pptx2svg.py` (generic pptx→SVG converter), `tools/build_arch.py` (architecture SVG with per-stage classes and math labels; EMF latent tiles are redrawn as SVG), `tools/extract_figures.py` (pictures + layout → `static/js/figdata.js`) and `tools/build_teaser.py` (view×time CTVS matrices of all nine NVIDIA scenes for every model, pruned to the 8 view/time indices with the best FL4N PSNR, from the raw prediction folders). The context-frame chart values are read off the paper PDF (`tools/` has no source numbers).
- `static/videos/overview.mp4` + `overview.vtt` + `static/images/overview-poster.webp` — the animated overview; source and re-render instructions in `tools/overview/`.
- Logo: `figure_ppts/flan.png` (pudding) → `static/images/flan.webp` (hero), `flan-icon.webp` (brand), `favicon.png`, `apple-touch-icon.png`. Script/CSS tags carry a `?v=` stamp; bump it (any new number) when editing JS/CSS so browsers and the Pages CDN (max-age 600 s) do not serve stale code.
- Hosting: public repo `eunbeen-hong/FL4N`, GitHub Pages from `main` → https://eunbeen-hong.github.io/FL4N/ (push to update).

To fill in before release: authors, affiliations, paper/arXiv/code links, badge text, and the BibTeX entry in `index.html`.

The hero camera-rig visualisation and its clips were removed on 2026-10-13 (user request); `tools/build_rig.py` and `tools/build_rig_grid.py` remain for reference.
