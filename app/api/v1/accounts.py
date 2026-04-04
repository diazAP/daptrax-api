from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Account)
        .where(Account.user_id == current_user.id)
        .order_by(Account.sort_order.asc(), Account.name.asc())
    )
    return db.execute(stmt).scalars().all()


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_name = payload.name.strip()

    existing_stmt = select(Account).where(
        Account.user_id == current_user.id,
        func.lower(Account.name) == normalized_name.lower(),
    )
    existing = db.execute(existing_stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account name already exists",
        )

    account = Account(
        user_id=current_user.id,
        name=normalized_name,
        initial_balance=payload.initial_balance,
        color_key=payload.color_key,
        icon_key=payload.icon_key,
        sort_order=payload.sort_order,
    )

    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: UUID,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Account).where(
        Account.id == account_id,
        Account.user_id == current_user.id,
    )
    account = db.execute(stmt).scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    normalized_name = payload.name.strip()

    existing_stmt = select(Account).where(
        Account.user_id == current_user.id,
        func.lower(Account.name) == normalized_name.lower(),
        Account.id != account_id,
    )
    existing = db.execute(existing_stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account name already exists",
        )

    account.name = normalized_name
    account.initial_balance = payload.initial_balance
    account.color_key = payload.color_key
    account.icon_key = payload.icon_key
    account.sort_order = payload.sort_order

    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", response_model=MessageResponse)
def delete_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Account).where(
        Account.id == account_id,
        Account.user_id == current_user.id,
    )
    account = db.execute(stmt).scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    transaction_stmt = select(Transaction).where(
        Transaction.user_id == current_user.id,
        Transaction.account_id == account_id,
    )
    linked_transaction = db.execute(transaction_stmt).scalar_one_or_none()

    if linked_transaction:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account is already used by transactions",
        )

    db.delete(account)
    db.commit()

    return MessageResponse(message="Account deleted successfully")