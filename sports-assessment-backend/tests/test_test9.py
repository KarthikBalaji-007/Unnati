"""
test_test9.py – Unit tests for the Sit-Ups rep counter (T9).
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ai.test9_situps as t9
from tests.conftest import _make_pose_frame


def _make_situp_frame(frame_idx: int, torso_angle_deg: float, fps: float = 30.0) -> object:
    """
    Create a synthetic sit-up frame at a given torso angle.
    torso_angle_deg: 0° = lying flat, 60°+ = sitting up.
    We manipulate shoulder y to simulate torso angle.
    """
    ts = frame_idx / fps
    # Hip stays fixed, shoulder y changes to simulate angle
    hip_y = 0.60
    hip_x = 0.50
    # Angle from horizontal; shoulder is above hip
    import math
    angle_rad = math.radians(torso_angle_deg)
    dx = 0.10 * math.cos(angle_rad)
    dy = 0.10 * math.sin(angle_rad)

    shoulder_x = hip_x + 0.02
    shoulder_y = hip_y - dy  # shoulder above hip (lower y = higher position)

    return _make_pose_frame(frame_idx, ts, overrides={
        "left_shoulder":  (shoulder_x - 0.04, shoulder_y),
        "right_shoulder": (shoulder_x + 0.04, shoulder_y),
        "left_hip":       (hip_x - 0.03, hip_y),
        "right_hip":      (hip_x + 0.03, hip_y),
        # Stable ankles
        "left_ankle":     (0.47, 0.85),
        "right_ankle":    (0.53, 0.85),
    })


def _build_situp_sequence(reps: int = 5, fps: float = 30.0):
    """
    Build synthetic sit-up frames. Each rep = down(10f) + up(10f) cycle.
    Starting in DOWN (0°), going to UP (60°), back to DOWN.
    """
    frames = []
    idx = 0

    # Start flat for 10 frames
    for _ in range(10):
        frames.append(_make_situp_frame(idx, 0.0, fps)); idx += 1

    for _ in range(reps):
        # Rising: 0° → 60° over 10 frames
        for step in range(10):
            angle = (step / 9) * 60.0
            frames.append(_make_situp_frame(idx, angle, fps)); idx += 1
        # Falling: 60° → 0° over 10 frames
        for step in range(10):
            angle = 60.0 - (step / 9) * 60.0
            frames.append(_make_situp_frame(idx, angle, fps)); idx += 1

    # End flat
    for _ in range(10):
        frames.append(_make_situp_frame(idx, 0.0, fps)); idx += 1

    return frames


def _make_vinfo(n, fps=30.0):
    return {"fps": fps, "total_frames": n, "width": 640, "height": 480, "duration_s": n / fps}


class TestSitUps:
    def test_counts_correct_reps(self):
        frames = _build_situp_sequence(reps=5)
        result = t9.analyze(frames, _make_vinfo(len(frames)))
        assert result["primary_metric"] is not None
        # Allow ±1 tolerance
        assert abs(result["secondary_metrics"]["total_reps"] - 5) <= 1

    def test_zero_reps_static_lying(self):
        # All frames at 0° (lying flat — no movement)
        frames = [_make_situp_frame(i, 0.0) for i in range(30)]
        result = t9.analyze(frames, _make_vinfo(30))
        assert result["secondary_metrics"]["total_reps"] == 0 or result["valid"] is False

    def test_too_few_frames(self):
        frames = [_make_situp_frame(i, 0.0) for i in range(5)]
        result = t9.analyze(frames, _make_vinfo(5))
        assert result["primary_metric"] is None
        assert result["valid"] is False

    def test_result_has_required_keys(self):
        frames = _build_situp_sequence(reps=3)
        result = t9.analyze(frames, _make_vinfo(len(frames)))
        for key in ["primary_metric", "secondary_metrics", "valid", "confidence_score", "cheat_flags", "cheat_score"]:
            assert key in result

    def test_secondary_metrics_structure(self):
        frames = _build_situp_sequence(reps=3)
        result = t9.analyze(frames, _make_vinfo(len(frames)))
        sm = result["secondary_metrics"]
        assert "valid_reps" in sm
        assert "invalid_reps" in sm
        assert "feet_stable" in sm
        assert "duration_s" in sm

    def test_confidence_and_cheat_scores_valid_range(self):
        frames = _build_situp_sequence(reps=4)
        result = t9.analyze(frames, _make_vinfo(len(frames)))
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert 0.0 <= result["cheat_score"] <= 1.0

    def test_10_reps(self):
        frames = _build_situp_sequence(reps=10)
        result = t9.analyze(frames, _make_vinfo(len(frames)))
        assert result["primary_metric"] is not None
        assert abs(result["secondary_metrics"]["total_reps"] - 10) <= 1
