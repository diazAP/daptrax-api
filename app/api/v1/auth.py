from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    generate_session_token,
    hash_session_token,
    verify_password,
)
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.auth import AdminLoginRequest
from app.schemas.user import MeResponse
from app.utils.enums import AUTH_PROVIDER_LOCAL, ROLE_ADMIN

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/admin/login", response_model=MeResponse)
def admin_login(
    payload: AdminLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    stmt = select(User).where(
        or_(
            User.email == payload.login,
            User.username == payload.login,
        )
    )
    user = db.execute(stmt).scalar_one_or_none()

    if (
        not user
        or user.role != ROLE_ADMIN
        or user.auth_provider != AUTH_PROVIDER_LOCAL
        or not user.password_hash
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials",
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials",
        )

    raw_session_token = generate_session_token()
    token_hash = hash_session_token(raw_session_token)
    expires_at = datetime.utcnow() + timedelta(days=settings.session_days)

    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=token_hash,
        expires_at=expires_at,
    )

    user.last_login_at = datetime.utcnow()

    db.add(auth_session)
    db.add(user)
    db.commit()
    db.refresh(user)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_session_token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=settings.session_days * 24 * 60 * 60,
        path="/",
    )

    return user


@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Ambil semua session aktif user saat logout dari session saat ini tidak dipetakan langsung,
    # jadi pendekatan sederhana untuk sekarang: revoke session aktif user yang belum revoked dan belum expired.
    stmt = select(AuthSession).where(
        AuthSession.user_id == current_user.id,
        AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > datetime.utcnow(),
    )
    sessions = db.execute(stmt).scalars().all()

    now = datetime.utcnow()
    for session in sessions:
        session.revoked_at = now
        db.add(session)

    db.commit()

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
    )

    return {"message": "Logged out successfully"}