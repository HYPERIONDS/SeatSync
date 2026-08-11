from datetime import timedelta

import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest, RegisterRequest, TokenPair
from app.core.config import get_settings
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    token_hash,
    verify_password,
)
from app.core.time import utcnow
from app.users.models import RefreshToken, User


def register(db: Session, data: RegisterRequest) -> User:
    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        role=data.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from exc
    db.refresh(user)
    return user


def _issue_pair(db: Session, user: User) -> TokenPair:
    settings = get_settings()
    access, _ = create_token(
        str(user.id), "access", timedelta(minutes=settings.access_token_minutes)
    )
    refresh, jti = create_token(
        str(user.id), "refresh", timedelta(days=settings.refresh_token_days)
    )
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=token_hash(refresh),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
        )
    )
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh, user=user)


def login(db: Session, data: LoginRequest) -> TokenPair:
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _issue_pair(db, user)


def rotate_refresh_token(db: Session, raw_token: str) -> TokenPair:
    try:
        payload = decode_token(raw_token, "refresh")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    stored = db.scalar(
        select(RefreshToken).where(
            RefreshToken.jti == payload.get("jti"),
            RefreshToken.token_hash == token_hash(raw_token),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > utcnow(),
        )
    )
    if stored is None:
        raise HTTPException(status_code=401, detail="Refresh token is expired or revoked")
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    stored.revoked_at = utcnow()
    db.flush()
    return _issue_pair(db, user)
