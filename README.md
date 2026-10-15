<div align="center">

<img src="assets/flan.webp" alt="FL4N" width="140">

# FL4N

#### Feed-forward Latent Model for 4D Novel View Synthesis

**The first feed-forward latent 4D NVS model.**

[![Project Page](https://img.shields.io/badge/Project%20Page-FL4N-b4591e?style=for-the-badge)](https://eunbeen-hong.github.io/FL4N/)
[![arXiv](https://img.shields.io/badge/arXiv-coming%20soon-b31b1b?style=for-the-badge)](https://eunbeen-hong.github.io/FL4N/)
[![Checkpoint](https://img.shields.io/badge/%F0%9F%A4%97%20Checkpoint-coming%20soon-ffcc4d?style=for-the-badge)](#-checkpoint)

This is the official implementation of the paper **"FL4N: Feed-forward Latent Model for 4D Novel View Synthesis"** by
[Eunbeen Hong](https://eunbeen-hong.github.io/)<sup>1</sup>, [Hyeonseo Yu](https://hdeori.github.io/)<sup>1</sup>, [Soowon Son](https://soow0n.github.io/)<sup>1</sup>, [Chaehyun Kim](https://kchyun.github.io/)<sup>1</sup>, [Jahyeok Koo](https://jahyeok-koo.github.io/)<sup>1</sup>, [Jisoo Kim](https://jiiiisoo.github.io/)<sup>1</sup>, [Junhwa Hur](https://hurjunhwa.github.io/)<sup>2†</sup>, [Seungryong Kim](https://cvlab.kaist.ac.kr/)<sup>1†</sup>.

<sup>1</sup> KAIST AI &nbsp;&nbsp;&nbsp; <sup>2</sup> Google DeepMind

<sub>† Corresponding authors.</sub>

</div>

**FL4N** renders a dynamic scene from viewpoints and timestamps that were never observed, given one monocular video,
in a single feed-forward pass. Existing feed-forward methods do this with explicit 3D Gaussians plus motion and pay
with ghosting, floaters and holes. FL4N bypasses explicit 4D primitives and keeps the whole scene in one latent
representation across space and time:

- **Frozen static latent prior.** A pretrained static latent NVS backbone supplies the 3D prior, so the model never has
  to learn geometry from the scarce dynamic training data.
- **Dynamic encoder with static anchoring.** A lightweight encoder sees each context frame with a learned time token and
  cross-attends into the frozen static features. It separates true scene motion from camera parallax and outputs a
  time-invariant **temporal residual** latent plus a dynamic mask.
- **Target-time adaptation.** A time module conditions the residual on the target timestamp and adds it to the static
  latent through a zero-initialised gate; the frozen renderer then produces the view. The residual is computed once per
  video, so every further target costs only the time module and the renderer.

Trained purely on image synthesis with binary motion-mask guidance, FL4N reaches state-of-the-art quality for
cross-time, novel-view and novel-time synthesis **in real time** (40 FPS at 224×224). More examples, the interactive
view×time explorer and the step-through architecture are on the [project page](https://eunbeen-hong.github.io/FL4N/).

<div align="center">
<img src="assets/teaser.webp" width="100%" alt="Explicit 3D Gaussians vs the FL4N latent">
<sub>Explicit Gaussian baselines (top) tear, blur and leave holes on the same views; FL4N (bottom) renders them cleanly.</sub>
</div>

## 🔥 TODO

- ☑️ Training, validation and benchmark code
- ☑️ Datasets mirrored on HuggingFace 🤗 ([pancakesonmonday/4D_dataset](https://huggingface.co/datasets/pancakesonmonday/4D_dataset/tree/main))
- ⬜ `fl4n.ckpt` release on HuggingFace 🤗
- ⬜ arXiv paper
- ⬜ HuggingFace 🤗 demo

## 📊 Results

Three protocols from one monocular video: **CTVS** renders unseen (view, time) pairs, **NVS** unseen views at seen
times, **NTS** unseen times at seen views. Scores are at native GT resolution with LPIPS-vgg; **bold** is best,
<ins>underlined</ins> second best. *Pose* says whether the context camera poses are given; † marks baselines that
run a 2,000-step test-time pose alignment with the target frames. FL4N needs no alignment: given context poses it is
best on every dataset, and the pose-free variant is second on all but one.

**Cross-time view synthesis (CTVS).**

| Method | Pose | NVIDIA PSNR ↑ | SSIM ↑ | LPIPS ↓ | N3DV PSNR ↑ | SSIM ↑ | LPIPS ↓ | Kubric4D PSNR ↑ | SSIM ↑ | LPIPS ↓ | CamxTime PSNR ↑ | SSIM ↑ | LPIPS ↓ | Charge PSNR ↑ | SSIM ↑ | LPIPS ↓ |
|---|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4DGT | ✓ | 15.937 | 0.3867 | 0.6052 | 16.097 | 0.6380 | 0.5483 | 15.680 | 0.5424 | 0.5786 | 17.024 | 0.6573 | 0.4939 | 17.939 | 0.7756 | 0.5617 |
| MoVieS | ✓ | 15.785 | 0.4614 | 0.5328 | 19.710 | 0.7400 | 0.4414 | 16.988 | 0.6368 | 0.4174 | 17.340 | 0.6470 | 0.4224 | 20.113 | 0.7771 | 0.5084 |
| NeoVerse† | ✗ | 14.449 | 0.3819 | 0.4890 | 12.447 | 0.4729 | 0.5681 | 8.885 | 0.2256 | 0.6793 | 10.276 | 0.3091 | 0.5911 | 15.220 | 0.5380 | 0.5940 |
| C4G† | ✗ | 16.403 | 0.4096 | 0.6304 | 17.039 | 0.6829 | 0.5374 | 15.270 | 0.5572 | 0.6348 | 20.175 | 0.7009 | 0.4453 | 18.410 | 0.7640 | 0.5324 |
| FL4N (ours) | ✗ | <ins>21.552</ins> | <ins>0.5348</ins> | <ins>0.3739</ins> | <ins>24.550</ins> | <ins>0.8152</ins> | <ins>0.3353</ins> | <ins>23.547</ins> | <ins>0.7535</ins> | <ins>0.2558</ins> | <ins>24.546</ins> | <ins>0.8040</ins> | <ins>0.2016</ins> | <ins>24.222</ins> | **0.8500** | <ins>0.4413</ins> |
| FL4N (ours) | ✓ | **21.838** | **0.5578** | **0.3562** | **25.109** | **0.8284** | **0.3234** | **24.272** | **0.7850** | **0.2304** | **27.648** | **0.8732** | **0.1325** | **24.421** | <ins>0.8496</ins> | **0.4382** |

**Novel view synthesis (NVS).**

| Method | Pose | NVIDIA PSNR ↑ | SSIM ↑ | LPIPS ↓ | N3DV PSNR ↑ | SSIM ↑ | LPIPS ↓ | Kubric4D PSNR ↑ | SSIM ↑ | LPIPS ↓ | CamxTime PSNR ↑ | SSIM ↑ | LPIPS ↓ | Charge PSNR ↑ | SSIM ↑ | LPIPS ↓ |
|---|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4DGT | ✓ | 16.127 | 0.3884 | 0.5972 | 17.813 | 0.6609 | 0.5131 | 14.148 | 0.5027 | 0.6096 | 17.125 | 0.6557 | 0.4893 | 18.017 | 0.7786 | 0.5653 |
| MoVieS | ✓ | 11.818 | 0.2546 | 0.6760 | <ins>20.136</ins> | 0.7045 | <ins>0.4605</ins> | 12.411 | 0.3550 | 0.6070 | 17.069 | 0.6223 | 0.4488 | 18.709 | 0.7473 | 0.5298 |
| NeoVerse† | ✗ | 15.050 | 0.4135 | <ins>0.4626</ins> | 12.953 | 0.4806 | 0.5697 | 8.954 | 0.2573 | 0.6721 | 10.432 | 0.3110 | 0.5905 | 15.224 | 0.5211 | 0.5919 |
| C4G† | ✗ | 16.572 | <ins>0.4182</ins> | 0.6203 | 18.444 | <ins>0.7050</ins> | 0.5246 | 14.931 | 0.5656 | 0.6442 | 20.527 | 0.7056 | 0.4369 | 18.535 | 0.7797 | 0.5279 |
| FL4N (ours) | ✗ | <ins>17.945</ins> | 0.4113 | 0.5229 | 18.581 | 0.6898 | 0.4776 | <ins>20.916</ins> | <ins>0.6433</ins> | <ins>0.3767</ins> | <ins>21.268</ins> | <ins>0.7237</ins> | <ins>0.2743</ins> | <ins>20.924</ins> | <ins>0.8217</ins> | <ins>0.4952</ins> |
| FL4N (ours) | ✓ | **20.435** | **0.4835** | **0.3867** | **22.896** | **0.7716** | **0.3560** | **22.209** | **0.6737** | **0.3350** | **25.730** | **0.8270** | **0.1681** | **22.959** | **0.8324** | **0.4616** |

**Novel time synthesis (NTS).**

| Method | Pose | DyCheck PSNR ↑ | SSIM ↑ | LPIPS ↓ | ADT PSNR ↑ | SSIM ↑ | LPIPS ↓ | TUM PSNR ↑ | SSIM ↑ | LPIPS ↓ |
|---|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4DGT | ✓ | 13.743 | 0.4079 | 0.6233 | 16.710 | 0.4999 | 0.5651 | 14.380 | 0.4468 | 0.5612 |
| MoVieS | ✓ | 11.755 | 0.3420 | 0.6428 | 15.432 | 0.4698 | 0.5828 | 15.683 | 0.5079 | 0.4426 |
| NeoVerse† | ✗ | 16.756 | 0.4663 | 0.4566 | 16.179 | 0.4384 | 0.5296 | 16.120 | 0.5266 | 0.3981 |
| C4G† | ✗ | 15.755 | 0.4735 | 0.6111 | 18.900 | 0.5813 | 0.5833 | 17.508 | 0.5518 | 0.4951 |
| FL4N (ours) | ✗ | <ins>19.019</ins> | <ins>0.4977</ins> | <ins>0.4284</ins> | <ins>19.693</ins> | <ins>0.5948</ins> | <ins>0.4490</ins> | <ins>17.847</ins> | <ins>0.5586</ins> | <ins>0.3449</ins> |
| FL4N (ours) | ✓ | **20.527** | **0.5470** | **0.3757** | **24.115** | **0.6875** | **0.3083** | **21.162** | **0.6978** | **0.2601** |

**Runtime per rendered view** (224×224, one RTX 5880 Ada):

| C4G† | NeoVerse† | 4DGT | MoVieS | C4G | NeoVerse | **FL4N (ours)** |
|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 23.885 s | 14.127 s | 0.040 s | 0.037 s | 0.036 s | 0.027 s | **0.025 s · 40 FPS** |

## 🧭 Layout
```
train.py                train / validate (Hydra + Lightning)
loss.py                 L2 + perceptual + dynamic-region terms + mask-head BCE
train_utils.py          LR schedules, weight-decay split
configs/config.yaml     the single config (model, loss, optimiser, data); override keys on the CLI
models/                 fl4n.py (model), encoder.py, time_module.py, renderer.py, checkpoint.py, layers/
vggt/                   vendored VGGT backbone (aggregator, DINOv2 patch embed, DPT head, pose encoding)
data/                   data_module.py, normalization.py, preprocessing.py, camera_utils.py, sources/{camxtime,kubric4d,nvidia}.py
eval/                   metrics.py (PSNR/SSIM/LPIPS) and vis.py (grids) used by train.py validation
benchmark/              final multi-model evaluation (FL4N + MoVieS / NeoVerse / 4DGT / C4G), see benchmark/README.md
checkpoints/            fl4n.ckpt (git-ignored)
```

## ⚙️ Setup
```bash
git clone https://github.com/eunbeen-hong/FL4N.git
cd FL4N
conda create -n fl4n python=3.11 && conda activate fl4n
pip install torch torchvision          # a CUDA build of PyTorch first
pip install -r requirements.txt
```
Recommended for every run:
```bash
export PYTHONNOUSERSITE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export HF_HOME=/path/to/hf_cache HF_HUB_OFFLINE=1      # cached DINOv2 / LPIPS / VGG weights
```

**Checkpoint.** `checkpoints/fl4n.ckpt` holds every weight of the reported model (frozen static
encoder + renderer, dynamic encoder, time module, gate, mask head; fp32, step 32k). It is both the
inference checkpoint and the initialisation for training (`model.pretrained_path`, or `FL4N_CKPT`).
```python
from models.checkpoint import load_checkpoint
model, step = load_checkpoint("checkpoints/fl4n.ckpt", "cuda")
out = model(images, rays, cam_token, num_cond_views=K, tau=tau)   # [b, K + T, 3, H, W]
```
Training checkpoints contain only the trainable modules; merge one into a full checkpoint with
`python -m models.checkpoint <exp>/checkpoints/step=N.ckpt checkpoints/fl4n.ckpt` (`load_checkpoint`
also accepts them directly).

**Data.** All data lives under one directory, `FL4N_DATA` (default `./data`), one subdirectory per
dataset; there are no other paths in the code. Datasets are mirrored at
[pancakesonmonday/4D_dataset](https://huggingface.co/datasets/pancakesonmonday/4D_dataset/tree/main);
extract each archive into its own subdirectory (`cat CamxTime.tar.* | tar xf - -C $FL4N_DATA`).
```
$FL4N_DATA/
  CamxTime/  Kubric4D/{train,test}/  NVIDIA/  N3DV/  Charge_v1_0/  ADT/  DyCheck/  TUM/
  camxtime_waft_masks_thr040_g16/  kubric4d_waft_masks_thr50_g4/  kubric4d_waft_masks_thr80_g8/
  vggt_poses/{ctvs,nvs,n3dv_nvs,nts}/      VGGT camera estimates used by the benchmark on real scenes
  _cache/                                   written by the benchmark loaders (N3DV frame cache)
```

Training uses CamXTime (1500 sequences, 90/10 scene split; primary set + validation), Kubric4D train
(2520 scenes, secondary set mixed 1:1), and Kubric4D test + NVIDIA for validation. The `*_waft_masks_*`
directories are flow-based dynamic masks (bit-packed npz; CamXTime 0.4 px / gap 16, Kubric4D 5 px / gap 4
and 8 px / gap 8) that drive the dynamic-region losses and the mask head.

## 🏋️ Train
```bash
python train.py                                   # 4 GPUs, bf16-mixed, 250k steps
python train.py devices=1 data.batch_size=1       # any key of configs/config.yaml can be overridden
python train.py experiment_path=<dir> ckpt_path=<dir>/checkpoints/last.ckpt   # resume
python train.py mode=eval ckpt_path=<ckpt> eval_out=val.json                    # validation only
```
Recipe: CamXTime (primary) + Kubric4D (secondary, resampled 1:1), input 336x512, 8 conditioning views,
12 targets per sample (6 transport / 2 novel-view / 4 novel-time at 1/4, 1/2, 3/4 of a conditioning gap),
conditioning poses zeroed with probability 0.4. AdamW lr 3.5e-5, weight decay 0.05, betas (0.9, 0.95),
cosine with 3000 warmup steps, grad clip 3.0, batch 2 per GPU x 4 GPUs. Frozen: static encoder, renderer.
Trainable: dynamic encoder (incl. patch embed), time module, gate, mask head. The reported model is step 32k.

## 📏 Evaluate
Baselines are expected under `FL4N_BASELINES` (default `./baselines`): the four repos `MoVieS/`, `NeoVerse/`,
`4DGT/`, `C4G/` and their checkpoints in `weights/<model>/`. Results go to `BENCH_OUT_ROOT` (default `./benchmark_out`).
```bash
python benchmark/run_eval.py --models fl4n movies neoverse 4dgt c4g --gpus 0 1 2 3   # all protocols, pose-free FL4N
python benchmark/run_eval.py --models fl4n --posed --gpus 0 1 2 3                    # FL4N with conditioning poses
python benchmark/runners/bench_fl4n.py --dataset kubric4d [--posed]                  # one dataset, this env only
```
Protocols, baseline footing and per-cell settings: `benchmark/README.md`, `benchmark/settings.py`.

## 📝 Citation

```bibtex
@article{hong2026fl4n,
  title   = {FL4N: Feed-forward Latent Model for 4D Novel View Synthesis},
  author  = {Hong, Eunbeen and Yu, Hyeonseo and Son, Soowon and Kim, Chaehyun and Koo, Jahyeok and Kim, Jisoo and Hur, Junhwa and Kim, Seungryong},
  journal = {arXiv preprint},
  year    = {2026}
}
```

## 🙏 Acknowledgements

The static backbone builds on [VGGT](https://github.com/facebookresearch/vggt), vendored under `vggt/`. The benchmark
runs the official MoVieS, NeoVerse, 4DGT and C4G code from their authors' repositories; see `benchmark/README.md`.
