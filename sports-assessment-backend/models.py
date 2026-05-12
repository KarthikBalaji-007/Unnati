"""
models.py
---------
SQLAlchemy ORM models representing the database schema.
Athlete, TestSession, TestResult — with points, ranking, badges, and grades.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Athlete(Base):
    __tablename__ = "athletes"

    athlete_id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("app_users.user_id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String, nullable=False)  # "male" | "female" | "other"
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    organization: Mapped[str | None] = mapped_column(String, nullable=True)

    # Profile & ranking
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    rank_level: Mapped[str] = mapped_column(String, default="Bronze")  # Bronze|Silver|Gold|Platinum
    badges: Mapped[list | None] = mapped_column(JSON, default=list)
    days_active: Mapped[int] = mapped_column(Integer, default=1)
    tests_completed: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list["TestSession"]] = relationship("TestSession", back_populates="athlete")


class TestSession(Base):
    __tablename__ = "test_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.athlete_id"), nullable=False)
    test_type: Mapped[str] = mapped_column(String, nullable=False)  # T3|T4|T5|T8|T9
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|completed|invalid
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    device_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    athlete: Mapped["Athlete"] = relationship("Athlete", back_populates="sessions")
    result: Mapped["TestResult | None"] = relationship("TestResult", back_populates="session", uselist=False)


class TestResult(Base):
    __tablename__ = "test_results"

    result_id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("test_sessions.session_id"), nullable=False)
    primary_metric: Mapped[float | None] = mapped_column(Float, nullable=True)
    secondary_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    valid: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cheat_flags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cheat_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Grading & scoring (new)
    grade: Mapped[str | None] = mapped_column(String, nullable=True)  # A|B|C|D|F
    form_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0–100%
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["TestSession"] = relationship("TestSession", back_populates="result")


class AppUser(Base):
    __tablename__ = "app_users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    mobile: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    password_salt: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions: Mapped[list["AuthSession"]] = relationship("AuthSession", back_populates="user")
    athletes: Mapped[list["Athlete"]] = relationship("Athlete", backref="owner")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("app_users.user_id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["AppUser"] = relationship("AppUser", back_populates="sessions")


class PasswordResetCode(Base):
    __tablename__ = "password_reset_codes"

    reset_id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("app_users.user_id"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
