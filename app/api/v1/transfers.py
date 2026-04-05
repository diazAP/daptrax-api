from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.account import Account
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.transfer import TransferCreate, TransferResponse, TransferUpdate

from app.core.audit import write_audit_log
from app.utils.enums import TARGET_TYPE_TRANSFER

router = APIRouter(prefix="/transfers", tags=["transfers"])


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


def _get_user_transfer(db: Session, user_id: UUID, transfer_id: UUID) -> Transfer:
    stmt = select(Transfer).where(
        Transfer.id == transfer_id,
        Transfer.user_id == user_id,
    )
    transfer = db.execute(stmt).scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found",
        )

    return transfer


def _validate_transfer(payload: TransferCreate | TransferUpdate, db: Session, user_id: UUID):
    if payload.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="amount must be greater than 0",
        )

    if payload.from_account_id == payload.to_account_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="from_account_id and to_account_id must be different",
        )

    _get_user_account(db, user_id, payload.from_account_id)
    _get_user_account(db, user_id, payload.to_account_id)


@router.get("", response_model=list[TransferResponse])
def list_transfers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    stmt = select(Transfer).where(Transfer.user_id == current_user.id)

    if account_id:
        stmt = stmt.where(
            (Transfer.from_account_id == account_id) | (Transfer.to_account_id == account_id)
        )

    stmt = stmt.order_by(
        desc(Transfer.transfer_date),
        desc(Transfer.created_at),
    ).limit(limit)

    return db.execute(stmt).scalars().all()


@router.get("/{transfer_id}", response_model=TransferResponse)
def get_transfer(
    transfer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_user_transfer(db, current_user.id, transfer_id)


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_transfer(payload, db, current_user.id)

    transfer = Transfer(
        user_id=current_user.id,
        transfer_date=payload.transfer_date,
        amount=payload.amount,
        from_account_id=payload.from_account_id,
        to_account_id=payload.to_account_id,
        note=payload.note.strip() if payload.note else None,
    )

    db.add(transfer)

    write_audit_log(
        db,
        action="transfer_create",
        target_type=TARGET_TYPE_TRANSFER,
        actor_user_id=current_user.id,
        target_id=transfer.id,
        meta_json={
            "amount": str(transfer.amount),
            "from_account_id": str(transfer.from_account_id),
            "to_account_id": str(transfer.to_account_id),
        },
    )

    db.commit()
    db.refresh(transfer)
    return transfer


@router.put("/{transfer_id}", response_model=TransferResponse)
def update_transfer(
    transfer_id: UUID,
    payload: TransferUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transfer = _get_user_transfer(db, current_user.id, transfer_id)
    _validate_transfer(payload, db, current_user.id)

    transfer.transfer_date = payload.transfer_date
    transfer.amount = payload.amount
    transfer.from_account_id = payload.from_account_id
    transfer.to_account_id = payload.to_account_id
    transfer.note = payload.note.strip() if payload.note else None

    db.add(transfer)

    write_audit_log(
        db,
        action="transfer_update",
        target_type=TARGET_TYPE_TRANSFER,
        actor_user_id=current_user.id,
        target_id=transfer.id,
        meta_json={
            "amount": str(transfer.amount),
            "from_account_id": str(transfer.from_account_id),
            "to_account_id": str(transfer.to_account_id),
        },
    )

    db.commit()
    db.refresh(transfer)
    return transfer


@router.delete("/{transfer_id}", response_model=MessageResponse)
def delete_transfer(
    transfer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transfer = _get_user_transfer(db, current_user.id, transfer_id)

    db.delete(transfer)

    write_audit_log(
        db,
        action="transfer_delete",
        target_type=TARGET_TYPE_TRANSFER,
        actor_user_id=current_user.id,
        target_id=transfer.id,
        meta_json={
            "amount": str(transfer.amount),
            "from_account_id": str(transfer.from_account_id),
            "to_account_id": str(transfer.to_account_id),
        },
    )   

    db.commit()

    return MessageResponse(message="Transfer deleted successfully")