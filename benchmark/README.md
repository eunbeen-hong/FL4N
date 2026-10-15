# Benchmark

Final evaluation of FL4N and four baselines (MoVieS, NeoVerse, 4DGT, C4G) under the three protocols
(CTVS / NVS / NTS) on 8 datasets. `settings.py` holds every per-cell setting; `run_eval.py` is the entry point.

```bash
python benchmark/run_eval.py --models fl4n movies neoverse 4dgt c4g --gpus 0 1 2 3
python benchmark/run_eval.py --models fl4n --posed --gpus 0 1 2 3          # FL4N with conditioning poses -> fl4n_posed/
python benchmark/run_eval.py --models c4g --protocols nvs --datasets n3dv --gpus 0
```
Output: `<out>/<protocol>/<dataset>/<dataset>/<out_name>/{<scene>/pred/*.png, <scene>/metrics.json, summary.json}`.
A `_done_<out_name>` marker is written only when `summary.json` covers the full scene count, so interrupted
runs resume. `BENCH_NOSAVE=1` skips the per-target PNG dumps.

## Environments and baselines
Each model runs in its own conda env (`settings.py:ENVS`, override with `CONDA_ENVS`):

| model | conda env | baseline repo |
|---|---|---|
| `fl4n` (`--posed` for the posed variant) | `fl4n` | this repo (`checkpoints/fl4n.ckpt`, override with `FL4N_CKPT`) |
| `movies` | `movies_eb` | `baselines/MoVieS` |
| `neoverse` | `neoverse_eb` | `baselines/NeoVerse` |
| `4dgt` | `4dgt_eb` | `baselines/4DGT` (gsplat JIT needs `ninja` on PATH) |
| `c4g` | `c4g_eb` | `baselines/C4G` |

## Paths
Everything external comes from four environment variables, resolved in `common/bench_paths.py`:

| variable | default | holds |
|---|---|---|
| `FL4N_DATA` | `./data` | one subdirectory per dataset (`CamxTime`, `Kubric4D/test`, `NVIDIA`, `N3DV`, `Charge_v1_0`, `ADT`, `DyCheck`, `TUM`), `vggt_poses/<tag>/` with the VGGT camera cache (`<dataset>__<scene>.npz`), and `_cache/` written by the loaders |
| `FL4N_BASELINES` | `./baselines` | `MoVieS/`, `NeoVerse/`, `4DGT/`, `C4G/` repos and `weights/{movies,neoverse,4dgt,c4g}/<ckpt>` |
| `BENCH_OUT_ROOT` | `./benchmark_out` | results (`run_eval.py --out` sets it per cell) |
| `CONDA_ENVS` | parent of the running env | the conda env root containing `fl4n`, `movies_eb`, `neoverse_eb`, `4dgt_eb`, `c4g_eb` |

`FL4N_CKPT` overrides the FL4N checkpoint (`checkpoints/fl4n.ckpt`) and `VGGT_POSE_CACHE` the pose cache pattern.

## Protocol
- Scoring at native GT resolution (predictions bilinearly upsampled); PSNR, SSIM (11x11 gaussian), LPIPS-vgg;
  overall = mean over all targets and scenes. Kubric4D and Charge also report masked dynamic-region PSNR;
  DyCheck is restricted to covisible pixels.
- FL4N never sees conditioning poses unless `--posed`. Pose normalisation: cameras in the first conditioning
  camera's frame, scaled so the largest conditioning-camera distance equals 1.35 (`CAM_SCALE`).

| protocol | setup | datasets |
|---|---|---|
| CTVS (cross-time view) | N diagonal conditioning frames (camera i at time i) -> all N x N - N off-diagonal cells | nvidia, n3dv, kubric4d, camxtime, charge |
| NVS (novel view, known time) | 9-camera window, hold out the 5th; 8 diagonal inputs -> held-out camera at the 8 conditioning times (`BENCH_TABLE2=1 BENCH_NVS8=1`) | nvidia, n3dv, kubric4d, camxtime, charge |
| NTS (novel time) | 16 context frames at stride S from frame 0 -> 15 in-between targets | adt (S=6), tum (S=6), dycheck (single camera, S=4) |

On NVIDIA, N3DV and the NTS sets FL4N uses VGGT-estimated extrinsics and intrinsics from a per-dataset,
per-protocol cache (`FL4N_VGGT_POSE_DIR`, see `settings.py:VGGT_CACHE`); synthetic sets use their exact cameras.

| model | input | cameras | test-time pose optimisation |
|---|---|---|---|
| FL4N | 512 long edge | VGGT (real) / GT (synthetic) | none |
| MoVieS | 518 long edge | dataset GT | none |
| NeoVerse | 560 long edge, static branch off | dataset GT | target view, 2000 steps (oracle) |
| 4DGT | 504 x 504 | dataset GT | none |
| C4G | letterboxed 224^2, GT-res render | dataset GT | target view, 2000 steps (oracle) |

## Settings worth knowing
- The N3DV NVS pose cache (`vggt_poses/n3dv_nvs`) differs from the generic one; using the wrong cache costs about 2.5 dB.
- Kubric4D = all 100 test scenes (`KUB4D_ALL=1`); the hard-coded 30-scene list is a legacy subset.
- `CAM_SCALE` = 1.35 (the training value) for both the pose-free and posed rows.
- Every cell waits for the model's minimum free VRAM on its GPU before starting.

## Layout
```
run_eval.py  settings.py  pathsetup.py
runners/     bench_fl4n.py  bench_movies.py  bench_neoverse.py  bench_4dgt.py  bench_c4g.py
common/      bench_paths.py (all external paths)  bench_proto_common.py (I/O + summaries)  protocol_score.py (PSNR/SSIM/LPIPS at native GT res)
datasets/    bench_ds_{nvidia,n3dv,n3dv_proto,kubric4d,camxtime,charge,adt,dycheck,tum}.py  bench_nvs8.py  bench_static_util.py
```
