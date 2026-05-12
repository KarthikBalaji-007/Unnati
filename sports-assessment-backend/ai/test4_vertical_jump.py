"""
test4_vertical_jump.py
----------------------
Test 4 – Vertical Jump

Algorithm (SRS §5.2, Test 4 – inspired by Sharma et al. ICVGIP approach):
  1. Detect ground-contact phase (standing baseline) using ankle y-coordinate stability.
  2. Detect flight phase when both ankles rise significantly (y decreases in image coords).
  3. Find peak: frame with minimum wrist y (= highest upward reach) during flight.
  4. Compute jump height as difference between baseline wrist height and peak wrist height.
  5. Convert normalized height delta to cm using body-relative calibration:
       body_height_norm ≈ nose_y - ankle_y  (head-to-ankle span in normalized coords)
       body_height_cm   = adult average or user-provided estimate (~165 cm)
     jump_cm = (baseline_wrist_y - peak_wrist_y) / body_height_norm * BODY_HEIGHT_CM

Keypoints: wrist, hip, ankle (falling back to hip COM if wrist unreliable).
"""

import numpy as np
from typing import Any

from ai.pose_extractor import (
    PoseFrame, get_accepted_frames, landmark_xy, avg_landmark_xy,
    moving_average, LM
)

# ─── Constants ────────────────────────────────────────────────────────────────
# Average adult body height used for pixel-to-cm calibration.
# The normalized head-to-ankle span represents this length.
ADULT_HEIGHT_CM = 165.0

# Ankle velocity threshold (normalized units/frame) to classify flight vs ground
ANKLE_TAKEOFF_VELOCITY_THRESH = 0.005

# Minimum flight duration in frames (< 3 frames = noise, not a jump)
MIN_FLIGHT_FRAMES = 3

# Minimum jump height in cm to count as a real jump attempt
MIN_JUMP_HEIGHT_CM = 5.0

# Max plausible jump height for adults (world record ≈ 120 cm)
MAX_JUMP_HEIGHT_CM = 130.0

# Single-attempt flight bounds. Anything much longer is usually multiple jumps
# or threshold drift being merged across the whole upload.
MIN_FLIGHT_DURATION_S = 0.12
MAX_FLIGHT_DURATION_S = 1.20

# Window for moving average smoothing
SMOOTH_WINDOW = 5


def analyze(pose_frames: list[PoseFrame], video_info: dict) -> dict[str, Any]:
    """Run the Vertical Jump analyzer on extracted pose frames."""
    accepted = get_accepted_frames(pose_frames)

    if len(accepted) < 15:
        return _failure("Too few high-confidence frames. Ensure full body is visible from side with good lighting.")

    fps = video_info.get("fps", 30.0)

    # ── Step 1: Extract per-frame y-coordinates ───────────────────────────────
    # y increases downward; lower y = higher in real world
    ankle_y_raw:  list[float] = []
    wrist_y_raw:  list[float] = []
    hip_y_raw:    list[float] = []
    nose_y_raw:   list[float] = []

    for f in accepted:
        _, ay = avg_landmark_xy(f, "left_ankle", "right_ankle")
        _, wy = avg_landmark_xy(f, "left_wrist", "right_wrist")
        _, hy = avg_landmark_xy(f, "left_hip",   "right_hip")
        _, ny = landmark_xy(f, "nose")

        ankle_y_raw.append(ay)
        wrist_y_raw.append(wy)
        hip_y_raw.append(hy)
        nose_y_raw.append(ny)

    # ── Step 2: Smooth signals ────────────────────────────────────────────────
    ankle_y = moving_average(ankle_y_raw, SMOOTH_WINDOW)
    wrist_y = moving_average(wrist_y_raw, SMOOTH_WINDOW)
    hip_y   = moving_average(hip_y_raw,   SMOOTH_WINDOW)
    nose_y  = moving_average(nose_y_raw,  SMOOTH_WINDOW)

    n = len(ankle_y)

    # ── Step 3: Compute ankle vertical velocity ───────────────────────────────
    # Negative velocity = ankle moving up (y decreasing) = takeoff
    ankle_vel = [0.0] + [ankle_y[i] - ankle_y[i - 1] for i in range(1, n)]

    # ── Step 4: Detect ground-contact baseline phase ──────────────────────────
    # Ground contact: ankle_vel ≈ 0 (stable), ankle_y near its maximum (lowest physical point)
    ankle_y_max = max(ankle_y)  # maximum y = when standing on ground
    ground_threshold = ankle_y_max - 0.05  # within 5% of ground level

    ground_frames = [i for i in range(n) if ankle_y[i] >= ground_threshold and abs(ankle_vel[i]) < ANKLE_TAKEOFF_VELOCITY_THRESH]

    if len(ground_frames) < 5:
        return _failure("Could not detect stable ground-standing phase. Ensure athlete starts standing still.")

    # Baseline = first stable standing period (before the jump)
    first_half_ground = [i for i in ground_frames if i < n // 2]
    if not first_half_ground:
        first_half_ground = ground_frames[:max(5, len(ground_frames) // 3)]

    baseline_wrist_y = float(np.median([wrist_y[i] for i in first_half_ground]))
    baseline_ankle_y = float(np.median([ankle_y[i] for i in first_half_ground]))

    # ── Step 5: Detect flight phase candidates ────────────────────────────────
    # Flight: ankle rises significantly above ground level
    flight_threshold = ankle_y_max - 0.08  # ankle at least 8% above ground
    flight_frames = [i for i in range(n) if ankle_y[i] < flight_threshold]

    # Filter to flight that comes AFTER the baseline period
    if first_half_ground:
        baseline_end = max(first_half_ground)
    else:
        baseline_end = 0

    flight_frames = [i for i in flight_frames if i > baseline_end]

    flight_groups = _contiguous_groups(flight_frames, max_gap=max(2, int(0.08 * fps)))
    flight_groups = [g for g in flight_groups if len(g) >= MIN_FLIGHT_FRAMES]

    if not flight_groups:
        return _failure(
            f"No clear jump flight phase detected. "
            f"Athlete must clearly leave the ground during the test."
        )

    # ── Step 6: Score each single jump candidate ──────────────────────────────
    candidates = []
    for group in flight_groups:
        candidate = _score_jump_candidate(
            group=group,
            accepted=accepted,
            ankle_y=ankle_y,
            wrist_y=wrist_y,
            hip_y=hip_y,
            nose_y=nose_y,
            ground_frames=ground_frames,
            first_half_ground=first_half_ground,
            flight_threshold=flight_threshold,
            fps=fps,
        )
        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        return _failure("Detected motion, but no complete single jump attempt could be isolated.")

    plausible = [
        c for c in candidates
        if MIN_FLIGHT_DURATION_S <= c["flight_duration_s"] <= MAX_FLIGHT_DURATION_S
        and MIN_JUMP_HEIGHT_CM <= c["jump_height_cm"] <= MAX_JUMP_HEIGHT_CM
        and c["both_feet_up"]
    ]
    best = max(plausible or candidates, key=lambda c: c["jump_height_cm"])

    peak_idx = best["peak_idx"]
    peak_wrist_y = wrist_y[peak_idx]
    baseline_wrist_y = best["baseline_wrist_y"]
    body_height_norm = best["body_height_norm"]
    jump_height_cm = best["jump_height_cm"]
    wrist_delta_norm = baseline_wrist_y - peak_wrist_y
    flight_duration_s = best["flight_duration_s"]
    both_feet_up = best["both_feet_up"]

    # ── Step 7: Validate ──────────────────────────────────────────────────────
    valid = True
    validity_notes = []

    if jump_height_cm < MIN_JUMP_HEIGHT_CM:
        valid = False
        validity_notes.append(f"Jump height too small ({jump_height_cm:.1f} cm) — may be noise.")
    if jump_height_cm > MAX_JUMP_HEIGHT_CM:
        valid = False
        validity_notes.append(f"Jump height implausibly large ({jump_height_cm:.1f} cm) — check camera setup.")
    if flight_duration_s < MIN_FLIGHT_DURATION_S or flight_duration_s > MAX_FLIGHT_DURATION_S:
        valid = False
        validity_notes.append(f"Flight duration outside single-jump range ({flight_duration_s:.2f}s).")

    if not both_feet_up:
        valid = False
        validity_notes.append("Both feet did not clearly leave the ground.")

    # ── Step 8: Confidence & cheat detection ──────────────────────────────────
    mean_conf = float(np.mean([f.frame_confidence for f in accepted]))
    confidence = _compute_confidence(mean_conf, flight_duration_s, jump_height_cm, valid)

    cheat_flags = _get_cheat_flags(jump_height_cm, flight_duration_s, mean_conf, both_feet_up)
    cheat_score = _get_cheat_score(jump_height_cm, flight_duration_s, mean_conf, both_feet_up)

    return {
        "primary_metric": round(max(jump_height_cm, 0.0), 1),
        "secondary_metrics": {
            "flight_duration_s": round(flight_duration_s, 3),
            "baseline_wrist_y_norm": round(baseline_wrist_y, 4),
            "peak_wrist_y_norm": round(peak_wrist_y, 4),
            "body_height_norm": round(body_height_norm, 4),
            "both_feet_off_ground": both_feet_up,
            "validity_notes": validity_notes,
            "total_accepted_frames": len(accepted),
            "attempts_detected": len(candidates),
            "selected_attempt_start_frame": accepted[best["start_idx"]].frame_idx,
            "selected_attempt_end_frame": accepted[best["end_idx"]].frame_idx,
        },
        "valid": valid,
        "confidence_score": confidence,
        "cheat_flags": cheat_flags,
        "cheat_score": cheat_score,
        "debug_info": {
            "baseline_frames": len(first_half_ground),
            "flight_frames": best["flight_frames"],
            "peak_frame_idx": accepted[peak_idx].frame_idx,
            "wrist_delta_norm": round(wrist_delta_norm, 4),
            "hip_delta_norm": round(best["hip_delta_norm"], 4),
            "height_source": "hip_vertical_displacement",
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


def _score_jump_candidate(
    group: list[int],
    accepted: list[PoseFrame],
    ankle_y: list[float],
    wrist_y: list[float],
    hip_y: list[float],
    nose_y: list[float],
    ground_frames: list[int],
    first_half_ground: list[int],
    flight_threshold: float,
    fps: float,
) -> dict[str, Any] | None:
    start_idx = group[0]
    end_idx = group[-1]
    pre_ground = [i for i in ground_frames if max(0, start_idx - int(1.5 * fps)) <= i < start_idx]
    if len(pre_ground) < 3:
        pre_ground = [i for i in first_half_ground if i < start_idx] or ground_frames[:max(5, min(len(ground_frames), 10))]
    if len(pre_ground) < 3:
        return None

    baseline_wrist_y = float(np.median([wrist_y[i] for i in pre_ground]))
    baseline_hip_y = float(np.median([hip_y[i] for i in pre_ground]))
    baseline_ankle_y = float(np.median([ankle_y[i] for i in pre_ground]))
    baseline_nose_y = float(np.median([nose_y[i] for i in pre_ground]))
    body_height_norm = abs(baseline_ankle_y - baseline_nose_y)
    if body_height_norm < 0.05:
        return None

    peak_idx = min(group, key=lambda i: hip_y[i])
    hip_delta_norm = max(0.0, baseline_hip_y - hip_y[peak_idx])
    peak_ankle_idx = min(group, key=lambda i: ankle_y[i])
    ankle_delta_norm = max(0.0, baseline_ankle_y - ankle_y[peak_ankle_idx])
    height_delta_norm = hip_delta_norm if hip_delta_norm >= 0.01 else ankle_delta_norm
    jump_height_cm = (height_delta_norm / body_height_norm) * ADULT_HEIGHT_CM

    lank_x, lank_y_peak = landmark_xy(accepted[peak_idx], "left_ankle")
    rank_x, rank_y_peak = landmark_xy(accepted[peak_idx], "right_ankle")
    both_feet_up = lank_y_peak < flight_threshold and rank_y_peak < flight_threshold

    return {
        "start_idx": start_idx,
        "end_idx": end_idx,
        "peak_idx": peak_idx,
        "flight_frames": len(group),
        "flight_duration_s": len(group) / fps,
        "baseline_wrist_y": baseline_wrist_y,
        "body_height_norm": body_height_norm,
        "hip_delta_norm": hip_delta_norm,
        "ankle_delta_norm": ankle_delta_norm,
        "jump_height_cm": jump_height_cm,
        "both_feet_up": both_feet_up,
    }


def _compute_confidence(mean_conf: float, flight_s: float, jump_cm: float, valid: bool) -> float:
    # Longer flight = more confident measurement; 0.3–0.7s is typical for good jumps
    flight_score = min(flight_s / 0.5, 1.0) * 0.3
    conf = mean_conf * 0.5 + flight_score + (0.2 if valid else 0.0)
    return round(min(max(conf, 0.0), 1.0), 3)


def _get_cheat_flags(jump_cm, flight_s, mean_conf, both_feet) -> list[str]:
    flags = []
    if jump_cm > 100.0:
        flags.append("implausibly_high_jump")
    if flight_s < 0.1:
        flags.append("very_short_flight")
    if mean_conf < 0.6:
        flags.append("low_pose_confidence")
    if not both_feet:
        flags.append("single_foot_takeoff")
    return flags


def _get_cheat_score(jump_cm, flight_s, mean_conf, both_feet) -> float:
    score = 0.0
    if jump_cm > 100.0:
        score += 0.4
    if flight_s < 0.05:
        score += 0.3
    if not both_feet:
        score += 0.2
    if mean_conf < 0.5:
        score += 0.1
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
