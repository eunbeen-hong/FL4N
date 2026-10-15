"""Protocol-compliant CamXTime dataset loader (data loading + protocol index selection)."""

import os
from bench_static_util import maybe_static  # noqa: E402
import json

import numpy as np
import bench_nvs8 as _V8

try:
    import cv2
except Exception as _e:  # pragma: no cover
    cv2 = None

# Constants
from bench_paths import dataset  # noqa: E402
ROOT = str(dataset("CamxTime"))
NATIVE = 512                       # native square resolution
N_FRAMES = 120                     # time frames per mp4
# CX_K / CX_STRIDE: input-count sweep knobs. Defaults reproduce the reported protocol exactly
K_COND = int(os.environ.get("CX_K", "8"))          # conditioning views
_SPAN = int(os.environ.get("CX_SPAN", "56"))       # cond extent in slots (stride*(K-1))
_auto = max(1, _SPAN // max(1, K_COND - 1)) if K_COND > 1 else 8
CAM_STRIDE = int(os.environ.get("CX_STRIDE", str(_auto)))    # camera-position stride
FRAME_STRIDE = int(os.environ.get("CX_STRIDE", str(_auto)))  # temporal stride
TRAIN_FRAC = 0.9                   # cross_scene split (train_frac 0.9 -> 10% test holdout)

CAM_KEY_OFFSET = 32                # trajectory JSON key = str(32 + cam_number)
_BLENDER_TO_OPENCV = np.diag([1.0, -1.0, -1.0]).astype(np.float32)
# NOTE: CamXTime dyn-PSNR is intentionally NOT reported — its only dynamic mask is a RANSAC

# Protocol trajectory roles: cond diagonal lives on trajectory-01; the held-out
COND_TRAJ = "camera-trajectory-01"
NOVEL_TRAJ = "camera-trajectory-03"

# --- Table 2 (novel-view / held-out interior trajectory): {0,2} -> 1 ---
T2_TRAJ = COND_TRAJ                # NVS uses trajectory-01 only, same as CTVS
K_COND_T2 = 8


# Pose math (reused convention)
def _blender_c2w_to_opencv(c2w):
    """Blender world c2w -> OpenCV c2w (negate rotation columns 1 and 2)."""
    out = np.array(c2w, dtype=np.float32).copy()
    out[:3, :3] = out[:3, :3] @ _BLENDER_TO_OPENCV
    return out


# Cross-scene test split (matches camxtime_dataset._initialize_sequences)
def _usable_scenes(root):
    """Scenes that contribute >=1 valid sequence: a trajectory with its camera JSON and >=2 cam*_full_motion.mp4 files (exactly the split's usability rule)."""
    scenes = []
    for scene in sorted(os.listdir(root)):
        sdir = os.path.join(root, scene)
        if not (scene.lower().startswith("scene") and os.path.isdir(sdir)):
            continue
        ok = False
        for traj in sorted(os.listdir(sdir)):
            tdir = os.path.join(sdir, traj)
            if not (traj.startswith("camera-trajectory-") and os.path.isdir(tdir)):
                continue
            jpath = os.path.join(tdir, f"{traj}-camera.json")
            if not os.path.isfile(jpath):
                continue
            n_mp4 = sum(
                1 for f in os.listdir(tdir)
                if f.startswith("cam") and f.endswith("_full_motion.mp4")
            )
            if n_mp4 >= 2:
                ok = True
                break
        if ok:
            scenes.append(scene)
    return scenes


def list_test_scenes(root=ROOT):
    """Cross-scene 10% holdout: sorted scenes, cut=int(N*0.9), test=scenes[cut:]."""
    scenes = _usable_scenes(root)
    cut = int(len(scenes) * TRAIN_FRAC)
    return scenes[cut:]


# Trajectory / camera helpers
def _traj_dir(root, scene, traj):
    return os.path.join(root, scene, traj)


def _read_traj_json(root, scene, traj):
    p = os.path.join(_traj_dir(root, scene, traj), f"{traj}-camera.json")
    with open(p) as f:
        return json.load(f)


def _cam_numbers(root, scene, traj):
    """Sorted camera numbers (1-indexed) present as mp4 in the trajectory folder."""
    tdir = _traj_dir(root, scene, traj)
    nums = []
    for f in sorted(os.listdir(tdir)):
        if f.startswith("cam") and f.endswith("_full_motion.mp4"):
            nums.append(int(f[3:6]))
    return nums


def _mp4_path(root, scene, traj, cam_number):
    return os.path.join(_traj_dir(root, scene, traj), f"cam{cam_number:03d}_full_motion.mp4")


def _K_from_json(js):
    """3x3 intrinsics for native 512x512 (JSON is already at 512)."""
    return np.array(js["intrinsics"]["K"], dtype=np.float32)


def _pose_opencv(js, cam_number):
    """OpenCV c2w (4x4) for a camera position; pose is time-independent."""
    traj = js["trajectory"]
    key = str(CAM_KEY_OFFSET + cam_number)
    if key not in traj:
        traj_keys = sorted(traj, key=int)
        key = traj_keys[(cam_number - 1) % len(traj_keys)]
    return _blender_c2w_to_opencv(traj[key]["c2w"])


# Protocol index selection (cond diagonal + transport + novel-view)
def _cond_indices(num_cam=N_FRAMES, num_frame=N_FRAMES, k=K_COND):
    """cam_select=stride, endpoints anchored: evenly-strided camera positions and frames via round(linspace), first & last anchored. Diagonal: view i = cam[i]@t[i]."""
    cam_slots = [CAM_STRIDE * i for i in range(k)]
    frames = [FRAME_STRIDE * i for i in range(k)]
    if cam_slots[-1] >= num_cam or frames[-1] >= num_frame:
        raise RuntimeError(f"camxtime: stride {CAM_STRIDE}/{FRAME_STRIDE} x k={k} exceeds {num_cam}/{num_frame}")
    return cam_slots, frames


def _target_index_plan(cam_slots, frames):
    """Deterministic transport + novel-view plans (80/20 known-time targets)."""
    k = len(cam_slots)
    transport = [(cam_slots[i], frames[j]) for i in range(k) for j in range(k) if i != j]

    # in-between (in-span) held-out camera slots: midpoints of consecutive cond slots
    mid_slots = np.round(
        (np.array(cam_slots[:-1]) + np.array(cam_slots[1:])) / 2.0
    ).astype(int).tolist()
    novel = []
    for i, ms in enumerate(mid_slots):
        novel.append((ms, frames[i]))       # bracketing cond time (left)
        novel.append((ms, frames[i + 1]))   # bracketing cond time (right)
    return transport, novel


# Frame decoding (cv2; only the needed frames)
def _decode_frames(mp4_path, frame_idxs):
    """Return {frame_idx: HxWx3 float32 RGB [0,1]} for the requested indices."""
    if cv2 is None:
        raise RuntimeError("cv2 unavailable; cannot decode mp4")
    want = sorted({int(t) for t in frame_idxs})
    max_t = want[-1]
    want_set = set(want)
    out = {}
    cap = cv2.VideoCapture(mp4_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {mp4_path}")
    i = 0
    try:
        while i <= max_t:
            ok, bgr = cap.read()
            if not ok:
                break
            if i in want_set:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                out[i] = (rgb.astype(np.float32) / 255.0)
            i += 1
    finally:
        cap.release()
    if not out:
        raise RuntimeError(f"decoded no frames from {mp4_path}")
    last = out[max(out)]
    return {t: out.get(t, last) for t in want}   # graceful fallback for short clips


# Deliverable
def load_camxtime_scene(scene, root=ROOT):
    """Load one CamXTime scene into protocol tensors."""
    # === Table 2 (novel-view / held-out interior trajectory): {0,2} -> 1 ===
    if os.environ.get("BENCH_TABLE2"):
        js = _read_traj_json(root, scene, T2_TRAJ)
        cams = _cam_numbers(root, scene, T2_TRAJ)
        Kmat = _K_from_json(js)
        cond_slots, tgt_slot = _V8.window9(list(range(len(cams))), CAM_STRIDE)
        times = [FRAME_STRIDE * i for i in range(K_COND_T2)]
        # input-config sweep knobs (same semantics as bench_ds_kubric4d / bench_ds_nvidia)
        if os.environ.get("T2_COND_IDX"):
            _ix = [int(x) for x in os.environ["T2_COND_IDX"].split(",")]
            cond_slots = [cond_slots[i] for i in _ix]
        if os.environ.get("T2_COND_TIMES"):
            times = [int(x) for x in os.environ["T2_COND_TIMES"].split(",")]
        assert len(times) == len(cond_slots), "T2 cond times must match cond slot count"
        tgt_times = ([int(x) for x in os.environ["T2_TGT_TIMES"].split(",")]
                     if os.environ.get("T2_TGT_TIMES") else list(times))
        need = {}
        for i, sl in enumerate(cond_slots):
            need.setdefault(cams[sl], set()).add(times[i])
        need.setdefault(cams[tgt_slot], set()).update(tgt_times)
        dec = {cn: _decode_frames(_mp4_path(root, scene, T2_TRAJ, cn), fs) for cn, fs in need.items()}
        cond = []
        for i, sl in enumerate(cond_slots):
            cn = cams[sl]
            cond.append({"image": dec[cn][times[i]], "c2w": _pose_opencv(js, cn), "K": Kmat.copy(),
                         "cam": sl, "frame": times[i], "traj": T2_TRAJ, "cam_number": cn})
        cn = cams[tgt_slot]
        targets_all = [{"gt": dec[cn][t], "c2w": _pose_opencv(js, cn), "K": Kmat.copy(),
                        "cam": tgt_slot, "frame": t, "dyn_mask": None,
                        "traj": T2_TRAJ, "cam_number": cn} for t in tgt_times]
        meta = {"scene": scene, "native_hw": (NATIVE, NATIVE), "table": "T2", "traj": T2_TRAJ,
                "cond_slots": cond_slots, "tgt_slot": tgt_slot, "times": times, "dyn_mask": None}
        return maybe_static({"cond": cond, "targets": {"all": targets_all}, "meta": meta})

    cond_js = _read_traj_json(root, scene, COND_TRAJ)
    novel_js = _read_traj_json(root, scene, NOVEL_TRAJ)
    cond_cams = _cam_numbers(root, scene, COND_TRAJ)
    novel_cams = _cam_numbers(root, scene, NOVEL_TRAJ)

    num_cam = len(cond_cams)
    cam_slots, frames = _cond_indices(num_cam=num_cam, num_frame=N_FRAMES, k=K_COND)
    transport_plan, novel_plan = _target_index_plan(cam_slots, frames)

    K_cond = _K_from_json(cond_js)
    K_novel = _K_from_json(novel_js)

    # --- gather the frames each mp4 must yield, then decode once per mp4 --------
    need = {}  # (traj, cam_number) -> set(frame_idx)

    def _add(traj, cam_number, frame):
        need.setdefault((traj, cam_number), set()).add(int(frame))

    for i in range(K_COND):
        _add(COND_TRAJ, cond_cams[cam_slots[i]], frames[i])
    for (slot, fr) in transport_plan:
        _add(COND_TRAJ, cond_cams[slot], fr)
    for (slot, fr) in novel_plan:
        _add(NOVEL_TRAJ, novel_cams[slot], fr)

    decoded = {}
    for (traj, cam_number), fs in need.items():
        decoded[(traj, cam_number)] = _decode_frames(
            _mp4_path(root, scene, traj, cam_number), fs
        )

    # --- conditioning (diagonal) ----------------------------------------------
    cond = []
    for i in range(K_COND):
        slot = cam_slots[i]
        cam_number = cond_cams[slot]
        fr = frames[i]
        cond.append({
            "image": decoded[(COND_TRAJ, cam_number)][fr],
            "c2w": _pose_opencv(cond_js, cam_number),
            "K": K_cond.copy(),
            "cam": int(slot),               # camera-position slot on the cond trajectory
            "frame": int(fr),
            "traj": COND_TRAJ,
            "cam_number": int(cam_number),
        })

    # --- transport targets -----------------------------------------------------
    transport = []
    for (slot, fr) in transport_plan:
        cam_number = cond_cams[slot]
        transport.append({
            "cam": int(slot),
            "frame": int(fr),
            "c2w": _pose_opencv(cond_js, cam_number),
            "K": K_cond.copy(),
            "gt": decoded[(COND_TRAJ, cam_number)][fr],
            "dyn_mask": None,
            "traj": COND_TRAJ,
            "cam_number": int(cam_number),
        })

    # --- novel-view targets (held-out trajectory) ------------------------------
    novel_view = []
    for (slot, fr) in novel_plan:
        cam_number = novel_cams[slot]
        novel_view.append({
            "cam": int(slot),
            "frame": int(fr),
            "c2w": _pose_opencv(novel_js, cam_number),
            "K": K_novel.copy(),
            "gt": decoded[(NOVEL_TRAJ, cam_number)][fr],
            "dyn_mask": None,
            "traj": NOVEL_TRAJ,
            "cam_number": int(cam_number),
        })

    meta = {
        "scene": scene,
        "root": root,
        "native_hw": (NATIVE, NATIVE),
        "num_frames": N_FRAMES,
        "cond_traj": COND_TRAJ,
        "novel_traj": NOVEL_TRAJ,
        "cond_cam_slots": list(cam_slots),
        "cond_frames": list(frames),
        "counts": {
            "cond": len(cond),
            "transport": len(transport),
            "novel_view": len(novel_view),
        },
        "target_ratio_transport_novel": "80/20",
        "pose_convention": "OpenCV c2w (Blender->OpenCV via negating rot cols 1,2)",
        "known_time": True,
        "dyn_mask": None,
        "dyn_mask_note": "RANSAC pseudo-mask (r004_m008_d2_h128) NOT generated; add later for dyn-PSNR.",
        "split": {"mode": "cross_scene", "train_frac": TRAIN_FRAC},
    }
    # New protocol: targets = K×K off-diagonal only (transport), single group "all"; novel-view dropped.
    return maybe_static({"cond": cond, "targets": {"all": transport}, "meta": meta})


# Validation (no model): load 1 test scene, print stats, save a montage
def _cam_center(c2w):
    return np.asarray(c2w)[:3, 3]
