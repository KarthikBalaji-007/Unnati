"""
pose_extractor.py
-----------------
Wraps MediaPipe PoseLandmarker (Tasks API, v0.10.30+) to process an entire
video file frame-by-frame.

MediaPipe landmark indices referenced throughout analyzers:
  0=nose, 11=left_shoulder, 12=right_shoulder, 13=left_elbow, 14=right_elbow,
  15=left_wrist, 16=right_wrist, 23=left_hip, 24=right_hip,
  25=left_knee, 26=right_knee, 27=left_ankle, 28=right_ankle,
  29=left_heel, 30=right_heel, 31=left_foot_index, 32=right_foot_index

All x/y coordinates are NORMALIZED [0, 1] relative to frame width/height.
y=0 is top of frame; y=1 is bottom (y increases downward).
"""

import os
import urllib.request
import cv2
import mediapipe as mp
import numpy as np
from dataclasses import dataclass
from typing import Optional

# ─── MediaPipe Tasks API imports ─────────────────────────────────────────────
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)

# Minimum per-landmark visibility accepted; frames below this are discarded
CONFIDENCE_THRESHOLD = 0.50
# Fraction of critical landmarks that must be visible to accept a frame
MIN_VISIBLE_FRACTION = 0.70

# MediaPipe landmark name → index mapping for convenience
LM = {
    "nose": 0,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13,    "right_elbow": 14,
    "left_wrist": 15,    "right_wrist": 16,
    "left_hip": 23,      "right_hip": 24,
    "left_knee": 25,     "right_knee": 26,
    "left_ankle": 27,    "right_ankle": 28,
    "left_heel": 29,     "right_heel": 30,
    "left_foot_index": 31, "right_foot_index": 32,
}

# ─── Model download ─────────────────────────────────────────────────────────
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "pose_landmarker_lite.task")


def _ensure_model():
    """Download the PoseLandmarker model file if not already present."""
    if os.path.exists(MODEL_PATH):
        return MODEL_PATH
    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"[pose_extractor] Downloading PoseLandmarker model to {MODEL_PATH}...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"[pose_extractor] Download complete ({os.path.getsize(MODEL_PATH) / 1e6:.1f} MB)")
    return MODEL_PATH


@dataclass
class Landmark:
    x: float
    y: float
    z: float
    visibility: float


@dataclass
class PoseFrame:
    frame_idx: int
    timestamp_s: float          # seconds from video start
    landmarks: list[Landmark]   # 33 landmarks (MediaPipe full body)
    frame_confidence: float     # mean visibility of critical landmarks
    accepted: bool              # True if above confidence threshold


def _compute_frame_confidence(landmarks: list[Landmark]) -> float:
    """
    Compute overall frame confidence as the mean visibility of 12 critical
    body landmarks (excludes face/hands that may be naturally occluded).
    """
    critical_indices = [
        LM["left_shoulder"], LM["right_shoulder"],
        LM["left_hip"],      LM["right_hip"],
        LM["left_knee"],     LM["right_knee"],
        LM["left_ankle"],    LM["right_ankle"],
        LM["left_wrist"],    LM["right_wrist"],
        LM["left_heel"],     LM["right_heel"],
    ]
    visibilities = [landmarks[i].visibility for i in critical_indices]
    return float(np.mean(visibilities))


def extract_poses_from_video(
    video_path: str,
    max_frames: Optional[int] = None,
    model_complexity: int = 1,
) -> tuple[list[PoseFrame], dict]:
    """
    Process a video file with MediaPipe PoseLandmarker (Tasks API) and return
    per-frame landmarks.

    Args:
        video_path:       Absolute path to the input video file.
        max_frames:       Cap on frames processed (None = all frames).
        model_complexity: Ignored (kept for API compatibility); lite model used.

    Returns:
        (pose_frames, video_info)
        pose_frames: list of PoseFrame; some may have accepted=False.
        video_info:  dict with fps, total_frames, width, height, duration_s.
    """
    model_path = _ensure_model()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_s = total_frames / fps

    video_info = {
        "fps": fps,
        "total_frames": total_frames,
        "width": width,
        "height": height,
        "duration_s": duration_s,
    }

    # Create PoseLandmarker for VIDEO mode
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    pose_frames: list[PoseFrame] = []
    frame_idx = 0
    # Process every Nth frame for speed (interpolate the rest)
    frame_skip = max(1, int(fps / 15))  # target ~15 fps analysis

    with PoseLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if max_frames and frame_idx >= max_frames:
                break

            # Skip frames for speed
            if frame_idx % frame_skip != 0:
                frame_idx += 1
                continue

            timestamp_s = frame_idx / fps
            timestamp_ms = int(timestamp_s * 1000)

            # MediaPipe Tasks API expects RGB as mp.Image
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            # Detect pose for this frame
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            if result.pose_landmarks and len(result.pose_landmarks) > 0:
                raw_lm = result.pose_landmarks[0]  # first person
                # New API provides NormalizedLandmark objects with x, y, z
                # visibility is in pose_world_landmarks or sometimes in the
                # normalized landmarks depending on version
                landmarks = []
                for i, lm in enumerate(raw_lm):
                    vis = lm.visibility if hasattr(lm, 'visibility') and lm.visibility is not None else 0.9
                    landmarks.append(Landmark(
                        x=lm.x,
                        y=lm.y,
                        z=lm.z if hasattr(lm, 'z') else 0.0,
                        visibility=vis,
                    ))

                # Pad to 33 if needed (should already be 33)
                while len(landmarks) < 33:
                    landmarks.append(Landmark(0.0, 0.0, 0.0, 0.0))

                confidence = _compute_frame_confidence(landmarks)
                accepted = confidence >= CONFIDENCE_THRESHOLD
            else:
                # No pose detected — create zero landmarks
                landmarks = [Landmark(0.0, 0.0, 0.0, 0.0) for _ in range(33)]
                confidence = 0.0
                accepted = False

            pose_frames.append(
                PoseFrame(
                    frame_idx=frame_idx,
                    timestamp_s=timestamp_s,
                    landmarks=landmarks,
                    frame_confidence=confidence,
                    accepted=accepted,
                )
            )
            frame_idx += 1

    cap.release()
    return pose_frames, video_info


def get_accepted_frames(pose_frames: list[PoseFrame]) -> list[PoseFrame]:
    """Filter to only frames above confidence threshold."""
    return [f for f in pose_frames if f.accepted]


def landmark_xy(frame: PoseFrame, name: str) -> tuple[float, float]:
    """Get (x, y) normalized coordinate of a named landmark."""
    idx = LM[name]
    lm = frame.landmarks[idx]
    return lm.x, lm.y


def avg_landmark_xy(frame: PoseFrame, name_a: str, name_b: str) -> tuple[float, float]:
    """Average x,y of two landmarks (e.g. midpoint of left/right hip)."""
    ax, ay = landmark_xy(frame, name_a)
    bx, by = landmark_xy(frame, name_b)
    return (ax + bx) / 2, (ay + by) / 2


def compute_angle_3pts(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> float:
    """
    Compute angle (degrees) at point b, formed by vectors b→a and b→c.
    Useful for joint angle computation (e.g. knee angle: hip-knee-ankle).
    """
    ab = np.array([a[0] - b[0], a[1] - b[1]])
    cb = np.array([c[0] - b[0], c[1] - b[1]])
    cos_angle = np.dot(ab, cb) / (np.linalg.norm(ab) * np.linalg.norm(cb) + 1e-8)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def moving_average(signal: list[float], window: int = 5) -> list[float]:
    """Apply a causal moving average to smooth a 1-D signal."""
    if len(signal) < window:
        return signal
    result = []
    for i in range(len(signal)):
        start = max(0, i - window + 1)
        result.append(float(np.mean(signal[start : i + 1])))
    return result
