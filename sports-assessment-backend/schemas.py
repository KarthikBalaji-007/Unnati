"""
schemas.py
----------
Pydantic schemas for request/response validation.
Keeps API contracts clean and separate from ORM models.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


# ─── Athlete ──────────────────────────────────────────────────────────────────

class AthleteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=5, le=80)
    gender: str = Field(..., pattern="^(male|female|other)$")
    location: str | None = None
    organization: str | None = None


class AthleteOut(BaseModel):
    athlete_id: str
    name: str
    age: int
    gender: str
    location: str | None
    organization: str | None
    total_points: int
    rank_level: str
    badges: list[str] | None
    days_active: int
    tests_completed: int
    created_at: datetime
    last_active: datetime

    model_config = {"from_attributes": True}


class AthleteProfile(AthleteOut):
    """Extended profile with rank progress and badge details."""
    rank_progress: dict | None = None     # {current_rank, next_rank, progress_pct, points_to_next}
    badge_details: list[dict] | None = None  # [{id, name, icon, desc}]


class LeaderboardEntry(BaseModel):
    athlete_id: str
    name: str
    total_points: int
    rank_level: str
    tests_completed: int
    badges_count: int

    model_config = {"from_attributes": True}


# ─── Upload ───────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    size_bytes: int
    message: str


# ─── Process ──────────────────────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    file_id: str
    test_type: str = Field(..., pattern="^(T3|T4|T5|T8|T9)$")
    athlete_id: str | None = None
    athlete_info: AthleteCreate | None = None  # If no athlete_id, create inline


class MetricResult(BaseModel):
    """Returned by each AI analyzer."""
    primary_metric: float | None
    secondary_metrics: dict[str, Any]
    valid: bool
    confidence_score: float
    cheat_flags: list[str]
    cheat_score: float
    debug_info: dict[str, Any] = {}
    # Grading (new)
    grade: str | None = None
    form_score: float | None = None
    points_awarded: int = 0
    benchmark_threshold: float | None = None


class ProcessResponse(BaseModel):
    session_id: str
    test_type: str
    athlete_id: str
    result: MetricResult
    message: str


# ─── Results ──────────────────────────────────────────────────────────────────

class SessionSummary(BaseModel):
    session_id: str
    athlete_id: str
    athlete_name: str | None
    test_type: str
    status: str
    start_time: datetime
    primary_metric: float | None
    valid: bool | None
    confidence_score: float | None
    grade: str | None = None
    points_awarded: int = 0

    model_config = {"from_attributes": True}


class ResultDetail(BaseModel):
    session_id: str
    athlete_id: str
    test_type: str
    primary_metric: float | None
    secondary_metrics: dict[str, Any] | None
    valid: bool
    confidence_score: float | None
    cheat_flags: list[str] | None
    cheat_score: float | None
    grade: str | None = None
    form_score: float | None = None
    points_awarded: int = 0
    start_time: datetime

    model_config = {"from_attributes": True}


# ─── Benchmarks ───────────────────────────────────────────────────────────────

class BenchmarkInfo(BaseModel):
    name: str
    unit: str
    higher_is_better: bool
    male: dict[str, float]
    female: dict[str, float]


# ─── Auth ─────────────────────────────────────────────────────────────────────

class AuthRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=120)
    mobile: str | None = Field(default=None, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)


class AuthLoginRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)


class AuthUserOut(BaseModel):
    user_id: str
    full_name: str
    email: str | None
    mobile: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: AuthUserOut


class AuthMessage(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=120)


class ForgotPasswordConfirm(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=120)
    code: str = Field(..., min_length=4, max_length=12)
    new_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordResponse(BaseModel):
    message: str
    expires_in_seconds: int
    dev_reset_code: str | None = None


class AuthSessionOut(BaseModel):
    session_id: str
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    current: bool = False

    model_config = {"from_attributes": True}


class CoachOverview(BaseModel):
    total_athletes: int
    total_sessions: int
    completed_sessions: int
    invalid_sessions: int
    valid_rate_pct: float
    avg_confidence_pct: float


class AthleteLinkRequest(BaseModel):
    athlete_id: str
