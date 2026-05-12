"""
test8_shuttle_run.py
--------------------
Test 8 – 4×10m Shuttle Run (Agility & Speed)

Algorithm (SRS §5.2, Test 8):
  1. Track the hip x-coordinate over time (lateral position across the lane).
  2. Smooth the signal with a moving average.
  3. Detect START: first large positive x-velocity spike after athlete leaves start region.
  4. Count direction reversals: sign changes in x-velocity clustered into shuttle legs.
     Expect exactly 3 reversals for 4 shuttles (Start→End, End→Start, Start→End, End=Finish).
  5. Detect END: after 4th shuttle, hip returns past endpoint and stops.
  6. Compute total time: (end_frame − start_frame) / fps

Camera setup assumption: camera faces the lane from the side, showing full 10m width.
The hip x-coordinate spans [0, 1] normalized across the frame width.
"""

import numpy as np
from typing import Any

from ai.pose_extractor import (
    PoseFrame, get_accepted_frames, landmark_xy, avg_landmark_xy, moving_average
)

# ─── Constants ────────────────────────────────────────────────────────────────
# Expected number of direction reversals for 4 shuttles
EXPECTED_REVERSALS = 3

# Velocity threshold for classifying motion start (hip moving)
MOTION_START_THRESH = 0.003

# Velocity sign change threshold: must be above this magnitude to count as reversal
REVERSAL_SPEED_THRESH = 0.002

# Minimum duration between reversals (seconds) to avoid noise
MIN_REVERSAL_GAP_S = 0.8

# Shuttle run time bounds (seconds) for MVP age range
MIN_SHUTTLE_TIME_S = 8.0    # elite athlete lower bound
MAX_SHUTTLE_TIME_S = 25.0   # upper bound for a valid attempt

SMOOTH_WINDOW = 7


def analyze(pose_frames: list[PoseFrame], video_info: dict) -> dict[str, Any]:
    """Run the 4×10m Shuttle Run analyzer."""
    accepted = get_accepted_frames(pose_frames)

    if len(accepted) < 30:
        return _failure("Too few frames. Ensure video covers the full shuttle run with both lane endpoints visible.")

    fps = video_info.get("fps", 30.0)
    n = len(accepted)

    # ── Step 1: Extract hip x-coordinate (lateral position) ──────────────────
    hip_x_raw: list[float] = []
    for f in accepted:
        hx, _ = avg_landmark_xy(f, "left_hip", "right_hip")
        hip_x_raw.append(hx)

    hip_x = moving_average(hip_x_raw, SMOOTH_WINDOW)

    # ── Step 2: Compute x-velocity ────────────────────────────────────────────
    hip_vel = [0.0] + [hip_x[i] - hip_x[i - 1] for i in range(1, n)]

    # ── Step 3: Detect motion start ───────────────────────────────────────────
    start_frame_idx = None
    for i in range(n):
        if abs(hip_vel[i]) >= MOTION_START_THRESH:
            # Verify sustained motion for next 3 frames
            if i + 3 < n and any(abs(hip_vel[j]) >= MOTION_START_THRESH for j in range(i, i + 3)):
                start_frame_idx = i
                break

    if start_frame_idx is None:
        return _failure("Could not detect athlete starting motion. Ensure the full run is captured.")

    # ── Step 4: Detect direction reversals ────────────────────────────────────
    # Sign of velocity indicates direction (+x = right, -x = left)
    # A reversal is when the sign flips significantly
    min_gap_frames = int(MIN_REVERSAL_GAP_S * fps)
    reversals: list[int] = []
    prev_sign = np.sign(hip_vel[start_frame_idx]) if hip_vel[start_frame_idx] != 0 else 1.0
    last_reversal = start_frame_idx

    for i in range(start_frame_idx + 1, n):
        curr_vel = hip_vel[i]
        if abs(curr_vel) < REVERSAL_SPEED_THRESH:
            continue  # ignore near-zero velocity (standing still at endpoints)
        curr_sign = np.sign(curr_vel)
        if curr_sign != prev_sign and (i - last_reversal) >= min_gap_frames:
            reversals.append(i)
            last_reversal = i
            prev_sign = curr_sign

    # ── Step 5: Detect end frame ──────────────────────────────────────────────
    # After the expected number of reversals, athlete completes the 4th shuttle
    shuttle_count = len(reversals) + 1  # each reversal adds a shuttle leg

    if len(reversals) >= EXPECTED_REVERSALS:
        # End: last detected reversal + one more shuttle leg
        final_reversal = reversals[EXPECTED_REVERSALS - 1]
        # Find when hip stops (velocity ≈ 0) after the final reversal
        end_frame_idx = n - 1
        for i in range(final_reversal, n):
            if abs(hip_vel[i]) < MOTION_START_THRESH * 0.5:
                # Check if stationery for 5+ frames
                if i + 5 < n and all(abs(hip_vel[j]) < MOTION_START_THRESH for j in range(i, i + 5)):
                    end_frame_idx = i
                    break
    else:
        # Best-effort: use last frame
        end_frame_idx = n - 1

    # ── Step 6: Compute total time ────────────────────────────────────────────
    start_ts = accepted[start_frame_idx].timestamp_s
    end_ts   = accepted[end_frame_idx].timestamp_s
    duration_s = end_ts - start_ts

    # ── Step 7: Validate ──────────────────────────────────────────────────────
    valid = True
    validity_notes = []

    if len(reversals) < EXPECTED_REVERSALS:
        valid = False
        validity_notes.append(
            f"Only {len(reversals)} direction reversals detected; expected {EXPECTED_REVERSALS}. "
            f"Ensure all 4 shuttles are in frame."
        )

    if duration_s < MIN_SHUTTLE_TIME_S:
        valid = False
        validity_notes.append(f"Duration too short ({duration_s:.2f}s). Possible detection error or skipped shuttles.")

    if duration_s > MAX_SHUTTLE_TIME_S:
        valid = False
        validity_notes.append(f"Duration too long ({duration_s:.2f}s). Check if camera stopped or athlete paused.")

    # ── Step 8: Confidence & cheat scores ─────────────────────────────────────
    mean_conf = float(np.mean([f.frame_confidence for f in accepted]))
    confidence = _compute_confidence(mean_conf, len(reversals), valid)
    cheat_flags = _get_cheat_flags(duration_s, mean_conf, len(reversals))
    cheat_score = _get_cheat_score(duration_s, mean_conf, len(reversals))

    return {
        "primary_metric": round(duration_s, 2),
        "secondary_metrics": {
            "shuttle_count": shuttle_count,
            "reversals_detected": len(reversals),
            "reversal_frames": [accepted[r].frame_idx for r in reversals],
            "start_frame": accepted[start_frame_idx].frame_idx,
            "end_frame": accepted[end_frame_idx].frame_idx,
            "validity_notes": validity_notes,
        },
        "valid": valid,
        "confidence_score": confidence,
        "cheat_flags": cheat_flags,
        "cheat_score": cheat_score,
        "debug_info": {
            "hip_x_range": [round(min(hip_x), 3), round(max(hip_x), 3)],
            "max_velocity": round(max(abs(v) for v in hip_vel), 4),
            "total_accepted_frames": n,
        },
    }


def _compute_confidence(mean_conf, reversals, valid):
    reversal_score = min(reversals / EXPECTED_REVERSALS, 1.0) * 0.35
    conf = mean_conf * 0.45 + reversal_score + (0.2 if valid else 0.0)
    return round(min(max(conf, 0.0), 1.0), 3)


def _get_cheat_flags(duration_s, mean_conf, reversals):
    flags = []
    if duration_s < MIN_SHUTTLE_TIME_S:
        flags.append("duration_too_short")
    if reversals < EXPECTED_REVERSALS:
        flags.append("incomplete_shuttles")
    if mean_conf < 0.6:
        flags.append("low_pose_confidence")
    return flags


def _get_cheat_score(duration_s, mean_conf, reversals):
    score = 0.0
    if duration_s < MIN_SHUTTLE_TIME_S:
        score += 0.4
    if reversals < EXPECTED_REVERSALS - 1:
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
