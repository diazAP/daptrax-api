from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.schemas.user import (
    AdminUserListResponse,
    AdminUserStatusUpdateRequest,
    AdminUserUpdateRequest,
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _get_user_or_404(db: Session, user_id: UUID) -> User:
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get("", response_model=list[AdminUserListResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(User)

    if search:
        search_value = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(User.full_name).like(search_value),
                func.lower(User.email).like(search_value),
                func.lower(User.username).like(search_value),
            )
        )

    stmt = stmt.order_by(User.created_at.desc()).limit(limit)

    return db.execute(stmt).scalars().all()


@router.get("/{user_id}", response_model=AdminUserListResponse)
def get_user_detail(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return _get_user_or_404(db, user_id)


@router.put("/{user_id}", response_model=AdminUserListResponse)
def update_user(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    user = _get_user_or_404(db, user_id)

    # Admin tunggal tetap tidak boleh dinonaktifkan atau diubah sembarangan oleh endpoint ini.
    if user.id == current_admin.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primary admin cannot be deactivated",
        )

    user.full_name = payload.full_name.strip()
    user.is_active = payload.is_active

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=AdminUserListResponse)
def update_user_status(
    user_id: UUID,
    payload: AdminUserStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    user = _get_user_or_404(db, user_id)

    if user.id == current_admin.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primary admin cannot be deactivated",
        )

    user.is_active = payload.is_active

    db.add(user)
    db.commit()
    db.refresh(user)
    return user