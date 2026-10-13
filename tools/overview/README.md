# Overview video

`overview.html` is a deterministic timeline animation (`render(t)` sets every element for time `t` in seconds, 72 s total). `assets/` holds the extracted frames it uses (Skating input/rendered/bullet-time frames from `static/videos/rig`, baseline frames from `static/videos/compare`, latent PCA and gate images from `static/figures`).

Re-render:

```bash
cd /tmp/claude-1001/-home-cvlab20-project-eunbeen-LagerNVS4d/2029518d-9a2f-403f-a387-494dcea53f53/scratchpad/pw   # any dir with node_modules/playwright
NODE_PATH=$PWD/node_modules node tools/overview/render_frames.js tools/overview/overview.html /tmp/ovframes 30 72
bash tools/overview/encode.sh /tmp/ovframes   # writes static/videos/overview.mp4 + static/images/overview-poster.webp
```

Preview single times: append a comma-separated list of seconds as the 6th argument to `render_frames.js` (writes PNGs instead of the JPEG sequence). `static/videos/overview.vtt` is the hand-written description track.
