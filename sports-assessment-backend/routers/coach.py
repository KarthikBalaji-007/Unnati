"""
coach.py – Read-only coach dashboard endpoints.
"""

from datetime import datetime
import hashlib

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import AppUser, AuthSession, Athlete, TestSession, TestResult
from schemas import CoachOverview, SessionSummary

router = APIRouter(prefix="/api/coach", tags=["coach"])


def _require_auth(db: Session, authorization: str | None) -> AppUser:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing.")
    parts = authorization.strip().split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format.")
    token_hash = hashlib.sha256(parts[1].encode("utf-8")).hexdigest()
    session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash).first()
    if not session or session.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    user = db.get(AppUser, session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


@router.get("/overview", response_model=CoachOverview)
def coach_overview(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _require_auth(db, authorization)
    total_athletes = db.query(func.count(Athlete.athlete_id)).scalar() or 0
    total_sessions = db.query(func.count(TestSession.session_id)).scalar() or 0
    completed_sessions = db.query(func.count(TestSession.session_id)).filter(TestSession.status == "completed").scalar() or 0
    invalid_sessions = db.query(func.count(TestSession.session_id)).filter(TestSession.status == "invalid").scalar() or 0
    avg_conf = db.query(func.avg(TestResult.confidence_score)).scalar() or 0.0

    valid_rate = (completed_sessions / total_sessions * 100.0) if total_sessions else 0.0
    return CoachOverview(
        total_athletes=total_athletes,
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        invalid_sessions=invalid_sessions,
        valid_rate_pct=round(valid_rate, 2),
        avg_confidence_pct=round(float(avg_conf) * 100.0, 2),
    )


@router.get("/recent-sessions", response_model=list[SessionSummary])
def coach_recent_sessions(
    limit: int = 20,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _require_auth(db, authorization)
    rows = (
        db.query(TestSession)
        .order_by(TestSession.start_time.desc())
        .limit(limit)
        .all()
    )
    out: list[SessionSummary] = []
    for row in rows:
        athlete_name = row.athlete.name if row.athlete else None
        result = row.result
        out.append(
            SessionSummary(
                session_id=row.session_id,
                athlete_id=row.athlete_id,
                athlete_name=athlete_name,
                test_type=row.test_type,
                status=row.status,
                start_time=row.start_time,
                primary_metric=result.primary_metric if result else None,
                valid=result.valid if result else None,
                confidence_score=result.confidence_score if result else None,
                grade=result.grade if result else None,
                points_awarded=result.points_awarded if result else 0,
            )
        )
    return out
