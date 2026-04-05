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
from uuid import uuid4

from fastapi import Request
from sqlalchemy.exc import IntegrityError

from app.core.oauth import oauth
from app.models.user_google_account import UserGoogleAccount
from app.models.user_setting import UserSetting
from app.utils.enums import AUTH_PROVIDER_GOOGLE, ROLE_USER

from fastapi.responses import RedirectResponse

def _seed_default_categories_and_accounts(db: Session, user_id):
    from app.models.category import Category
    from app.models.account import Account

    default_categories = [
        "Makanan",
        "Travel",
        "Gaji",
        "Youtube",
    ]
    default_accounts = [
        "Cash",
        "BCA",
        "GoPay",
        "OVO",
    ]

    for idx, name in enumerate(default_categories, start=1):
        db.add(
            Category(
                user_id=user_id,
                name=name,
                sort_order=idx,
            )
        )

    for idx, name in enumerate(default_accounts, start=1):
        db.add(
            Account(
                user_id=user_id,
                name=name,
                initial_balance=0,
                sort_order=idx,
            )
        )

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

@router.get("/google/login")
async def google_login(request: Request):
    if not settings.google_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google redirect URI is not configured",
        )

    return await oauth.google.authorize_redirect(
        request,
        settings.google_redirect_uri,
    )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured",
        )

    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")

    if not userinfo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to obtain Google user info",
        )

    google_sub = userinfo.get("sub")
    google_email = userinfo.get("email")
    full_name = userinfo.get("name") or google_email

    if not google_sub or not google_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google user info",
        )

    google_stmt = select(UserGoogleAccount).where(
        UserGoogleAccount.google_sub == google_sub
    )
    google_account = db.execute(google_stmt).scalar_one_or_none()

    if google_account:
        user_stmt = select(User).where(User.id == google_account.user_id)
        user = db.execute(user_stmt).scalar_one_or_none()
    else:
        user_stmt = select(User).where(User.email == google_email)
        user = db.execute(user_stmt).scalar_one_or_none()

        if user:
            # link existing user to google
            google_account = UserGoogleAccount(
                user_id=user.id,
                google_sub=google_sub,
                google_email=google_email,
            )
            db.add(google_account)
        else:
            user = User(
                email=google_email,
                username=None,
                full_name=full_name,
                role=ROLE_USER,
                auth_provider=AUTH_PROVIDER_GOOGLE,
                password_hash=None,
                is_active=True,
            )
            db.add(user)
            db.flush()

            db.add(
                UserGoogleAccount(
                    user_id=user.id,
                    google_sub=google_sub,
                    google_email=google_email,
                )
            )
            db.add(
                UserSetting(
                    user_id=user.id,
                    currency_code="IDR",
                    timezone="Asia/Jakarta",
                    week_start_day="monday",
                )
            )

            _seed_default_categories_and_accounts(db, user.id)

    user.full_name = full_name
    user.last_login_at = datetime.utcnow()
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create or link Google user",
        )

    db.refresh(user)

    raw_session_token = generate_session_token()
    token_hash = hash_session_token(raw_session_token)
    expires_at = datetime.utcnow() + timedelta(days=settings.session_days)

    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(auth_session)
    db.commit()

    response = RedirectResponse(
        url=settings.post_login_redirect_url,
        status_code=status.HTTP_302_FOUND,
    ) 

    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_session_token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=settings.session_days * 24 * 60 * 60,
        path="/",
    )
    return response

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