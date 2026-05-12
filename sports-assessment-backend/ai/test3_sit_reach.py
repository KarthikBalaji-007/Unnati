"""
test3_sit_reach.py
------------------
Test 3 – Sit & Reach (Flexibility)

Algorithm (SRS §5.2, Test 3):
  1. Detect stable seated baseline: hip-knee angle ≈ 90–110°, knee-ankle nearly straight.
  2. Identify the frame with maximum wrist forward x-displacement relative to ankle (the
     furthest reach point).
  3. Validate knees remain extended (angle > 150° = nearly straight legs) and no bouncing
     (single global maximum, not multiple spikes).
  4. Calibrate reach using the body-relative ankle-to-hip vertical span as scale reference:
       reach_norm = (wrist_x - ankle_x) / body_height_px_norm
       reach_cm   ≈ reach_norm * BODY_REF_CM
     Since we don't have a ruler in frame, we use median hip-to-ankle distance in normalized
     coords as the calibration reference (adult hip-to-ankle ≈ 55 cm).

Keypoints used: left/right hip, knee, ankle, wrist (preferring the side closer to camera).
"""

import numpy as np
from typing import Any

from ai.pose_extractor import (
    PoseFrame, get_accepted_frames, landmark_xy, avg_landmark_xy,
    compute_angle_3pts, moving_average, LM
)

# ─── Constants ────────────────────────────────────────────────────────────────
# Real-world reference: typical adult hip-to-ankle distance ≈ 0.55 m (55 cm).
# This is used as a body-relative calibration baseline.
BODY_REF_HIP_ANKLE_CM = 55.0

# During seated pose, hip-knee angle should be roughly 90–110°
SEATED_HIP_KNEE_MIN = 80.0
SEATED_HIP_KNEE_MAX = 120.0

# Knee must stay extended during reach phase. MediaPipe side-view estimates are
# often 5-10 degrees low when legs are slightly rotated, so keep a tolerance.
KNEE_EXTENDED_THRESHOLD = 145.0  # degrees

# Min fraction of frames that must be in seated pose to declare a valid attempt
MIN_SEATED_FRACTION = 0.25

# Minimum raw reach (normalized) to be above noise floor
MIN_REACH_NORM = 0.01

# Attempts are separated by dropping meaningfully below the best reach. This
# lets demo videos contain several trials while still scoring one clean reach.
REACH_ATTEMPT_FRACTION = 0.55


def analyze(pose_frames: list[PoseFrame], video_info: dict) -> dict[str, Any]:
    """
    Run the Sit & Reach analyzer on extracted pose frames.

    Returns a dict matching MetricResult schema.
    """
    accepted = get_accepted_frames(pose_frames)

    if len(accepted) < 10:
        return _failure("Too few high-confidence frames detected. Please retake with better lighting and camera angle.")

    fps = video_info.get("fps", 30.0)

    # ── Step 1: Compute per-frame metrics ────────────────────────────────────
    left_knee_angles: list[float] = []
    right_knee_angles: list[float] = []
    left_reach_vals: list[float] = []
    right_reach_vals: list[float] = []
    left_hip_ankle_norms: list[float] = []
    right_hip_ankle_norms: list[float] = []

    for f in accepted:
        lh = landmark_xy(f, "left_hip")
        lk = landmark_xy(f, "left_knee")
        la = landmark_xy(f, "left_ankle")
        lw = landmark_xy(f, "left_wrist")
        rh = landmark_xy(f, "right_hip")
        rk = landmark_xy(f, "right_knee")
        ra = landmark_xy(f, "right_ankle")
        rw = landmark_xy(f, "right_wrist")

        left_knee_angles.append(compute_angle_3pts(lh, lk, la))
        right_knee_angles.append(compute_angle_3pts(rh, rk, ra))
        left_reach_vals.append(lw[0] - la[0])
        right_reach_vals.append(rw[0] - ra[0])
        left_hip_ankle_norms.append(float(np.linalg.norm(np.array(lh) - np.array(la))))
        right_hip_ankle_norms.append(float(np.linalg.norm(np.array(rh) - np.array(ra))))

    # ── Step 2: Smooth wrist signal ───────────────────────────────────────────
    side = _select_side(left_hip_ankle_norms, right_hip_ankle_norms)
    if side == "left":
        knee_angles = left_knee_angles
        hip_ankle_norms = left_hip_ankle_norms
        raw_reach = left_reach_vals
    else:
        knee_angles = right_knee_angles
        hip_ankle_norms = right_hip_ankle_norms
        raw_reach = right_reach_vals

    reach_signals = moving_average(raw_reach, window=5)
    if abs(min(reach_signals)) > abs(max(reach_signals)):
        reach_signals = [-r for r in reach_signals]
    knee_extended_flags = [angle > KNEE_EXTENDED_THRESHOLD for angle in knee_angles]

    # ── Step 3: Detect seated phase ───────────────────────────────────────────
    # NOTE: In sit-and-reach, the person is seated with legs extended, so the hip-knee
    # angle is actually around 160–180° (nearly flat). We adjust the check: look for
    # frames where hip y and knee y are similar (both on the ground).
    seated_mask = [
        abs(knee_angles[i] - 170.0) < 30.0  # legs extended, roughly straight
        for i in range(len(accepted))
    ]
    seated_count = sum(seated_mask)
    seated_fraction = seated_count / len(accepted)

    if seated_fraction < MIN_SEATED_FRACTION:
        return _failure(
            f"Could not detect a proper seated position. Ensure the athlete is seated "
            f"with legs extended, facing the camera from the side."
        )

    # ── Step 4: Find and score individual reach attempts ──────────────────────
    seated_reach = [reach_signals[i] if seated_mask[i] else -999 for i in range(len(accepted))]
    global_peak_reach = float(max(seated_reach))

    if global_peak_reach < MIN_REACH_NORM:
        return _failure("Wrist did not move forward significantly. Could not detect a reach attempt.")

    attempt_threshold = max(MIN_REACH_NORM, global_peak_reach * REACH_ATTEMPT_FRACTION)
    attempt_indices = [i for i, r in enumerate(seated_reach) if r >= attempt_threshold]
    attempt_groups = _contiguous_groups(attempt_indices, max_gap=max(2, int(0.20 * fps)))
    candidates = []
    for group in attempt_groups:
        peak_idx = max(group, key=lambda i: seated_reach[i])
        peak_reach_norm = reach_signals[peak_idx]
        local_high = [i for i in group if reach_signals[i] > 0.9 * peak_reach_norm]
        span_seconds = ((local_high[-1] - local_high[0]) / fps) if local_high else 0.0
        candidates.append({
            "group": group,
            "peak_idx": peak_idx,
            "peak_reach_norm": peak_reach_norm,
            "bouncing": span_seconds > 2.0,
            "span_seconds": span_seconds,
        })

    if not candidates:
        return _failure("Detected seated pose, but no reach attempt could be isolated.")

    best = max(candidates, key=lambda c: c["peak_reach_norm"])
    peak_idx = best["peak_idx"]
    peak_reach_norm = best["peak_reach_norm"]
    bouncing = best["bouncing"]

    # ── Step 6: Validate – knee must be extended at peak ─────────────────────
    knee_at_peak = knee_extended_flags[peak_idx]

    valid = knee_at_peak and not bouncing

    # ── Step 7: Convert to cm ─────────────────────────────────────────────────
    reference_indices = [i for i, is_seated in enumerate(seated_mask) if is_seated]
    median_hip_ankle_norm = float(np.median([hip_ankle_norms[i] for i in reference_indices]))
    if median_hip_ankle_norm < 1e-4:
        return _failure("Could not compute body scale reference. Ensure full body is visible.")

    # reach_norm relative to body height unit
    reach_relative = peak_reach_norm / median_hip_ankle_norm
    reach_cm = reach_relative * BODY_REF_HIP_ANKLE_CM

    # ── Step 8: Confidence ────────────────────────────────────────────────────
    mean_conf = float(np.mean([f.frame_confidence for f in accepted]))
    confidence = _compute_confidence(mean_conf, seated_fraction, valid)

    return {
        "primary_metric": round(reach_cm, 1),
        "secondary_metrics": {
            "reach_normalized": round(peak_reach_norm, 4),
            "seated_frame_fraction": round(seated_fraction, 2),
            "knee_extended_at_peak": knee_at_peak,
            "bouncing_detected": bouncing,
            "peak_frame_idx": accepted[peak_idx].frame_idx,
            "total_accepted_frames": len(accepted),
            "attempts_detected": len(candidates),
            "selected_attempt_start_frame": accepted[best["group"][0]].frame_idx,
            "selected_attempt_end_frame": accepted[best["group"][-1]].frame_idx,
            "body_side_used": side,
        },
        "valid": valid,
        "confidence_score": confidence,
        "cheat_flags": _get_cheat_flags(bouncing, seated_fraction, mean_conf),
        "cheat_score": _get_cheat_score(bouncing, seated_fraction, mean_conf),
        "debug_info": {
            "knee_angle_range": [round(min(knee_angles), 1), round(max(knee_angles), 1)],
            "reach_signal_max": round(max(reach_signals), 4),
            "body_ref_norm": round(median_hip_ankle_norm, 4),
        },
    }


def _select_side(left_refs: list[float], right_refs: list[float]) -> str:
    left_med = float(np.median(left_refs))
    right_med = float(np.median(right_refs))
    return "left" if left_med >= right_med else "right"


def _contiguous_groups(indices: list[int], max_gap: int = 1) -> list[list[int]]:
    if not indices:
        return []
    groups = [[indices[0]]]
    for idx in indices[1:]:
        if idx - groups[-1][-1] <= max_gap:
            groups[-1].append(idx)
        else:
            groups.append([idx])
    return groups


def _compute_confidence(mean_conf: float, seated_fraction: float, valid: bool) -> float:
    conf = mean_conf * 0.5 + min(seated_fraction / 0.5, 1.0) * 0.3 + (0.2 if valid else 0.0)
    return round(min(max(conf, 0.0), 1.0), 3)


def _get_cheat_flags(bouncing: bool, seated_fraction: float, mean_conf: float) -> list[str]:
    flags = []
    if bouncing:
        flags.append("bouncing_detected")
    if seated_fraction < 0.3:
        flags.append("insufficient_seated_frames")
    if mean_conf < 0.6:
        flags.append("low_pose_confidence")
    return flags


def _get_cheat_score(bouncing: bool, seated_fraction: float, mean_conf: float) -> float:
    score = 0.0
    if bouncing:
        score += 0.4
    if seated_fraction < 0.3:
        score += 0.3
    if mean_conf < 0.5:
        score += 0.3
    return round(min(score, 1.0), 3)


def _failure(reason: str) -> dict[str, Any]:
    return {
        "primary_metric": None,
        "secondary_metrics": {"failure_reason": reason},
        "valid": False,
        "confidence_score": 0.0,
        "cheat_flags": ["analysis_failed"],
        "cheat_score": 0.0,
        "debug_info": {"error": reason},
    }
