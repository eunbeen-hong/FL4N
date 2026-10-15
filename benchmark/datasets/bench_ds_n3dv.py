#!/usr/bin/env python3
"""Protocol-compliant N3DV (DyNeRF) dataset loader (feed-forward NVS eval)."""
import os
import glob

import numpy as np
import cv2


from bench_paths import dataset  # noqa: E402
N3DV_ROOT = str(dataset("N3DV"))
N3DV_SCENES = [
    "coffee_martini", "cook_spinach", "cut_roasted_beef",
    "flame_steak", "sear_steak", "flame_salmon_1",
]
N3DV_K_COND = 12


# Pose / intrinsics                                                            #
def llff_to_opencv_c2w(pose_3x5: np.ndarray) -> np.ndarray:
    """LLFF `poses_bounds` 3x5 [R|t|hwf] -> 4x4 OpenCV camera-to-world."""
    R = pose_3x5[:, :3]
    t = pose_3x5[:, 3]
    c0, c1, c2 = R[:, 0], R[:, 1], R[:, 2]
    R_cv = np.stack([c1, c0, -c2], axis=1)  # columns -> [right, down, forward]
    c2w = np.eye(4, dtype=np.float64)
    c2w[:3, :3] = R_cv
    c2w[:3, 3] = t
    return c2w


def _n3dv_intrinsics(hwf: np.ndarray, eval_hw) -> np.ndarray:
    """3x3 K for eval_hw from LLFF hwf=[H_native,W_native,focal_native]."""
    H_n, W_n, f_n = float(hwf[0]), float(hwf[1]), float(hwf[2])
    H_e, W_e = eval_hw
    sx, sy = W_e / W_n, H_e / H_n
    return np.array([[f_n * sx, 0.0, 0.5 * W_n * sx],
                     [0.0, f_n * sy, 0.5 * H_n * sy],
                     [0.0, 0.0, 1.0]], dtype=np.float64)


# Frame decoding (only the needed frames)                                     #
def _decode_frame(video_path, frame_idx, eval_hw):
    """Decode ONE frame -> HxWx3 float32 RGB in [0,1] resized to eval_hw."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
    ok, bgr = cap.read()
    cap.release()
    if not ok or bgr is None:
        raise RuntimeError(f"failed to read frame {frame_idx} from {video_path}")
    H_e, W_e = eval_hw
    if (bgr.shape[0], bgr.shape[1]) != (H_e, W_e):
        bgr = cv2.resize(bgr, (W_e, H_e), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return rgb.astype(np.float32) / 255.0


class LazyGT:
    """Lazily-decoded GT frame; behaves like an ndarray."""

    def __init__(self, video_path, frame_idx, eval_hw):
        self.video_path = video_path
        self.frame_idx = int(frame_idx)
        self.eval_hw = tuple(eval_hw)
        self._arr = None

    @property
    def shape(self):
        return (self.eval_hw[0], self.eval_hw[1], 3)

    def load(self):
        if self._arr is None:
            self._arr = _decode_frame(self.video_path, self.frame_idx, self.eval_hw)
        return self._arr

    def free(self):
        self._arr = None

    def __call__(self):
        return self.load()

    def __array__(self, dtype=None):
        a = self.load()
        return a.astype(dtype) if dtype is not None else a


# Protocol index selection                                                     #
def n3dv_cond_indices(n_cams, clip_len):
    """(cond_cams, cond_times) for the N x N CTVS grid."""
    if os.environ.get("N3DV_ALLCAM", "1") == "0":
        cams = np.round(np.linspace(0, n_cams - 1, N3DV_K_COND)).astype(int).tolist()
        times = np.round(np.linspace(0, clip_len - 1, N3DV_K_COND)).astype(int).tolist()
        return cams, times
    cams = list(range(1, n_cams))                       # all cameras except cam0
    N = len(cams)
    times = np.round(np.linspace(0, clip_len - 1, N)).astype(int).tolist()
    return cams, times


def n3dv_target_indices(n_cams, cond_cams, cond_times):
    """{"novel_view":[(cam,time),...], "transport":[(cam,time),...]}."""
    cond_cam_set = set(cond_cams)
    held_out = [c for c in range(n_cams) if c not in cond_cam_set]
    cond_time_set = sorted(set(cond_times))
    novel = [(c, t) for c in held_out for t in cond_time_set]
    transport = []
    for i, cam in enumerate(cond_cams):
        own_time = cond_times[i]
        for t in cond_times:
            if t != own_time:
                transport.append((cam, t))
    return {"novel_view": novel, "transport": transport}


def _cam_files(scene_dir):
    files = sorted(glob.glob(os.path.join(scene_dir, "cam*.mp4")))
    if not files:
        raise FileNotFoundError(f"no cam*.mp4 in {scene_dir}")
    return files


# Loader                                                                       #
def load_n3dv_scene(scene: str, eval_hw=(1014, 1352),
                    root: str = N3DV_ROOT, lazy_gt: bool = True) -> dict:
    """Load one N3DV/DyNeRF scene per the eval protocol (no model inference)."""
    scene_dir = os.path.join(root, scene)
    if not os.path.isdir(scene_dir):
        raise FileNotFoundError(f"scene dir not found: {scene_dir}")

    cam_files = _cam_files(scene_dir)
    n_cams = len(cam_files)

    pb = np.load(os.path.join(scene_dir, "poses_bounds.npy"))
    if pb.shape[0] != n_cams:
        raise ValueError(
            f"{scene}: poses_bounds rows ({pb.shape[0]}) != n cam*.mp4 ({n_cams})")
    poses = pb[:, :15].reshape(-1, 3, 5)
    bounds = pb[:, 15:]

    c2ws = [llff_to_opencv_c2w(poses[i]) for i in range(n_cams)]
    Ks = [_n3dv_intrinsics(poses[i, :, 4], eval_hw) for i in range(n_cams)]

    cap = cv2.VideoCapture(cam_files[0])
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {cam_files[0]}")
    W_n = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H_n = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    clip_len = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    cond_cams, cond_times = n3dv_cond_indices(n_cams, clip_len)
    tgt_idx = n3dv_target_indices(n_cams, cond_cams, cond_times)

    cond = []
    for i in range(N3DV_K_COND):
        cam, t = cond_cams[i], cond_times[i]
        cond.append({
            "image": _decode_frame(cam_files[cam], t, eval_hw),
            "c2w": c2ws[cam].copy(),
            "K": Ks[cam].copy(),
            "time": int(t),
            "cam": int(cam),
        })

    def _make_target(cam, t):
        gt = LazyGT(cam_files[cam], t, eval_hw)
        return {
            "cam": int(cam), "time": int(t),
            "c2w": c2ws[cam].copy(), "K": Ks[cam].copy(),
            "gt": gt if lazy_gt else gt.load(),
        }

    targets = {
        "novel_view": [_make_target(c, t) for (c, t) in tgt_idx["novel_view"]],
        "transport": [_make_target(c, t) for (c, t) in tgt_idx["transport"]],
    }

    meta = {
        "scene": scene,
        "n_cams": n_cams,
        "clip_len": clip_len,
        "native_hw": (H_n, W_n),
        "eval_hw": tuple(eval_hw),
        "cam_files": [os.path.basename(f) for f in cam_files],
        "cond_cams": cond_cams,
        "cond_times": cond_times,
        "focal_native": float(poses[0, 2, 4]),
        "near": float(bounds.min()),
        "far": float(bounds.max()),
    }
    return {"cond": cond, "targets": targets, "meta": meta}


# Validation / sanity check (no model)                                         #
def _sanity_montage(data, out_png, eval_hw):
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    H, W = eval_hw
    tw = 320
    th = int(round(tw * H / W))

    def thumb(arr01, label):
        bgr = cv2.cvtColor((np.clip(arr01, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        bgr = cv2.resize(bgr, (tw, th), interpolation=cv2.INTER_AREA)
        cv2.putText(bgr, label, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(bgr, label, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1, cv2.LINE_AA)
        return bgr

    tiles = []
    for i in [0, 4, 8, 11]:
        cd = data["cond"][i]
        tiles.append(thumb(cd["image"], f"cond{i} c{cd['cam']} t{cd['time']}"))
    nv = data["targets"]["novel_view"][0]
    tiles.append(thumb(np.asarray(nv["gt"]), f"NV c{nv['cam']} t{nv['time']}"))
    tr = data["targets"]["transport"][0]
    tiles.append(thumb(np.asarray(tr["gt"]), f"TR c{tr['cam']} t{tr['time']}"))

    cols, pad = 3, 4
    rows = (len(tiles) + cols - 1) // cols
    grid = np.full(((th + pad) * rows + pad, (tw + pad) * cols + pad, 3), 255, np.uint8)
    for idx, t in enumerate(tiles):
        r, c = idx // cols, idx % cols
        y, x = pad + r * (th + pad), pad + c * (tw + pad)
        grid[y:y + th, x:x + tw] = t
    cv2.imwrite(out_png, grid)
    return out_png
