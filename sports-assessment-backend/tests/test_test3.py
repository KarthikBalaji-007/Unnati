"""
test_test3.py – Unit tests for Sit & Reach analyzer (T3).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ai.test3_sit_reach as t3
from tests.conftest import _make_pose_frame


def _make_seated_reach_frame(frame_idx, wrist_x=0.60, ankle_x=0.50, hip_y=0.55, fps=30.0):
    """Simulate a seated athlete reaching forward. Legs extended (hip-knee-ankle nearly flat)."""
    ts = frame_idx / fps
    return _make_pose_frame(frame_idx, ts, overrides={
        "left_wrist":   (wrist_x - 0.02, 0.50),
        "right_wrist":  (wrist_x + 0.02, 0.50),
        "left_hip":     (0.47, hip_y),
        "right_hip":    (0.53, hip_y),
        "left_knee":    (0.55, hip_y + 0.02),   # nearly horizontal with hip (legs extended)
        "right_knee":   (0.60, hip_y + 0.02),
        "left_ankle":   (ankle_x - 0.02, hip_y + 0.03),
        "right_ankle":  (ankle_x + 0.02, hip_y + 0.03),
        "left_shoulder": (0.40, hip_y - 0.15),
        "right_shoulder":(0.46, hip_y - 0.15),
    })


def _make_vinfo(n, fps=30.0):
    return {"fps": fps, "total_frames": n, "width": 640, "height": 480, "duration_s": n / fps}


class TestSitReach:
    def test_result_has_required_keys(self):
        frames = [_make_seated_reach_frame(i) for i in range(40)]
        result = t3.analyze(frames, _make_vinfo(40))
        for key in ["primary_metric", "secondary_metrics", "valid", "confidence_score", "cheat_flags", "cheat_score"]:
            assert key in result

    def test_confidence_cheat_range(self):
        frames = [_make_seated_reach_frame(i) for i in range(40)]
        result = t3.analyze(frames, _make_vinfo(40))
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert 0.0 <= result["cheat_score"] <= 1.0

    def test_too_few_frames(self):
        frames = [_make_seated_reach_frame(i) for i in range(5)]
        result = t3.analyze(frames, _make_vinfo(5))
        assert result["primary_metric"] is None
        assert result["valid"] is False

    def test_larger_reach_gives_larger_metric(self):
        """Frames with wrist further forward should produce a higher reach_cm."""
        frames_close = [_make_seated_reach_frame(i, wrist_x=0.52, ankle_x=0.50) for i in range(40)]
        frames_far   = [_make_seated_reach_frame(i, wrist_x=0.68, ankle_x=0.50) for i in range(40)]
        vinfo = _make_vinfo(40)
        r_close = t3.analyze(frames_close, vinfo)
        r_far   = t3.analyze(frames_far,   vinfo)
        # If both produced metrics, far should be >= close
        if r_close["primary_metric"] is not None and r_far["primary_metric"] is not None:
            assert r_far["primary_metric"] >= r_close["primary_metric"]
