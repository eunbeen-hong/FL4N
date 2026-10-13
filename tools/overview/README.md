# Overview video

`overview.html` is a deterministic timeline animation in the page's light theme (cream background, caramel/custard accents, flan logo): `render(t)` sets every element for time `t` in seconds, 47 s total at 30 fps, 1920x840. Chapters: title 0-3, 01 input 3-8, 02 task grid 8-13, 03 Gaussians struggle 13-19, 04 frozen static prior 19-24, 05 dynamic encoder 24-30, 06 any view any time 30-36, 07 image-only training 36-40, 08 state of the art 40-45, closing 45-47. All connectors are horizontal/vertical SVG paths; minimum text 22 px.

`assets/` holds the frames it uses (Skating input/rendered/bullet-time frames, baseline renders, latent PCA and gate images); the Skating view x time matrix comes from `static/figures/teaser/Skating/`.

Re-render:

```bash
PW=/tmp/claude-1001/-home-cvlab20-project-eunbeen-LagerNVS4d/2029518d-9a2f-403f-a387-494dcea53f53/scratchpad/pw   # any dir with node_modules/playwright
cd $PW && NODE_PATH=$PW/node_modules node tools/overview/render_frames.js tools/overview/overview.html /tmp/ovframes 30 47
bash tools/overview/encode.sh /tmp/ovframes   # writes static/videos/overview.mp4 + static/images/overview-poster.webp
```

Preview single times: pass a comma-separated list of seconds as the 6th argument to `render_frames.js` (writes PNGs). `static/videos/overview.vtt` is the hand-written description track, one cue per chapter.
