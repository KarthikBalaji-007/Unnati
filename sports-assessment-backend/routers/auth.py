"""
auth.py – Router for user authentication.
Provides register/login/logout/me with bearer token sessions.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import AppUser, AuthSession, PasswordResetCode
from schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    AuthUserOut,
    AuthMessage,
    ForgotPasswordRequest,
    ForgotPasswordConfirm,
    ForgotPasswordResponse,
    AuthSessionOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_TTL_DAYS = 7
RESET_CODE_TTL_MINUTES = 10
PBKDF2_ITERATIONS = 120_000


def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None


def _normalize_mobile(mobile: str | None) -> str | None:
    if mobile is None:
        return None
    digits = re.sub(r"\D", "", mobile)
    return digits or None


def _hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return salt.hex(), digest.hex()


def _verify_password(password: str, stored_salt: str, stored_hash: str) -> bool:
    _, computed_hash = _hash_password(password, stored_salt)
    return hmac.compare_digest(computed_hash, stored_hash)


def _new_session(db: Session, user: AppUser) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.utcnow() + timedelta(days=SESSION_TTL_DAYS)

    session = AuthSession(
        session_id=str(uuid.uuid4()),
        user_id=user.user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    return token, expires_at


def _to_user_out(user: AppUser) -> AuthUserOut:
    return AuthUserOut(
        user_id=user.user_id,
        full_name=user.full_name,
        email=user.email,
        mobile=user.mobile,
        created_at=user.created_at,
    )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing.")
    parts = authorization.strip().split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise HTTPException(status_code=401, detail="Invalid authorization header format.")
    return parts[1]


def _get_authenticated_session(db: Session, authorization: str | None) -> tuple[AppUser, AuthSession]:
    token = _extract_bearer_token(authorization)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    session = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == token_hash)
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    if session.expires_at <= datetime.utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")

    user = db.get(AppUser, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive or does not exist.")

    session.last_used_at = datetime.utcnow()
    db.commit()
    return user, session


def get_current_user_optional(db: Session, authorization: str | None) -> AppUser | None:
    if not authorization:
        return None
    try:
        user, _ = _get_authenticated_session(db, authorization)
        return user
    except HTTPException:
        return None


def _resolve_user_by_identifier(db: Session, identifier: str) -> AppUser | None:
    ident = identifier.strip()
    if "@" in ident:
        return db.query(AppUser).filter(AppUser.email == _normalize_email(ident)).first()
    mobile = _normalize_mobile(ident)
    if not mobile:
        return None
    return db.query(AppUser).filter(AppUser.mobile == mobile).first()


@router.post("/register", response_model=AuthResponse)
def register(body: AuthRegisterRequest, db: Session = Depends(get_db)):
    email = _normalize_email(body.email)
    mobile = _normalize_mobile(body.mobile)
    full_name = body.full_name.strip()

    if not email and not mobile:
        raise HTTPException(status_code=422, detail="Provide at least one identifier: email or mobile.")
    if mobile and not (8 <= len(mobile) <= 15):
        raise HTTPException(status_code=422, detail="Mobile number must contain 8 to 15 digits.")

    if email and db.query(AppUser).filter(AppUser.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    if mobile and db.query(AppUser).filter(AppUser.mobile == mobile).first():
        raise HTTPException(status_code=409, detail="An account with this mobile already exists.")

    salt_hex, password_hash = _hash_password(body.password)
    user = AppUser(
        user_id=str(uuid.uuid4()),
        full_name=full_name,
        email=email,
        mobile=mobile,
        password_hash=password_hash,
        password_salt=salt_hex,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token, expires_at = _new_session(db, user)
    return AuthResponse(
        token=token,
        token_type="bearer",
        expires_at=expires_at,
        user=_to_user_out(user),
    )


@router.post("/login", response_model=AuthResponse)
def login(body: AuthLoginRequest, db: Session = Depends(get_db)):
    user = _resolve_user_by_identifier(db, body.identifier)
    if "@" not in body.identifier and not _normalize_mobile(body.identifier):
        raise HTTPException(status_code=422, detail="Enter a valid email or mobile number.")

    if not user or not _verify_password(body.password, user.password_salt, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is inactive.")

    token, expires_at = _new_session(db, user)
    return AuthResponse(
        token=token,
        token_type="bearer",
        expires_at=expires_at,
        user=_to_user_out(user),
    )


@router.get("/me", response_model=AuthUserOut)
def me(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user, _ = _get_authenticated_session(db, authorization)
    return _to_user_out(user)


@router.post("/logout", response_model=AuthMessage)
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _, session = _get_authenticated_session(db, authorization)
    db.delete(session)
    db.commit()
    return AuthMessage(message="Logged out successfully.")


@router.post("/forgot-password/request", response_model=ForgotPasswordResponse)
def request_password_reset(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = _resolve_user_by_identifier(db, body.identifier)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found for this identifier.")

    raw_code = "".join(secrets.choice("0123456789") for _ in range(6))
    code_hash = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
    expires_at = datetime.utcnow() + timedelta(minutes=RESET_CODE_TTL_MINUTES)

    # invalidate old pending codes
    old_codes = (
        db.query(PasswordResetCode)
        .filter(PasswordResetCode.user_id == user.user_id, PasswordResetCode.used.is_(False))
        .all()
    )
    for item in old_codes:
        item.used = True

    reset = PasswordResetCode(
        reset_id=str(uuid.uuid4()),
        user_id=user.user_id,
        code_hash=code_hash,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset)
    db.commit()
    return ForgotPasswordResponse(
        message="Password reset code generated.",
        expires_in_seconds=RESET_CODE_TTL_MINUTES * 60,
        dev_reset_code=raw_code,
    )


@router.post("/forgot-password/confirm", response_model=AuthMessage)
def confirm_password_reset(body: ForgotPasswordConfirm, db: Session = Depends(get_db)):
    user = _resolve_user_by_identifier(db, body.identifier)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found for this identifier.")

    submitted_hash = hashlib.sha256(body.code.strip().encode("utf-8")).hexdigest()
    reset = (
        db.query(PasswordResetCode)
        .filter(
            PasswordResetCode.user_id == user.user_id,
            PasswordResetCode.used.is_(False),
            PasswordResetCode.code_hash == submitted_hash,
        )
        .order_by(PasswordResetCode.created_at.desc())
        .first()
    )
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid reset code.")
    if reset.expires_at <= datetime.utcnow():
        reset.used = True
        db.commit()
        raise HTTPException(status_code=400, detail="Reset code expired.")

    salt_hex, password_hash = _hash_password(body.new_password)
    user.password_salt = salt_hex
    user.password_hash = password_hash
    reset.used = True

    # revoke all active sessions on password reset
    sessions = db.query(AuthSession).filter(AuthSession.user_id == user.user_id).all()
    for session in sessions:
        db.delete(session)

    db.commit()
    return AuthMessage(message="Password reset successful. Please log in again.")


@router.get("/sessions", response_model=list[AuthSessionOut])
def list_auth_sessions(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _, current_session = _get_authenticated_session(db, authorization)
    sessions = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == current_session.user_id)
        .order_by(AuthSession.created_at.desc())
        .all()
    )
    return [
        AuthSessionOut(
            session_id=s.session_id,
            created_at=s.created_at,
            last_used_at=s.last_used_at,
            expires_at=s.expires_at,
            current=s.session_id == current_session.session_id,
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", response_model=AuthMessage)
def revoke_session(
    session_id: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _, current_session = _get_authenticated_session(db, authorization)
    target = db.get(AuthSession, session_id)
    if not target or target.user_id != current_session.user_id:
        raise HTTPException(status_code=404, detail="Session not found.")
    db.delete(target)
    db.commit()
    return AuthMessage(message="Session revoked.")


@router.post("/sessions/revoke-all", response_model=AuthMessage)
def revoke_all_sessions(
    keep_current: bool = True,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _, current_session = _get_authenticated_session(db, authorization)
    sessions = db.query(AuthSession).filter(AuthSession.user_id == current_session.user_id).all()
    for item in sessions:
        if keep_current and item.session_id == current_session.session_id:
            continue
        db.delete(item)
    db.commit()
    return AuthMessage(message="Sessions revoked successfully.")
