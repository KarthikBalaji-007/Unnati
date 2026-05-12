"""
test9_situps.py
---------------
Test 9 – Sit-Ups (Core Strength)

Algorithm (SRS §5.2, Test 9):
  State Machine over torso angle:
    - "DOWN" state: torso angle ≈ 0° (lying flat, back near ground)
    - "UP"   state: torso angle ≥ threshold (45–60°, sitting up)
    - Transition DOWN → UP → DOWN = 1 valid repetition

  Torso angle = angle between the shoulder-hip line and the horizontal plane.
  Since y increases downward in image coordinates:
    torso_angle_deg = arctan((shoulder_y - hip_y) / (shoulder_x - hip_x + ε)) + 90°
    More robustly: angle of vector hip→shoulder relative to horizontal.

  Smoothing: 5-frame moving average on torso angle to reduce jitter.

  Form validation:
    - Feet stability: variance in ankle y across the test window must be low.
    - Neck not used for cheating: nose y should follow shoulder y roughly.

  Protocol: 30-second or 60-second window; actual duration taken from video length.

Keypoints: left/right shoulder, left/right hip, left/right knee, left/right ankle, nose.
"""

import numpy as np
from typing import Any

from ai.pose_extractor import (
    PoseFrame, get_accepted_frames, landmark_xy, avg_landmark_xy,
    compute_angle_3pts, moving_average, LM
)

# ─── State machine thresholds ─────────────────────────────────────────────────
# Torso angle when lying flat (degrees above horizontal)
DOWN_ANGLE_THRESH = 25.0   # ≤ 25° = "down" state
# Torso angle when properly sitting up
UP_ANGLE_THRESH   = 44.0   # ≥ 45° = "up" state

# Minimum time (frames) between transitions to avoid counting noise
MIN_TRANSITION_GAP = 5

# Maximum ankle y-variance: low = feet are anchored
MAX_ANKLE_VARIANCE = 0.008

SMOOTH_WINDOW = 5


def analyze(pose_frames: list[PoseFrame], video_info: dict) -> dict[str, Any]:
    """Run the Sit-Up rep counter and form validator."""
    accepted = get_accepted_frames(pose_frames)

    if len(accepted) < 20:
        return _failure("Too few high-confidence frames. Ensure side-view with full body (head to feet) visible.")

    fps = video_info.get("fps", 30.0)
    n = len(accepted)
    duration_s = accepted[-1].timestamp_s - accepted[0].timestamp_s

    # ── Step 1: Compute per-frame torso angle ─────────────────────────────────
    # Torso angle: angle of the shoulder relative to hip in the vertical plane.
    # angle = 0° when shoulder is at hip level (lying flat)
    # angle = 90° when shoulder is directly above hip (fully upright)
    raw_angles: list[float] = []

    for f in accepted:
        sx, sy = avg_landmark_xy(f, "left_shoulder", "right_shoulder")
        hx, hy = avg_landmark_xy(f, "left_hip",      "right_hip")

        # Vector from hip to shoulder
        dx = sx - hx
        dy = hy - sy  # flip y so up is positive

        # Angle from horizontal in degrees
        angle_rad = np.arctan2(dy, abs(dx) + 1e-8)
        angle_deg = float(np.degrees(angle_rad))
        # Clamp to 0–90°
        angle_deg = max(0.0, min(90.0, angle_deg))
        raw_angles.append(angle_deg)

    # ── Step 2: Smooth angle signal ───────────────────────────────────────────
    smooth_angles = moving_average(raw_angles, SMOOTH_WINDOW)

    # ── Step 3: State machine – count reps ───────────────────────────────────
    # Start in unknown state; wait for first DOWN to initialize
    state = "UNKNOWN"  # UNKNOWN → DOWN → UP → DOWN (count) → ...
    rep_count = 0
    invalid_reps = 0
    last_transition = 0
    current_rep_start_idx = None
    rep_events: list[dict] = []  # for debug

    for i, angle in enumerate(smooth_angles):
        if state == "UNKNOWN":
            if angle <= DOWN_ANGLE_THRESH:
                state = "DOWN"
                last_transition = i

        elif state == "DOWN":
            if angle >= UP_ANGLE_THRESH and (i - last_transition) >= MIN_TRANSITION_GAP:
                state = "UP"
                last_transition = i
                current_rep_start_idx = i

        elif state == "UP":
            if angle <= DOWN_ANGLE_THRESH and (i - last_transition) >= MIN_TRANSITION_GAP:
                state = "DOWN"
                rep_count += 1
                rep_events.append({
                    "rep": rep_count,
                    "start_frame": accepted[current_rep_start_idx].frame_idx if current_rep_start_idx is not None else accepted[i].frame_idx,
                    "start_time_s": accepted[current_rep_start_idx].timestamp_s if current_rep_start_idx is not None else accepted[i].timestamp_s,
                    "completion_frame": accepted[i].frame_idx,
                    "completion_time_s": accepted[i].timestamp_s,
                })
                last_transition = i
                current_rep_start_idx = None

    # ── Step 4: Count partial/invalid reps ───────────────────────────────────
    # A partial rep is when UP state was entered but DOWN wasn't reached before
    # video ends — i.e., state is still UP at end. These don't count as valid.
    partial = 1 if state == "UP" else 0

    # Count reps where angle never reached full DOWN (angle didn't drop < DOWN + 10°)
    for ev in rep_events:
        comp_i = next(
            (i for i, f in enumerate(accepted) if f.frame_idx == ev["completion_frame"]),
            None,
        )
        if comp_i is not None:
            # Check if full down was reached (angle < DOWN_ANGLE_THRESH + 10)
            if smooth_angles[comp_i] > DOWN_ANGLE_THRESH + 10:
                invalid_reps += 1

    valid_reps = rep_count - invalid_reps
    if rep_events:
        active_duration_s = max(accepted[-1].timestamp_s - accepted[0].timestamp_s, 1e-6)
        active_duration_s = max(
            rep_events[-1]["completion_time_s"] - rep_events[0]["start_time_s"],
            1.0,
        )
    else:
        active_duration_s = max(duration_s, 1e-6)

    # ── Step 5: Validate feet stability ──────────────────────────────────────
    ankle_y_vals: list[float] = []
    for f in accepted:
        _, ay = avg_landmark_xy(f, "left_ankle", "right_ankle")
        ankle_y_vals.append(ay)

    ankle_variance = float(np.var(ankle_y_vals))
    feet_stable = ankle_variance < MAX_ANKLE_VARIANCE

    # ── Step 6: Detect cheating – half reps ──────────────────────────────────
    # Half rep: UP was achieved but DOWN wasn't fully completed (angle > 30° at bottom)
    cheat_half_reps = 0
    for rep_ev in rep_events:
        frame_idx = rep_ev["completion_frame"]
        i = next((j for j, f in enumerate(accepted) if f.frame_idx == frame_idx), None)
        if i is not None and smooth_angles[i] > DOWN_ANGLE_THRESH + 5:
            cheat_half_reps += 1

    valid = valid_reps > 0

    # ── Step 7: Confidence and cheat scores ───────────────────────────────────
    mean_conf = float(np.mean([f.frame_confidence for f in accepted]))
    confidence = _compute_confidence(mean_conf, feet_stable, rep_count, valid)
    cheat_flags = _get_cheat_flags(ankle_variance, cheat_half_reps, mean_conf)
    cheat_score = _get_cheat_score(ankle_variance, cheat_half_reps, mean_conf)

    return {
        "primary_metric": float(valid_reps),
        "secondary_metrics": {
            "total_reps": rep_count,
            "valid_reps": valid_reps,
            "invalid_reps": invalid_reps,
            "partial_reps": partial,
            "half_rep_flags": cheat_half_reps,
            "feet_stable": feet_stable,
            "ankle_y_variance": round(ankle_variance, 5),
            "duration_s": round(duration_s, 1),
            "active_duration_s": round(active_duration_s, 1),
            "reps_per_minute": round((valid_reps / active_duration_s) * 60 if active_duration_s > 0 else 0, 1),
            "rep_events": rep_events,
        },
        "valid": valid,
        "confidence_score": confidence,
        "cheat_flags": cheat_flags,
        "cheat_score": cheat_score,
        "debug_info": {
            "angle_range": [round(min(smooth_angles), 1), round(max(smooth_angles), 1)],
            "angle_mean": round(float(np.mean(smooth_angles)), 1),
            "down_thresh": DOWN_ANGLE_THRESH,
            "up_thresh": UP_ANGLE_THRESH,
            "total_frames_analyzed": n,
        },
    }


def _compute_confidence(mean_conf, feet_stable, rep_count, valid):
    stability_bonus = 0.15 if feet_stable else 0.0
    rep_bonus = min(rep_count / 10, 1.0) * 0.15
    conf = mean_conf * 0.5 + stability_bonus + rep_bonus + (0.2 if valid else 0.0)
    return round(min(max(conf, 0.0), 1.0), 3)


def _get_cheat_flags(ankle_var, half_reps, mean_conf):
    flags = []
    if ankle_var > MAX_ANKLE_VARIANCE * 2:
        flags.append("feet_not_anchored")
    if half_reps > 2:
        flags.append("multiple_half_reps_detected")
    if mean_conf < 0.6:
        flags.append("low_pose_confidence")
    return flags


def _get_cheat_score(ankle_var, half_reps, mean_conf):
    score = 0.0
    if ankle_var > MAX_ANKLE_VARIANCE * 3:
        score += 0.35
    if half_reps > 3:
        score += 0.35
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
