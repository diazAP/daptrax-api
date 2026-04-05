from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import MessageResponse
from app.core.audit import write_audit_log
from app.utils.enums import TARGET_TYPE_CATEGORY

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Category)
        .where(Category.user_id == current_user.id)
        .order_by(Category.sort_order.asc(), Category.name.asc())
    )
    return db.execute(stmt).scalars().all()


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_name = payload.name.strip()

    existing_stmt = select(Category).where(
        Category.user_id == current_user.id,
        func.lower(Category.name) == normalized_name.lower(),
    )
    existing = db.execute(existing_stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists",
        )

    category = Category(
        user_id=current_user.id,
        name=normalized_name,
        color_key=payload.color_key,
        icon_key=payload.icon_key,
        sort_order=payload.sort_order,
    )

    db.add(category)
    write_audit_log(
        db,
        action="category_create",
        target_type=TARGET_TYPE_CATEGORY,
        actor_user_id=current_user.id,
        target_id=category.id,
        meta_json={"name": category.name},
    )
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Category).where(
        Category.id == category_id,
        Category.user_id == current_user.id,
    )
    category = db.execute(stmt).scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    normalized_name = payload.name.strip()

    existing_stmt = select(Category).where(
        Category.user_id == current_user.id,
        func.lower(Category.name) == normalized_name.lower(),
        Category.id != category_id,
    )
    existing = db.execute(existing_stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists",
        )

    category.name = normalized_name
    category.color_key = payload.color_key
    category.icon_key = payload.icon_key
    category.sort_order = payload.sort_order

    db.add(category)

    write_audit_log(
        db,
        action="category_update",
        target_type=TARGET_TYPE_CATEGORY,
        actor_user_id=current_user.id,
        target_id=category.id,
        meta_json={"name": category.name},
    )    

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", response_model=MessageResponse)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Category).where(
        Category.id == category_id,
        Category.user_id == current_user.id,
    )
    category = db.execute(stmt).scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    transaction_stmt = select(Transaction).where(
        Transaction.user_id == current_user.id,
        Transaction.category_id == category_id,
    )
    linked_transaction = db.execute(transaction_stmt).scalar_one_or_none()

    if linked_transaction:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category is already used by transactions",
        )

    db.delete(category)

    write_audit_log(
        db,
        action="category_delete",
        target_type=TARGET_TYPE_CATEGORY,
        actor_user_id=current_user.id,
        target_id=category.id,
        meta_json={"name": category.name},
    )

    db.commit()

    return MessageResponse(message="Category deleted successfully")