from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.utils.enums import (
    TRANSACTION_TYPE_EXPENSE,
    TRANSACTION_TYPE_INCOME,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _validate_transaction_type(value: str) -> str:
    if value not in {TRANSACTION_TYPE_INCOME, TRANSACTION_TYPE_EXPENSE}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="transaction_type must be 'income' or 'expense'",
        )
    return value


def _get_user_category(db: Session, user_id: UUID, category_id: UUID) -> Category:
    stmt = select(Category).where(
        Category.id == category_id,
        Category.user_id == user_id,
    )
    category = db.execute(stmt).scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return category


def _get_user_account(db: Session, user_id: UUID, account_id: UUID) -> Account:
    stmt = select(Account).where(
        Account.id == account_id,
        Account.user_id == user_id,
    )
    account = db.execute(stmt).scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return account


def _get_user_transaction(db: Session, user_id: UUID, transaction_id: UUID) -> Transaction:
    stmt = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    )
    transaction = db.execute(stmt).scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return transaction


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    transaction_type: str | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    account_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    stmt = select(Transaction).where(Transaction.user_id == current_user.id)

    if transaction_type:
        _validate_transaction_type(transaction_type)
        stmt = stmt.where(Transaction.transaction_type == transaction_type)

    if category_id:
        stmt = stmt.where(Transaction.category_id == category_id)

    if account_id:
        stmt = stmt.where(Transaction.account_id == account_id)

    stmt = stmt.order_by(
        desc(Transaction.transaction_date),
        desc(Transaction.created_at),
    ).limit(limit)

    return db.execute(stmt).scalars().all()


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_user_transaction(db, current_user.id, transaction_id)


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_transaction_type(payload.transaction_type)

    if payload.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="amount must be greater than 0",
        )

    _get_user_category(db, current_user.id, payload.category_id)
    _get_user_account(db, current_user.id, payload.account_id)

    transaction = Transaction(
        user_id=current_user.id,
        transaction_type=payload.transaction_type,
        transaction_date=payload.transaction_date,
        amount=payload.amount,
        category_id=payload.category_id,
        account_id=payload.account_id,
        note=payload.note.strip() if payload.note else None,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = _get_user_transaction(db, current_user.id, transaction_id)

    _validate_transaction_type(payload.transaction_type)

    if payload.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="amount must be greater than 0",
        )

    _get_user_category(db, current_user.id, payload.category_id)
    _get_user_account(db, current_user.id, payload.account_id)

    transaction.transaction_type = payload.transaction_type
    transaction.transaction_date = payload.transaction_date
    transaction.amount = payload.amount
    transaction.category_id = payload.category_id
    transaction.account_id = payload.account_id
    transaction.note = payload.note.strip() if payload.note else None

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", response_model=MessageResponse)
def delete_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = _get_user_transaction(db, current_user.id, transaction_id)

    db.delete(transaction)
    db.commit()

    return MessageResponse(message="Transaction deleted successfully")