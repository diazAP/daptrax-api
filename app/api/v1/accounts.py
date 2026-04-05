from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.schemas.common import MessageResponse
from app.utils.enums import TRANSACTION_TYPE_EXPENSE, TRANSACTION_TYPE_INCOME

from app.core.audit import write_audit_log
from app.utils.enums import TARGET_TYPE_ACCOUNT

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _build_account_balance_map(db: Session, user_id: UUID):
    income_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_INCOME, Transaction.amount),
        else_=0,
    )
    expense_case = case(
        (Transaction.transaction_type == TRANSACTION_TYPE_EXPENSE, Transaction.amount),
        else_=0,
    )

    tx_rows = db.execute(
        select(
            Transaction.account_id.label("account_id"),
            func.coalesce(func.sum(income_case), 0).label("income_total"),
            func.coalesce(func.sum(expense_case), 0).label("expense_total"),
        )
        .where(Transaction.user_id == user_id)
        .group_by(Transaction.account_id)
    ).all()

    transfer_in_rows = db.execute(
        select(
            Transfer.to_account_id.label("account_id"),
            func.coalesce(func.sum(Transfer.amount), 0).label("transfer_in_total"),
        )
        .where(Transfer.user_id == user_id)
        .group_by(Transfer.to_account_id)
    ).all()

    transfer_out_rows = db.execute(
        select(
            Transfer.from_account_id.label("account_id"),
            func.coalesce(func.sum(Transfer.amount), 0).label("transfer_out_total"),
        )
        .where(Transfer.user_id == user_id)
        .group_by(Transfer.from_account_id)
    ).all()

    result: dict[UUID, dict[str, Decimal]] = {}

    for row in tx_rows:
        result[row.account_id] = {
            "income_total": Decimal(row.income_total or 0),
            "expense_total": Decimal(row.expense_total or 0),
            "transfer_in_total": Decimal(0),
            "transfer_out_total": Decimal(0),
        }

    for row in transfer_in_rows:
        result.setdefault(
            row.account_id,
            {
                "income_total": Decimal(0),
                "expense_total": Decimal(0),
                "transfer_in_total": Decimal(0),
                "transfer_out_total": Decimal(0),
            },
        )
        result[row.account_id]["transfer_in_total"] = Decimal(row.transfer_in_total or 0)

    for row in transfer_out_rows:
        result.setdefault(
            row.account_id,
            {
                "income_total": Decimal(0),
                "expense_total": Decimal(0),
                "transfer_in_total": Decimal(0),
                "transfer_out_total": Decimal(0),
            },
        )
        result[row.account_id]["transfer_out_total"] = Decimal(row.transfer_out_total or 0)

    return result


def _to_account_response(account: Account, balance_data: dict[str, Decimal] | None = None) -> AccountResponse:
    balance_data = balance_data or {
        "income_total": Decimal(0),
        "expense_total": Decimal(0),
        "transfer_in_total": Decimal(0),
        "transfer_out_total": Decimal(0),
    }

    initial_balance = Decimal(account.initial_balance or 0)
    income_total = Decimal(balance_data["income_total"])
    expense_total = Decimal(balance_data["expense_total"])
    transfer_in_total = Decimal(balance_data["transfer_in_total"])
    transfer_out_total = Decimal(balance_data["transfer_out_total"])

    current_balance = (
        initial_balance
        + income_total
        - expense_total
        + transfer_in_total
        - transfer_out_total
    )

    return AccountResponse(
        id=account.id,
        name=account.name,
        initial_balance=initial_balance,
        total_income=income_total,
        total_expense=expense_total,
        total_transfer_in=transfer_in_total,
        total_transfer_out=transfer_out_total,
        current_balance=current_balance,
        color_key=account.color_key,
        icon_key=account.icon_key,
        sort_order=account.sort_order,
    )


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
    accounts = db.execute(stmt).scalars().all()

    balance_map = _build_account_balance_map(db, current_user.id)

    return [
        _to_account_response(account, balance_map.get(account.id))
        for account in accounts
    ]


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
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

    balance_map = _build_account_balance_map(db, current_user.id)
    return _to_account_response(account, balance_map.get(account.id))


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

    write_audit_log(
        db,
        action="account_create",
        target_type=TARGET_TYPE_ACCOUNT,
        actor_user_id=current_user.id,
        target_id=account.id,
        meta_json={"name": account.name},
    )

    db.commit()
    db.refresh(account)
    return _to_account_response(account)


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

    has_transaction = db.execute(
        select(Transaction.id).where(
            Transaction.user_id == current_user.id,
            Transaction.account_id == account_id,
        )
    ).scalar_one_or_none()

    has_transfer = db.execute(
        select(Transfer.id).where(
            Transfer.user_id == current_user.id,
            (Transfer.from_account_id == account_id) | (Transfer.to_account_id == account_id),
        )
    ).scalar_one_or_none()

    if (has_transaction or has_transfer) and Decimal(payload.initial_balance) != Decimal(account.initial_balance):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="initial_balance cannot be changed after account has activity",
        )

    account.name = normalized_name
    account.initial_balance = payload.initial_balance
    account.color_key = payload.color_key
    account.icon_key = payload.icon_key
    account.sort_order = payload.sort_order

    db.add(account)

    write_audit_log(
        db,
        action="account_update",
        target_type=TARGET_TYPE_ACCOUNT,
        actor_user_id=current_user.id,
        target_id=account.id,
        meta_json={"name": account.name},
    )

    db.commit()
    db.refresh(account)

    balance_map = _build_account_balance_map(db, current_user.id)
    return _to_account_response(account, balance_map.get(account.id))


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

    linked_transaction = db.execute(
        select(Transaction.id).where(
            Transaction.user_id == current_user.id,
            Transaction.account_id == account_id,
        )
    ).scalar_one_or_none()

    if linked_transaction:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account is already used by transactions",
        )

    linked_transfer = db.execute(
        select(Transfer.id).where(
            Transfer.user_id == current_user.id,
            (Transfer.from_account_id == account_id) | (Transfer.to_account_id == account_id),
        )
    ).scalar_one_or_none()

    if linked_transfer:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account is already used by transfers",
        )

    db.delete(account)

    write_audit_log(
        db,
        action="account_delete",
        target_type=TARGET_TYPE_ACCOUNT,
        actor_user_id=current_user.id,
        target_id=account.id,
        meta_json={"name": account.name},
    )

    db.commit()

    return MessageResponse(message="Account deleted successfully")