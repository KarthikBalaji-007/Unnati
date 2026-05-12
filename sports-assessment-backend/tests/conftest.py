"""
conftest.py – Shared pytest fixtures for synthetic pose data.
"""

import pytest
from ai.pose_extractor import PoseFrame, Landmark, LM


def _make_landmark(x=0.5, y=0.5, z=0.0, visibility=0.95):
    return Landmark(x=x, y=y, z=z, visibility=visibility)


def _make_pose_frame(frame_idx: int, timestamp_s: float, overrides: dict = None) -> PoseFrame:
    """
    Build a full 33-landmark PoseFrame with sensible defaults (person standing center-frame).
    overrides: dict of {landmark_name_or_index: (x, y)} to customize specific keypoints.
    """
    # Default: full body in normalized coords (person standing, full height ~0.1–0.9 y-range)
    defaults = {
        "nose":               (0.50, 0.10),
        "left_shoulder":      (0.46, 0.25), "right_shoulder": (0.54, 0.25),
        "left_elbow":         (0.44, 0.35), "right_elbow":    (0.56, 0.35),
        "left_wrist":         (0.45, 0.45), "right_wrist":    (0.55, 0.45),
        "left_hip":           (0.47, 0.55), "right_hip":      (0.53, 0.55),
        "left_knee":          (0.47, 0.70), "right_knee":     (0.53, 0.70),
        "left_ankle":         (0.47, 0.85), "right_ankle":    (0.53, 0.85),
        "left_heel":          (0.46, 0.87), "right_heel":     (0.54, 0.87),
        "left_foot_index":    (0.45, 0.88), "right_foot_index":(0.55, 0.88),
    }

    if overrides:
        defaults.update(overrides)

    landmarks = [_make_landmark() for _ in range(33)]  # fill all 33 first

    for name, (x, y) in defaults.items():
        idx = LM[name]
        landmarks[idx] = _make_landmark(x=x, y=y)

    return PoseFrame(
        frame_idx=frame_idx,
        timestamp_s=timestamp_s,
        landmarks=landmarks,
        frame_confidence=0.92,
        accepted=True,
    )


@pytest.fixture
def standing_frames():
    """30 frames of a person standing still (baseline for jump tests)."""
    return [_make_pose_frame(i, i / 30.0) for i in range(30)]


@pytest.fixture
def video_info_30fps():
    return {"fps": 30.0, "total_frames": 150, "width": 640, "height": 480, "duration_s": 5.0}
