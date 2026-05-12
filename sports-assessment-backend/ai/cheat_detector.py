"""
cheat_detector.py
-----------------
Cross-cutting cheat and anomaly detection for all test types.

Checks performed:
  1. Video too short: likely cut/edited to remove invalid sections.
  2. Suspiciously uniform pose: keypoints barely moving = static image or edited video.
  3. Keypoint teleportation: sudden large jumps between frames = edit cut.
  4. Implausibly high confidence combined with extreme metric = suspicious.
  5. Multiple distinct pose sequences (resets) = attempted multiple videos spliced together.

Returns anomaly_flags (list of strings) and cheat_score (0–1).
"""

import numpy as np
from typing import Any

from ai.pose_extractor import PoseFrame, get_accepted_frames, avg_landmark_xy, LM

# ─── Thresholds ───────────────────────────────────────────────────────────────
MIN_VIDEO_DURATION_S = 2.0          # anything under 2s is suspicious
TELEPORT_THRESH = 0.15              # normalized jump between frames = teleportation
MAX_VARIANCE_THRESH = 1e-5          # signal variance below this = static image
POSE_RESET_THRESH = 0.20            # large sudden jump in hip position = edit


def run_global_checks(
    pose_frames: list[PoseFrame],
    video_info: dict,
    test_result: dict[str, Any],
    test_type: str,
) -> tuple[list[str], float]:
    """
    Run global cheat/anomaly checks on pose sequence and test result.

    Args:
        pose_frames: All pose frames from video (including rejected ones).
        video_info:  Video metadata dict.
        test_result: Already-computed test result dict (from test-specific analyzer).
        test_type:   'T3' | 'T4' | 'T5' | 'T8' | 'T9'

    Returns:
        (cheat_flags, cheat_score) — merged with test-specific flags from result.
    """
    flags: list[str] = list(test_result.get("cheat_flags", []))
    score: float = test_result.get("cheat_score", 0.0)

    accepted = get_accepted_frames(pose_frames)
    duration_s = video_info.get("duration_s", 0.0)

    # ── Check 1: Video too short ──────────────────────────────────────────────
    if duration_s < MIN_VIDEO_DURATION_S:
        if "video_too_short" not in flags:
            flags.append("video_too_short")
            score = min(score + 0.4, 1.0)

    # ── Check 2: Suspiciously low pose motion (static image) ──────────────────
    if len(accepted) >= 10:
        hip_x_vals = [avg_landmark_xy(f, "left_hip", "right_hip")[0] for f in accepted]
        hip_x_var = float(np.var(hip_x_vals))
        if hip_x_var < MAX_VARIANCE_THRESH:
            if "static_image_suspected" not in flags:
                flags.append("static_image_suspected")
                score = min(score + 0.5, 1.0)

    # ── Check 3: Keypoint teleportation ──────────────────────────────────────
    teleported = False
    if len(accepted) >= 2:
        for i in range(1, len(accepted)):
            prev_hx, _ = avg_landmark_xy(accepted[i - 1], "left_hip", "right_hip")
            curr_hx, _ = avg_landmark_xy(accepted[i],     "left_hip", "right_hip")
            if abs(curr_hx - prev_hx) > TELEPORT_THRESH:
                teleported = True
                break

    if teleported:
        if "keypoint_teleportation" not in flags:
            flags.append("keypoint_teleportation")
            score = min(score + 0.3, 1.0)

    # ── Check 4: Pose resets (potential video splice) ─────────────────────────
    resets = 0
    if len(accepted) >= 10:
        hip_positions = [avg_landmark_xy(f, "left_hip", "right_hip")[0] for f in accepted]
        for i in range(1, len(hip_positions)):
            if abs(hip_positions[i] - hip_positions[i - 1]) > POSE_RESET_THRESH:
                resets += 1

    if resets >= 2:
        if "multiple_pose_resets" not in flags:
            flags.append("multiple_pose_resets")
            score = min(score + 0.3, 1.0)

    # ── Check 5: Implausible metrics ─────────────────────────────────────────
    primary = test_result.get("primary_metric")
    if primary is not None:
        implausible = _check_implausible_metric(test_type, primary)
        if implausible and "implausible_metric" not in flags:
            flags.append("implausible_metric")
            score = min(score + 0.3, 1.0)

    return flags, round(min(score, 1.0), 3)


def _check_implausible_metric(test_type: str, value: float) -> bool:
    """Return True if the metric value is outside any physiological plausibility range."""
    bounds = {
        "T3": (-10.0, 60.0),   # Sit & Reach: -10 to 60 cm
        "T4": (0.0,  120.0),   # Vertical Jump: 0 to 120 cm
        "T5": (0.0,  350.0),   # Broad Jump: 0 to 350 cm
        "T8": (7.0,  30.0),    # Shuttle Run: 7 to 30 seconds
        "T9": (0.0,  100.0),   # Sit-Ups: 0 to 100 reps in window
    }
    lo, hi = bounds.get(test_type, (-1e9, 1e9))
    return not (lo <= value <= hi)
