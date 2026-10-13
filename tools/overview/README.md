# Overview video

`overview.html` is a deterministic timeline animation in the page's light theme (cream background, caramel/custard accents, flan logo): `render(t)` sets every element for time `t` in seconds, 41.5 s total at 30 fps, 1920x840, no chapter numbering. Chapters: title 0-2.5, input 2.5-6.5, task grid 6.5-11, Gaussians struggle 11-16, architecture 16-25.5 (the paper figure `static/figures/arch.svg`, injected by `render_frames.js`, revealed stage by stage through its `.st` classes with per-stage captions), any view any time 25.5-31.5, image-only training 31.5-35, state of the art 35-39.5, closing 39.5-41.5. Minimum text 22 px.

`assets/` holds the frames it uses (Skating input/rendered/bullet-time frames and baseline renders); the Skating view x time matrix comes from `static/figures/teaser/Skating/`.

Re-render:

```bash
PW=/tmp/claude-1001/-home-cvlab20-project-eunbeen-LagerNVS4d/2029518d-9a2f-403f-a387-494dcea53f53/scratchpad/pw   # any dir with node_modules/playwright
cd $PW && NODE_PATH=$PW/node_modules node tools/overview/render_frames.js tools/overview/overview.html /tmp/ovframes 30 41.5
bash tools/overview/encode.sh /tmp/ovframes   # writes static/videos/overview.mp4 + static/images/overview-poster.webp
```

Preview single times: pass a comma-separated list of seconds as the 6th argument to `render_frames.js` (writes PNGs). `static/videos/overview.vtt` is the hand-written description track, one cue per chapter.
