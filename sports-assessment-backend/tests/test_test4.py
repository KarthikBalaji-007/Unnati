"""
test_test4.py – Unit tests for the Vertical Jump analyzer (T4).
We build synthetic pose sequences simulating realistic jump physics.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.pose_extractor import LM
import ai.test4_vertical_jump as t4
from tests.conftest import _make_pose_frame


def _build_jump_sequence(
    baseline_wrist_y: float = 0.45,
    peak_wrist_y: float = 0.20,      # lower y = higher position
    baseline_ankle_y: float = 0.85,
    peak_ankle_y: float = 0.65,      # ankles rising during flight
    fps: float = 30.0,
    baseline_frames: int = 20,
    flight_frames: int = 12,
    landing_frames: int = 18,
):
    """
    Build a synthetic jump sequence:
      - baseline_frames: person standing (ankles at ground)
      - flight_frames:   airborne (ankles and wrists rise)
      - landing_frames:  back on ground
    """
    frames = []
    idx = 0

    # Phase 1: Baseline standing
    for i in range(baseline_frames):
        f = _make_pose_frame(idx, idx / fps, overrides={
            "left_wrist":  (0.45, baseline_wrist_y),
            "right_wrist": (0.55, baseline_wrist_y),
            "left_ankle":  (0.47, baseline_ankle_y),
            "right_ankle": (0.53, baseline_ankle_y),
        })
        frames.append(f)
        idx += 1

    # Phase 2: Flight (smooth parabola using quadratic interpolation)
    for i in range(flight_frames):
        t_norm = i / max(flight_frames - 1, 1)
        # Parabolic: peak at t=0.5
        parabola = 1 - 4 * (t_norm - 0.5) ** 2  # 0 at edges, 1 at center
        wrist_y = baseline_wrist_y - (baseline_wrist_y - peak_wrist_y) * parabola
        ankle_y = baseline_ankle_y - (baseline_ankle_y - peak_ankle_y) * parabola

        f = _make_pose_frame(idx, idx / fps, overrides={
            "left_wrist":  (0.45, wrist_y),
            "right_wrist": (0.55, wrist_y),
            "left_ankle":  (0.47, ankle_y),
            "right_ankle": (0.53, ankle_y),
        })
        frames.append(f)
        idx += 1

    # Phase 3: Landing
    for i in range(landing_frames):
        f = _make_pose_frame(idx, idx / fps, overrides={
            "left_wrist":  (0.45, baseline_wrist_y),
            "right_wrist": (0.55, baseline_wrist_y),
            "left_ankle":  (0.47, baseline_ankle_y),
            "right_ankle": (0.53, baseline_ankle_y),
        })
        frames.append(f)
        idx += 1

    return frames


def _make_vinfo(fps=30.0, total=50):
    return {"fps": fps, "total_frames": total, "width": 640, "height": 480, "duration_s": total / fps}


class TestVerticalJump:
    def test_basic_jump_returns_positive_height(self):
        frames = _build_jump_sequence()
        result = t4.analyze(frames, _make_vinfo(total=len(frames)))
        assert result["primary_metric"] is not None
        assert result["primary_metric"] > 0

    def test_jump_height_in_plausible_range(self):
        # Simulate ~40 cm jump (wrist moves from 0.45 to 0.20 in normalized space)
        frames = _build_jump_sequence(baseline_wrist_y=0.45, peak_wrist_y=0.20)
        result = t4.analyze(frames, _make_vinfo(total=len(frames)))
        # Should be in a plausible range (20–80 cm for this synthetic data)
        assert result["primary_metric"] is not None
        assert 10.0 <= result["primary_metric"] <= 120.0

    def test_no_jump_returns_invalid(self):
        # All frames are standing still — no flight phase
        frames = [_make_pose_frame(i, i / 30.0) for i in range(40)]
        result = t4.analyze(frames, _make_vinfo(total=40))
        # Should fail or produce None/invalid
        assert result["valid"] is False or result["primary_metric"] is None

    def test_too_few_frames_returns_failure(self):
        frames = [_make_pose_frame(i, i / 30.0) for i in range(5)]
        result = t4.analyze(frames, _make_vinfo(total=5))
        assert result["primary_metric"] is None
        assert result["valid"] is False

    def test_confidence_score_between_0_and_1(self):
        frames = _build_jump_sequence()
        result = t4.analyze(frames, _make_vinfo(total=len(frames)))
        assert 0.0 <= result["confidence_score"] <= 1.0

    def test_cheat_score_between_0_and_1(self):
        frames = _build_jump_sequence()
        result = t4.analyze(frames, _make_vinfo(total=len(frames)))
        assert 0.0 <= result["cheat_score"] <= 1.0

    def test_result_has_required_keys(self):
        frames = _build_jump_sequence()
        result = t4.analyze(frames, _make_vinfo(total=len(frames)))
        for key in ["primary_metric", "secondary_metrics", "valid", "confidence_score", "cheat_flags", "cheat_score"]:
            assert key in result

    def test_secondary_metrics_present(self):
        frames = _build_jump_sequence()
        result = t4.analyze(frames, _make_vinfo(total=len(frames)))
        sm = result["secondary_metrics"]
        assert "flight_duration_s" in sm
        assert sm["flight_duration_s"] > 0
