"""
athletes.py – Router for athlete profiles, leaderboard, and benchmarks.
"""

from datetime import datetime
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import Athlete, TestResult, TestSession, AppUser, AuthSession
from schemas import (
    AthleteCreate, AthleteOut, AthleteProfile,
    LeaderboardEntry, BenchmarkInfo,
)
from ai.scoring import compute_rank_progress, get_badge_info, get_all_badges
from ai.sai_benchmarks import get_all_benchmarks

import uuid

router = APIRouter(prefix="/api", tags=["athletes"])


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        return None
    return parts[1]


def _get_current_user(db: Session, authorization: str | None) -> AppUser | None:
    token = _extract_bearer_token(authorization)
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash).first()
    if not session or session.expires_at <= datetime.utcnow():
        return None
    return db.get(AppUser, session.user_id)


# ─── Create athlete ──────────────────────────────────────────────────────────
@router.post("/athletes", response_model=AthleteOut)
def create_athlete(
    body: AthleteCreate,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    existing = db.query(Athlete).filter(Athlete.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Athlete '{body.name}' already exists (id={existing.athlete_id}).")

    user = _get_current_user(db, authorization)
    athlete = Athlete(
        athlete_id=str(uuid.uuid4()),
        user_id=user.user_id if user else None,
        name=body.name,
        age=body.age,
        gender=body.gender,
        location=body.location,
        organization=body.organization,
    )
    db.add(athlete)
    db.commit()
    db.refresh(athlete)
    return athlete


# ─── Get athlete profile ─────────────────────────────────────────────────────
@router.get("/athletes/{athlete_id}", response_model=AthleteProfile)
def get_athlete(athlete_id: str, db: Session = Depends(get_db)):
    athlete = db.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail=f"Athlete '{athlete_id}' not found.")

    rank_progress = compute_rank_progress(athlete.total_points)
    badge_details = []
    for bid in (athlete.badges or []):
        info = get_badge_info(bid)
        if info:
            badge_details.append(info)

    return AthleteProfile(
        athlete_id=athlete.athlete_id,
        name=athlete.name,
        age=athlete.age,
        gender=athlete.gender,
        location=athlete.location,
        organization=athlete.organization,
        total_points=athlete.total_points,
        rank_level=athlete.rank_level,
        badges=athlete.badges or [],
        days_active=athlete.days_active,
        tests_completed=athlete.tests_completed,
        created_at=athlete.created_at,
        last_active=athlete.last_active,
        rank_progress=rank_progress,
        badge_details=badge_details,
    )


# ─── List all athletes ───────────────────────────────────────────────────────
@router.get("/athletes", response_model=list[AthleteOut])
def list_athletes(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_current_user(db, authorization)
    q = db.query(Athlete)
    if user:
        linked = q.filter(Athlete.user_id == user.user_id).order_by(desc(Athlete.created_at)).all()
        if linked:
            return linked
    return q.order_by(desc(Athlete.created_at)).all()


# ─── Athlete test history ────────────────────────────────────────────────────
@router.get("/athletes/{athlete_id}/history")
def get_athlete_history(athlete_id: str, db: Session = Depends(get_db)):
    athlete = db.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail=f"Athlete '{athlete_id}' not found.")

    sessions = (
        db.query(TestSession)
        .filter(TestSession.athlete_id == athlete_id)
        .order_by(desc(TestSession.start_time))
        .all()
    )

    history = []
    for s in sessions:
        r = s.result
        history.append({
            "session_id": s.session_id,
            "test_type": s.test_type,
            "status": s.status,
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "primary_metric": r.primary_metric if r else None,
            "valid": r.valid if r else None,
            "grade": r.grade if r else None,
            "points_awarded": r.points_awarded if r else 0,
            "confidence_score": r.confidence_score if r else None,
        })
    return history


@router.get("/my-athlete", response_model=AthleteOut)
def get_my_athlete(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_current_user(db, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized.")
    athlete = (
        db.query(Athlete)
        .filter(Athlete.user_id == user.user_id)
        .order_by(desc(Athlete.created_at))
        .first()
    )
    if not athlete:
        raise HTTPException(status_code=404, detail="No athlete linked to current account.")
    return athlete


@router.post("/athletes/link/{athlete_id}", response_model=AthleteOut)
def link_my_athlete(
    athlete_id: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_current_user(db, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized.")

    athlete = db.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail=f"Athlete '{athlete_id}' not found.")

    # ensure unique mapping per user
    existing = db.query(Athlete).filter(Athlete.user_id == user.user_id).all()
    for item in existing:
        if item.athlete_id != athlete_id:
            item.user_id = None

    athlete.user_id = user.user_id
    db.commit()
    db.refresh(athlete)
    return athlete


# ─── Leaderboard ─────────────────────────────────────────────────────────────
@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def get_leaderboard(limit: int = 20, db: Session = Depends(get_db)):
    athletes = (
        db.query(Athlete)
        .order_by(desc(Athlete.total_points))
        .limit(limit)
        .all()
    )
    return [
        LeaderboardEntry(
            athlete_id=a.athlete_id,
            name=a.name,
            total_points=a.total_points,
            rank_level=a.rank_level,
            tests_completed=a.tests_completed,
            badges_count=len(a.badges or []),
        )
        for a in athletes
    ]


# ─── Benchmarks ──────────────────────────────────────────────────────────────
@router.get("/benchmarks")
def get_benchmarks():
    """Return SAI benchmark tables for all tests."""
    return get_all_benchmarks()


@router.get("/benchmarks/{test_type}", response_model=BenchmarkInfo)
def get_benchmark(test_type: str):
    benchmarks = get_all_benchmarks()
    if test_type not in benchmarks:
        raise HTTPException(status_code=404, detail=f"No benchmarks for test type '{test_type}'.")
    return benchmarks[test_type]


# ─── Badges ──────────────────────────────────────────────────────────────────
@router.get("/badges")
def list_badges():
    """Return all available badge definitions."""
    return get_all_badges()
