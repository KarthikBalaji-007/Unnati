"""
test5_broad_jump.py
--------------------
Test 5 – Standing Broad Jump

Algorithm (SRS §5.2, Test 5):
  1. Detect take-off frame: hip/ankle y-velocity goes sharply negative (rising up).
  2. Detect landing frame: after peak height, ankles return to ground and stabilize.
  3. Compute horizontal ankle displacement between take-off and landing frames.
  4. Calibrate using shoulder-width (left-to-right shoulder x distance) as body reference:
       shoulder_width_norm ≈ known ≈ 0.45 × (hip-to-ankle span)
     We use hip-to-ankle body-relative calibration (same as T4) for consistency.
       jump_cm = (ankle_dx / body_height_norm) * ADULT_HEIGHT_CM * FORWARD_RATIO

Keypoints: hip, ankle, heel, left/right shoulder.
"""

import numpy as np
from typing import Any

from ai.pose_extractor import (
    PoseFrame, get_accepted_frames, landmark_xy, avg_landmark_xy,
    moving_average, LM
)

# ─── Constants ────────────────────────────────────────────────────────────────
ADULT_HEIGHT_CM = 165.0

# Fraction of body height dedicated to leg length (knee to ankle ≈ 45 cm / 165 cm)
LEG_FRACTION = 0.55  # legs + hips as fraction of body height

# Velocity threshold for detecting takeoff (ankle rising)
TAKEOFF_VELOCITY_THRESH = -0.004

# Ground level tolerance — frames where ankle y is within this of max are "on ground"
GROUND_TOL = 0.06

SMOOTH_WINDOW = 4

MIN_JUMP_CM = 30.0     # unlikely to be below 30 cm for a valid broad jump
MAX_JUMP_CM = 350.0    # world record is ~3.73 m; cap at 350 cm for sanity
MIN_FLIGHT_DURATION_S = 0.12
MAX_FLIGHT_DURATION_S = 1.50


def analyze(pose_frames: list[PoseFrame], video_info: dict) -> dict[str, Any]:
    """Run the Standing Broad Jump analyzer."""
    accepted = get_accepted_frames(pose_frames)

    if len(accepted) < 15:
        return _failure("Too few high-confidence frames. Ensure full body and landing zone are visible.")

    fps = video_info.get("fps", 30.0)
    n = len(accepted)

    # ── Step 1: Extract trajectory signals ───────────────────────────────────
    ankle_y_raw: list[float] = []
    ankle_x_raw: list[float] = []
    hip_y_raw:   list[float] = []

    for f in accepted:
        ax, ay = avg_landmark_xy(f, "left_ankle", "right_ankle")
        _, hy  = avg_landmark_xy(f, "left_hip",   "right_hip")
        ankle_y_raw.append(ay)
        ankle_x_raw.append(ax)
        hip_y_raw.append(hy)

    ankle_y = moving_average(ankle_y_raw, SMOOTH_WINDOW)
    ankle_x = moving_average(ankle_x_raw, SMOOTH_WINDOW)
    hip_y   = moving_average(hip_y_raw,   SMOOTH_WINDOW)

    # Vertical velocity (negative = moving up)
    ankle_vel = [0.0] + [ankle_y[i] - ankle_y[i - 1] for i in range(1, n)]
    hip_vel   = [0.0] + [hip_y[i]   - hip_y[i - 1]   for i in range(1, n)]

    # ── Step 2: Detect standing baseline ─────────────────────────────────────
    ankle_y_max = max(ankle_y)
    ground_threshold = ankle_y_max - GROUND_TOL
    ground_mask = [ankle_y[i] >= ground_threshold for i in range(n)]

    baseline_ground = [i for i in range(n) if ground_mask[i] and i < n // 2]
    if len(baseline_ground) < 3:
        return _failure("Cannot detect initial standing position. Start the video 1–2 seconds before you jump.")

    # ── Step 3: Detect and score jump attempts ────────────────────────────────
    airborne_indices = [i for i in range(n) if not ground_mask[i]]
    flight_groups = _contiguous_groups(airborne_indices, max_gap=max(2, int(0.08 * fps)))
    candidates = []
    for group in flight_groups:
        candidate = _score_broad_jump_candidate(
            group=group,
            accepted=accepted,
            ankle_x=ankle_x,
            ankle_y=ankle_y,
            ground_mask=ground_mask,
            baseline_ground=baseline_ground,
            fps=fps,
        )
        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        return _failure("Could not isolate a complete broad jump attempt. Ensure takeoff and landing are visible.")

    plausible = [
        c for c in candidates
        if MIN_FLIGHT_DURATION_S <= c["flight_s"] <= MAX_FLIGHT_DURATION_S
        and MIN_JUMP_CM <= c["jump_cm"] <= MAX_JUMP_CM
        and c["airborne"]
    ]
    best = max(plausible or candidates, key=lambda c: c["jump_cm"])

    takeoff_idx = best["takeoff_idx"]
    landing_idx = best["landing_idx"]
    peak_idx = best["peak_idx"]
    dx_norm = best["dx_norm"]
    body_height_norm = best["body_height_norm"]
    jump_cm = best["jump_cm"]
    flight_s = best["flight_s"]

    # ── Step 4: Validate ──────────────────────────────────────────────────────
    valid = True
    validity_notes = []

    if jump_cm < MIN_JUMP_CM:
        valid = False
        validity_notes.append(f"Jump distance too small ({jump_cm:.1f} cm). Ensure camera captures full jump.")
    if jump_cm > MAX_JUMP_CM:
        valid = False
        validity_notes.append(f"Jump distance implausibly large ({jump_cm:.1f} cm). Check calibration/camera.")
    if flight_s < MIN_FLIGHT_DURATION_S or flight_s > MAX_FLIGHT_DURATION_S:
        valid = False
        validity_notes.append(f"Flight duration outside single-jump range ({flight_s:.2f}s).")

    airborne = best["airborne"]

    # Check landing stability (no early step) — standard deviation of ankle x after landing
    post_landing = ankle_x[landing_idx: min(landing_idx + 8, n)]
    landing_stability = float(np.std(post_landing)) if len(post_landing) > 2 else 0.0
    stable_landing = landing_stability < 0.04

    if not airborne:
        valid = False
        validity_notes.append("Athlete did not clearly leave the ground.")
    if not stable_landing:
        validity_notes.append("Landing instability detected (early step or stumble).")

    # ── Step 5: Confidence & cheat scores ─────────────────────────────────────
    mean_conf = float(np.mean([f.frame_confidence for f in accepted]))

    confidence = _compute_confidence(mean_conf, flight_s, valid, airborne)
    cheat_flags = _get_cheat_flags(jump_cm, mean_conf, airborne)
    cheat_score = _get_cheat_score(jump_cm, mean_conf, airborne)

    return {
        "primary_metric": round(max(jump_cm, 0.0), 1),
        "secondary_metrics": {
            "takeoff_frame_idx": accepted[takeoff_idx].frame_idx,
            "landing_frame_idx": accepted[landing_idx].frame_idx,
            "flight_duration_s": round(flight_s, 3),
            "both_feet_airborne": airborne,
            "stable_landing": stable_landing,
            "validity_notes": validity_notes,
            "attempts_detected": len(candidates),
        },
        "valid": valid,
        "confidence_score": confidence,
        "cheat_flags": cheat_flags,
        "cheat_score": cheat_score,
        "debug_info": {
            "dx_normalized": round(dx_norm, 4),
            "body_height_norm": round(body_height_norm, 4),
            "peak_frame_idx": accepted[peak_idx].frame_idx,
        },
    }


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


def _score_broad_jump_candidate(
    group: list[int],
    accepted: list[PoseFrame],
    ankle_x: list[float],
    ankle_y: list[float],
    ground_mask: list[bool],
    baseline_ground: list[int],
    fps: float,
) -> dict[str, Any] | None:
    if len(group) < 3:
        return None
    start = group[0]
    end = group[-1]
    pre_ground = [i for i in range(max(0, start - int(1.2 * fps)), start) if ground_mask[i]]
    post_ground = [i for i in range(end + 1, min(len(ground_mask), end + int(1.2 * fps))) if ground_mask[i]]
    if len(pre_ground) < 2:
        pre_ground = [i for i in baseline_ground if i < start]
    if len(pre_ground) < 2 or len(post_ground) < 2:
        return None

    takeoff_idx = pre_ground[-1]
    landing_idx = post_ground[0]
    peak_idx = min(group, key=lambda i: ankle_y[i])
    dx_norm = abs(ankle_x[landing_idx] - ankle_x[takeoff_idx])

    nose_y_list = [landmark_xy(accepted[i], "nose")[1] for i in pre_ground]
    ankle_y_baseline = float(np.median([ankle_y[i] for i in pre_ground]))
    nose_y_baseline = float(np.median(nose_y_list)) if nose_y_list else ankle_y_baseline - 0.5
    body_height_norm = abs(ankle_y_baseline - nose_y_baseline)
    if body_height_norm < 0.05:
        body_height_norm = 0.5

    jump_cm = (dx_norm / body_height_norm) * ADULT_HEIGHT_CM
    peak_ankle_y = ankle_y[peak_idx]
    ground_level = float(np.median([ankle_y[i] for i in pre_ground]))
    airborne = peak_ankle_y < (ground_level - GROUND_TOL - 0.02)

    return {
        "takeoff_idx": takeoff_idx,
        "landing_idx": landing_idx,
        "peak_idx": peak_idx,
        "dx_norm": dx_norm,
        "body_height_norm": body_height_norm,
        "jump_cm": jump_cm,
        "flight_s": len(group) / fps,
        "airborne": airborne,
    }


def _compute_confidence(mean_conf, flight_s, valid, airborne):
    flight_score = min(flight_s / 0.4, 1.0) * 0.25
    conf = mean_conf * 0.5 + flight_score + (0.15 if valid else 0.0) + (0.1 if airborne else 0.0)
    return round(min(max(conf, 0.0), 1.0), 3)


def _get_cheat_flags(jump_cm, mean_conf, airborne):
    flags = []
    if jump_cm > 300.0:
        flags.append("implausibly_long_jump")
    if mean_conf < 0.6:
        flags.append("low_pose_confidence")
    if not airborne:
        flags.append("no_clear_takeoff")
    return flags


def _get_cheat_score(jump_cm, mean_conf, airborne):
    score = 0.0
    if jump_cm > 300.0:
        score += 0.4
    if not airborne:
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
