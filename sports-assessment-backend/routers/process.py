"""
process.py – Router for AI video processing
POST /api/process
"""

import os
import glob
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Athlete, TestSession, TestResult
from schemas import ProcessRequest, ProcessResponse, MetricResult, AthleteCreate

# AI modules
from ai.pose_extractor import extract_poses_from_video
from ai.cheat_detector import run_global_checks
from ai.sai_benchmarks import compute_grade, get_benchmark_threshold
from ai.scoring import calculate_points, compute_rank, check_badges
import ai.test3_sit_reach   as test3
import ai.test4_vertical_jump as test4
import ai.test5_broad_jump  as test5
import ai.test8_shuttle_run as test8
import ai.test9_situps      as test9

router = APIRouter(prefix="/api", tags=["process"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")

# Map test type string → analyzer module
ANALYZERS = {
    "T3": test3,
    "T4": test4,
    "T5": test5,
    "T8": test8,
    "T9": test9,
}


def _find_uploaded_file(file_id: str) -> str:
    """Locate the uploaded file on disk by file_id (any extension)."""
    pattern = os.path.join(UPLOAD_DIR, f"{file_id}.*")
    matches = glob.glob(pattern)
    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"No uploaded file found with file_id='{file_id}'. Upload the video first via /api/upload.",
        )
    return matches[0]


def _get_or_create_athlete(
    db: Session,
    athlete_id: str | None,
    athlete_info: AthleteCreate | None,
) -> Athlete:
    """Return existing Athlete or create a new one from inline athlete_info."""
    if athlete_id:
        athlete = db.get(Athlete, athlete_id)
        if not athlete:
            raise HTTPException(status_code=404, detail=f"Athlete '{athlete_id}' not found.")
        return athlete

    if athlete_info:
        athlete = Athlete(
            athlete_id=str(uuid.uuid4()),
            name=athlete_info.name,
            age=athlete_info.age,
            gender=athlete_info.gender,
            location=athlete_info.location,
            organization=getattr(athlete_info, 'organization', None),
        )
        db.add(athlete)
        db.flush()
        return athlete

    # Default anonymous athlete for quick testing
    athlete = Athlete(
        athlete_id=str(uuid.uuid4()),
        name="Anonymous",
        age=18,
        gender="other",
    )
    db.add(athlete)
    db.flush()
    return athlete


def _update_athlete_stats(db: Session, athlete: Athlete, grade: str, points: int, confidence: float):
    """Update athlete cumulative points, rank, badges, and stats."""
    athlete.total_points += points
    athlete.tests_completed += 1
    athlete.rank_level = compute_rank(athlete.total_points)
    athlete.last_active = datetime.utcnow()

    # Gather stats for badge checks
    unique_tests = db.query(TestSession.test_type).filter(
        TestSession.athlete_id == athlete.athlete_id
    ).distinct().count()

    stats = {
        "tests_completed": athlete.tests_completed,
        "total_points": athlete.total_points,
        "max_confidence": confidence,
        "has_grade_a": grade == "A",
        "unique_tests": unique_tests,
    }

    existing_badges = athlete.badges or []
    new_badges = check_badges(stats, existing_badges)
    if new_badges:
        athlete.badges = existing_badges + new_badges

    db.flush()


@router.post("/process", response_model=ProcessResponse)
def process_video(body: ProcessRequest, db: Session = Depends(get_db)):
    """
    Trigger AI analysis on a previously uploaded video.

    Flow:
      1. Locate uploaded file on disk.
      2. Run MediaPipe pose extraction.
      3. Route to the correct test analyzer module.
      4. Run global cheat detection.
      5. Compute SAI grade + points.
      6. Persist results to SQLite + update athlete stats.
      7. Return structured metrics with grade.
    """
    if body.test_type not in ANALYZERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported test_type '{body.test_type}'. Must be one of: {list(ANALYZERS.keys())}.",
        )

    # Step 1: Find file
    video_path = _find_uploaded_file(body.file_id)

    # Step 2: Extract poses
    try:
        pose_frames, video_info = extract_poses_from_video(video_path, model_complexity=1)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Pose extraction failed: {exc}")

    accepted_count = sum(1 for f in pose_frames if f.accepted)
    if accepted_count == 0:
        raise HTTPException(
            status_code=422,
            detail="No valid pose detected in the video. Check lighting, camera angle, and ensure the full body is visible.",
        )

    # Step 3: Run test-specific analyzer
    analyzer = ANALYZERS[body.test_type]
    try:
        raw_result = analyzer.analyze(pose_frames, video_info)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis error in {body.test_type}: {exc}")

    # Step 4: Global cheat detection (merges with test-specific flags)
    global_flags, global_cheat_score = run_global_checks(
        pose_frames, video_info, raw_result, body.test_type
    )
    raw_result["cheat_flags"] = global_flags
    raw_result["cheat_score"] = global_cheat_score

    # Step 5: Compute grade + points
    athlete = _get_or_create_athlete(db, body.athlete_id, body.athlete_info)
    gender = athlete.gender

    grade = compute_grade(body.test_type, raw_result.get("primary_metric"), gender)
    points = calculate_points(grade) if raw_result.get("valid", False) else 0
    form_score = raw_result.get("confidence_score", 0.0) * 100  # convert to percentage
    benchmark_threshold = get_benchmark_threshold(body.test_type, "A", gender)

    # Step 6: Persist to DB
    session = TestSession(
        session_id=str(uuid.uuid4()),
        athlete_id=athlete.athlete_id,
        test_type=body.test_type,
        file_path=video_path,
        status="completed" if raw_result["valid"] else "invalid",
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
    )
    db.add(session)
    db.flush()

    result_row = TestResult(
        result_id=str(uuid.uuid4()),
        session_id=session.session_id,
        primary_metric=raw_result.get("primary_metric"),
        secondary_metrics=raw_result.get("secondary_metrics"),
        valid=raw_result.get("valid", False),
        confidence_score=raw_result.get("confidence_score"),
        cheat_flags=raw_result.get("cheat_flags"),
        cheat_score=raw_result.get("cheat_score"),
        grade=grade,
        form_score=form_score,
        points_awarded=points,
    )
    db.add(result_row)

    # Update athlete stats
    if raw_result.get("valid", False):
        _update_athlete_stats(db, athlete, grade, points, raw_result.get("confidence_score", 0.0))

    db.commit()

    # Step 7: Return with grade info
    metric = MetricResult(
        primary_metric=raw_result.get("primary_metric"),
        secondary_metrics=raw_result.get("secondary_metrics", {}),
        valid=raw_result.get("valid", False),
        confidence_score=raw_result.get("confidence_score", 0.0),
        cheat_flags=raw_result.get("cheat_flags", []),
        cheat_score=raw_result.get("cheat_score", 0.0),
        debug_info=raw_result.get("debug_info", {}),
        grade=grade,
        form_score=form_score,
        points_awarded=points,
        benchmark_threshold=benchmark_threshold,
    )

    return ProcessResponse(
        session_id=session.session_id,
        test_type=body.test_type,
        athlete_id=athlete.athlete_id,
        result=metric,
        message=f"Analysis complete. Grade: {grade} ({points} pts)." if raw_result["valid"]
                else "Analysis complete — attempt marked invalid.",
    )
