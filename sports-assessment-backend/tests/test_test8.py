"""
test_test8.py – Unit tests for the Shuttle Run analyzer (T8).
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ai.test8_shuttle_run as t8
from tests.conftest import _make_pose_frame


def _make_shuttle_frame(frame_idx: int, hip_x: float, fps: float = 30.0):
    ts = frame_idx / fps
    return _make_pose_frame(frame_idx, ts, overrides={
        "left_hip":   (hip_x - 0.03, 0.55),
        "right_hip":  (hip_x + 0.03, 0.55),
        "left_ankle": (hip_x - 0.02, 0.85),
        "right_ankle":(hip_x + 0.02, 0.85),
    })


def _build_shuttle_sequence(fps: float = 30.0, shuttle_frames_each: int = 30):
    """
    Simulate 4×10m shuttle: right (0.1→0.9), left (0.9→0.1), right, left.
    """
    frames = []
    idx = 0
    n = shuttle_frames_each

    # Standing start (5 frames)
    for _ in range(5):
        frames.append(_make_shuttle_frame(idx, 0.15, fps)); idx += 1

    # Shuttle 1: 0.15 → 0.85
    for i in range(n):
        x = 0.15 + (0.70 * i / (n - 1))
        frames.append(_make_shuttle_frame(idx, x, fps)); idx += 1

    # Turn 1: brief pause
    for _ in range(3):
        frames.append(_make_shuttle_frame(idx, 0.85, fps)); idx += 1

    # Shuttle 2: 0.85 → 0.15
    for i in range(n):
        x = 0.85 - (0.70 * i / (n - 1))
        frames.append(_make_shuttle_frame(idx, x, fps)); idx += 1

    # Turn 2
    for _ in range(3):
        frames.append(_make_shuttle_frame(idx, 0.15, fps)); idx += 1

    # Shuttle 3: 0.15 → 0.85
    for i in range(n):
        x = 0.15 + (0.70 * i / (n - 1))
        frames.append(_make_shuttle_frame(idx, x, fps)); idx += 1

    # Turn 3
    for _ in range(3):
        frames.append(_make_shuttle_frame(idx, 0.85, fps)); idx += 1

    # Shuttle 4: 0.85 → 0.15
    for i in range(n):
        x = 0.85 - (0.70 * i / (n - 1))
        frames.append(_make_shuttle_frame(idx, x, fps)); idx += 1

    # Finish
    for _ in range(5):
        frames.append(_make_shuttle_frame(idx, 0.15, fps)); idx += 1

    return frames


def _make_vinfo(n, fps=30.0):
    return {"fps": fps, "total_frames": n, "width": 640, "height": 480, "duration_s": n / fps}


class TestShuttleRun:
    def test_duration_is_positive(self):
        frames = _build_shuttle_sequence()
        result = t8.analyze(frames, _make_vinfo(len(frames)))
        assert result["primary_metric"] is not None
        assert result["primary_metric"] > 0

    def test_result_has_required_keys(self):
        frames = _build_shuttle_sequence()
        result = t8.analyze(frames, _make_vinfo(len(frames)))
        for key in ["primary_metric", "secondary_metrics", "valid", "confidence_score", "cheat_flags", "cheat_score"]:
            assert key in result

    def test_secondary_metrics_have_shuttle_count(self):
        frames = _build_shuttle_sequence()
        result = t8.analyze(frames, _make_vinfo(len(frames)))
        sm = result["secondary_metrics"]
        assert "reversals_detected" in sm

    def test_too_few_frames(self):
        frames = [_make_shuttle_frame(i, 0.5) for i in range(10)]
        result = t8.analyze(frames, _make_vinfo(10))
        assert result["primary_metric"] is None
        assert result["valid"] is False

    def test_confidence_cheat_score_range(self):
        frames = _build_shuttle_sequence()
        result = t8.analyze(frames, _make_vinfo(len(frames)))
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert 0.0 <= result["cheat_score"] <= 1.0
