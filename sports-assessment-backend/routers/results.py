"""
results.py – Router for querying stored test results
GET /api/sessions
GET /api/results/{session_id}
DELETE /api/sessions/{session_id}
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import TestSession, TestResult, Athlete
from schemas import SessionSummary, ResultDetail

router = APIRouter(prefix="/api", tags=["results"])


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions(limit: int = 50, db: Session = Depends(get_db)):
    """Return list of all test sessions, newest first."""
    rows = (
        db.query(TestSession)
        .order_by(TestSession.start_time.desc())
        .limit(limit)
        .all()
    )

    summaries = []
    for row in rows:
        athlete_name = row.athlete.name if row.athlete else None
        primary = row.result.primary_metric if row.result else None
        valid = row.result.valid if row.result else None
        conf = row.result.confidence_score if row.result else None

        grade = row.result.grade if row.result else None
        pts = row.result.points_awarded if row.result else 0

        summaries.append(
            SessionSummary(
                session_id=row.session_id,
                athlete_id=row.athlete_id,
                athlete_name=athlete_name,
                test_type=row.test_type,
                status=row.status,
                start_time=row.start_time,
                primary_metric=primary,
                valid=valid,
                confidence_score=conf,
                grade=grade,
                points_awarded=pts,
            )
        )
    return summaries


@router.get("/results/{session_id}", response_model=ResultDetail)
def get_result(session_id: str, db: Session = Depends(get_db)):
    """Fetch detailed result for a specific session."""
    session = db.get(TestSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    if not session.result:
        raise HTTPException(status_code=404, detail="No result recorded for this session yet.")

    r = session.result
    return ResultDetail(
        session_id=session.session_id,
        athlete_id=session.athlete_id,
        test_type=session.test_type,
        primary_metric=r.primary_metric,
        secondary_metrics=r.secondary_metrics or {},
        valid=r.valid,
        confidence_score=r.confidence_score,
        cheat_flags=r.cheat_flags or [],
        cheat_score=r.cheat_score,
        grade=r.grade,
        form_score=r.form_score,
        points_awarded=r.points_awarded,
        start_time=session.start_time,
    )


@router.delete("/sessions/{session_id}", status_code=200)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a session and its result from the database."""
    session = db.get(TestSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    if session.result:
        db.delete(session.result)
    db.delete(session)
    db.commit()
    return {"message": f"Session '{session_id}' deleted."}
