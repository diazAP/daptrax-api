import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.deps import require_admin
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.backup import BackupImportError, BackupImportResult
from app.utils.enums import (
    TARGET_TYPE_BACKUP,
    TRANSACTION_TYPE_EXPENSE,
    TRANSACTION_TYPE_INCOME,
)

router = APIRouter(prefix="/admin/backups", tags=["admin-backups"])


def _get_target_user_or_404(db: Session, user_id: UUID) -> User:
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found",
        )
    return user


def _csv_response(filename: str, fieldnames: list[str], rows: list[dict]) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _read_csv_rows(file: UploadFile) -> list[dict]:
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded CSV",
        )

    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _to_decimal(value: str, field_name: str) -> Decimal:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field_name} is invalid decimal")


def _to_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValueError(f"{field_name} must be YYYY-MM-DD")


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _require_text(value: str | None, field_name: str) -> str:
    value = _normalize_text(value)
    if not value:
        raise ValueError(f"{field_name} is required")
    return value


def _find_category_by_name(db: Session, user_id: UUID, name: str) -> Category | None:
    stmt = select(Category).where(
        Category.user_id == user_id,
        func.lower(Category.name) == name.lower(),
    )
    return db.execute(stmt).scalar_one_or_none()


def _find_account_by_name(db: Session, user_id: UUID, name: str) -> Account | None:
    stmt = select(Account).where(
        Account.user_id == user_id,
        func.lower(Account.name) == name.lower(),
    )
    return db.execute(stmt).scalar_one_or_none()


def _account_has_activity(db: Session, user_id: UUID, account_id: UUID) -> bool:
    tx_exists = db.execute(
        select(Transaction.id).where(
            Transaction.user_id == user_id,
            Transaction.account_id == account_id,
        )
    ).scalar_one_or_none()

    if tx_exists:
        return True

    transfer_exists = db.execute(
        select(Transfer.id).where(
            Transfer.user_id == user_id,
            (Transfer.from_account_id == account_id) | (Transfer.to_account_id == account_id),
        )
    ).scalar_one_or_none()

    return transfer_exists is not None


@router.get("/export/categories")
def export_categories(
    user_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target_user = _get_target_user_or_404(db, user_id)

    rows = db.execute(
        select(Category)
        .where(Category.user_id == target_user.id)
        .order_by(Category.sort_order.asc(), Category.name.asc())
    ).scalars().all()

    data = [
        {
            "name": row.name,
            "color_key": row.color_key or "",
            "icon_key": row.icon_key or "",
            "sort_order": row.sort_order,
        }
        for row in rows
    ]

    write_audit_log(
        db,
        action="backup_export_categories",
        target_type=TARGET_TYPE_BACKUP,
        actor_user_id=current_admin.id,
        target_id=target_user.id,
        meta_json={"row_count": len(data)},
    )
    db.commit()

    return _csv_response(
        filename=f"categories_{target_user.id}.csv",
        fieldnames=["name", "color_key", "icon_key", "sort_order"],
        rows=data,
    )


@router.get("/export/accounts")
def export_accounts(
    user_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target_user = _get_target_user_or_404(db, user_id)

    rows = db.execute(
        select(Account)
        .where(Account.user_id == target_user.id)
        .order_by(Account.sort_order.asc(), Account.name.asc())
    ).scalars().all()

    data = [
        {
            "name": row.name,
            "initial_balance": str(row.initial_balance),
            "color_key": row.color_key or "",
            "icon_key": row.icon_key or "",
            "sort_order": row.sort_order,
        }
        for row in rows
    ]

    write_audit_log(
        db,
        action="backup_export_accounts",
        target_type=TARGET_TYPE_BACKUP,
        actor_user_id=current_admin.id,
        target_id=target_user.id,
        meta_json={"row_count": len(data)},
    )
    db.commit()

    return _csv_response(
        filename=f"accounts_{target_user.id}.csv",
        fieldnames=["name", "initial_balance", "color_key", "icon_key", "sort_order"],
        rows=data,
    )


@router.get("/export/transactions")
def export_transactions(
    user_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target_user = _get_target_user_or_404(db, user_id)

    rows = db.execute(
        select(
            Transaction.transaction_type,
            Transaction.transaction_date,
            Transaction.amount,
            Category.name.label("category_name"),
            Account.name.label("account_name"),
            Transaction.note,
        )
        .join(Category, Category.id == Transaction.category_id)
        .join(Account, Account.id == Transaction.account_id)
        .where(Transaction.user_id == target_user.id)
        .order_by(Transaction.transaction_date.asc(), Transaction.created_at.asc())
    ).all()

    data = [
        {
            "transaction_type": row.transaction_type,
            "transaction_date": row.transaction_date.isoformat(),
            "amount": str(row.amount),
            "category_name": row.category_name,
            "account_name": row.account_name,
            "note": row.note or "",
        }
        for row in rows
    ]

    write_audit_log(
        db,
        action="backup_export_transactions",
        target_type=TARGET_TYPE_BACKUP,
        actor_user_id=current_admin.id,
        target_id=target_user.id,
        meta_json={"row_count": len(data)},
    )
    db.commit()

    return _csv_response(
        filename=f"transactions_{target_user.id}.csv",
        fieldnames=["transaction_type", "transaction_date", "amount", "category_name", "account_name", "note"],
        rows=data,
    )


@router.get("/export/transfers")
def export_transfers(
    user_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target_user = _get_target_user_or_404(db, user_id)

    from_account = aliased(Account)
    to_account = aliased(Account)

    rows = db.execute(
        select(
            Transfer.transfer_date,
            Transfer.amount,
            from_account.name.label("from_account_name"),
            to_account.name.label("to_account_name"),
            Transfer.note,
        )
        .join(from_account, from_account.id == Transfer.from_account_id)
        .join(to_account, to_account.id == Transfer.to_account_id)
        .where(Transfer.user_id == target_user.id)
        .order_by(Transfer.transfer_date.asc(), Transfer.created_at.asc())
    ).all()

    data = [
        {
            "transfer_date": row.transfer_date.isoformat(),
            "amount": str(row.amount),
            "from_account_name": row.from_account_name,
            "to_account_name": row.to_account_name,
            "note": row.note or "",
        }
        for row in rows
    ]

    write_audit_log(
        db,
        action="backup_export_transfers",
        target_type=TARGET_TYPE_BACKUP,
        actor_user_id=current_admin.id,
        target_id=target_user.id,
        meta_json={"row_count": len(data)},
    )
    db.commit()

    return _csv_response(
        filename=f"transfers_{target_user.id}.csv",
        fieldnames=["transfer_date", "amount", "from_account_name", "to_account_name", "note"],
        rows=data,
    )


@router.post("/import/categories", response_model=BackupImportResult)
async def import_categories(
    user_id: UUID = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target_user = _get_target_user_or_404(db, user_id)
    rows = await _read_csv_rows(file)

    errors: list[BackupImportError] = []
    success_rows = 0

    for row_num, row in enumerate(rows, start=2):
        try:
            name = _require_text(row.get("name"), "name")
            color_key = _normalize_text(row.get("color_key"))
            icon_key = _normalize_text(row.get("icon_key"))
            sort_order = int((row.get("sort_order") or "0").strip())

            existing = _find_category_by_name(db, target_user.id, name)

            if existing:
                existing.color_key = color_key
                existing.icon_key = icon_key
                existing.sort_order = sort_order
                db.add(existing)
            else:
                db.add(
                    Category(
                        user_id=target_user.id,
                        name=name,
                        color_key=color_key,
                        icon_key=icon_key,
                        sort_order=sort_order,
                    )
                )

            db.commit()
            success_rows += 1
        except Exception as exc:
            db.rollback()
            errors.append(BackupImportError(row=row_num, message=str(exc)))

    write_audit_log(
        db,
        action="backup_import_categories",
        target_type=TARGET_TYPE_BACKUP,
        actor_user_id=current_admin.id,
        target_id=target_user.id,
        meta_json={
            "success_rows": success_rows,
            "failed_rows": len(errors),
            "total_rows": len(rows),
        },
    )
    db.commit()

    return BackupImportResult(
        total_rows=len(rows),
        success_rows=success_rows,
        failed_rows=len(errors),
        errors=errors,
    )


@router.post("/import/accounts", response_model=BackupImportResult)
async def import_accounts(
    user_id: UUID = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target_user = _get_target_user_or_404(db, user_id)
    rows = await _read_csv_rows(file)

    errors: list[BackupImportError] = []
    success_rows = 0

    for row_num, row in enumerate(rows, start=2):
        try:
            name = _require_text(row.get("name"), "name")
            initial_balance = _to_decimal(row.get("initial_balance"), "initial_balance")
            color_key = _normalize_text(row.get("color_key"))
            icon_key = _normalize_text(row.get("icon_key"))
            sort_order = int((row.get("sort_order") or "0").strip())

            existing = _find_account_by_name(db, target_user.id, name)

            if existing:
                if initial_balance != Decimal(existing.initial_balance) and _account_has_activity(db, target_user.id, existing.id):
                    raise ValueError("initial_balance cannot be changed after account has activity")

                existing.initial_balance = initial_balance
                existing.color_key = color_key
                existing.icon_key = icon_key
                existing.sort_order = sort_order
                db.add(existing)
            else:
                db.add(
                    Account(
                        user_id=target_user.id,
                        name=name,
                        initial_balance=initial_balance,
                        color_key=color_key,
                        icon_key=icon_key,
                        sort_order=sort_order,
                    )
                )

            db.commit()
            success_rows += 1
        except Exception as exc:
            db.rollback()
            errors.append(BackupImportError(row=row_num, message=str(exc)))

    write_audit_log(
        db,
        action="backup_import_accounts",
        target_type=TARGET_TYPE_BACKUP,
        actor_user_id=current_admin.id,
        target_id=target_user.id,
        meta_json={
            "success_rows": success_rows,
            "failed_rows": len(errors),
            "total_rows": len(rows),
        },
    )
    db.commit()

    return BackupImportResult(
        total_rows=len(rows),
        success_rows=success_rows,
        failed_rows=len(errors),
        errors=errors,
    )


@router.post("/import/transactions", response_model=BackupImportResult)
async def import_transactions(
    user_id: UUID = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target_user = _get_target_user_or_404(db, user_id)
    rows = await _read_csv_rows(file)

    errors: list[BackupImportError] = []
    success_rows = 0

    for row_num, row in enumerate(rows, start=2):
        try:
            transaction_type = _require_text(row.get("transaction_type"), "transaction_type").lower()
            if transaction_type not in {TRANSACTION_TYPE_INCOME, TRANSACTION_TYPE_EXPENSE}:
                raise ValueError("transaction_type must be 'income' or 'expense'")

            transaction_date = _to_date(row.get("transaction_date"), "transaction_date")
            amount = _to_decimal(row.get("amount"), "amount")
            if amount <= 0:
                raise ValueError("amount must be greater than 0")

            category_name = _require_text(row.get("category_name"), "category_name")
            account_name = _require_text(row.get("account_name"), "account_name")
            note = _normalize_text(row.get("note"))

            category = _find_category_by_name(db, target_user.id, category_name)
            if not category:
                raise ValueError(f"category '{category_name}' not found")

            account = _find_account_by_name(db, target_user.id, account_name)
            if not account:
                raise ValueError(f"account '{account_name}' not found")

            existing = db.execute(
                select(Transaction).where(
                    Transaction.user_id == target_user.id,
                    Transaction.transaction_type == transaction_type,
                    Transaction.transaction_date == transaction_date,
                    Transaction.amount == amount,
                    Transaction.category_id == category.id,
                    Transaction.account_id == account.id,
                    Transaction.note == note,
                )
            ).scalar_one_or_none()

            if existing:
                success_rows += 1
                continue

            db.add(
                Transaction(
                    user_id=target_user.id,
                    transaction_type=transaction_type,
                    transaction_date=transaction_date,
                    amount=amount,
                    category_id=category.id,
                    account_id=account.id,
                    note=note,
                )
            )

            db.commit()
            success_rows += 1
        except Exception as exc:
            db.rollback()
            errors.append(BackupImportError(row=row_num, message=str(exc)))

    write_audit_log(
        db,
        action="backup_import_transactions",
        target_type=TARGET_TYPE_BACKUP,
        actor_user_id=current_admin.id,
        target_id=target_user.id,
        meta_json={
            "success_rows": success_rows,
            "failed_rows": len(errors),
            "total_rows": len(rows),
        },
    )
    db.commit()

    return BackupImportResult(
        total_rows=len(rows),
        success_rows=success_rows,
        failed_rows=len(errors),
        errors=errors,
    )


@router.post("/import/transfers", response_model=BackupImportResult)
async def import_transfers(
    user_id: UUID = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target_user = _get_target_user_or_404(db, user_id)
    rows = await _read_csv_rows(file)

    errors: list[BackupImportError] = []
    success_rows = 0

    for row_num, row in enumerate(rows, start=2):
        try:
            transfer_date = _to_date(row.get("transfer_date"), "transfer_date")
            amount = _to_decimal(row.get("amount"), "amount")
            if amount <= 0:
                raise ValueError("amount must be greater than 0")

            from_account_name = _require_text(row.get("from_account_name"), "from_account_name")
            to_account_name = _require_text(row.get("to_account_name"), "to_account_name")
            note = _normalize_text(row.get("note"))

            from_account = _find_account_by_name(db, target_user.id, from_account_name)
            if not from_account:
                raise ValueError(f"from_account '{from_account_name}' not found")

            to_account = _find_account_by_name(db, target_user.id, to_account_name)
            if not to_account:
                raise ValueError(f"to_account '{to_account_name}' not found")

            if from_account.id == to_account.id:
                raise ValueError("from_account_name and to_account_name must be different")

            existing = db.execute(
                select(Transfer).where(
                    Transfer.user_id == target_user.id,
                    Transfer.transfer_date == transfer_date,
                    Transfer.amount == amount,
                    Transfer.from_account_id == from_account.id,
                    Transfer.to_account_id == to_account.id,
                    Transfer.note == note,
                )
            ).scalar_one_or_none()

            if existing:
                success_rows += 1
                continue

            db.add(
                Transfer(
                    user_id=target_user.id,
                    transfer_date=transfer_date,
                    amount=amount,
                    from_account_id=from_account.id,
                    to_account_id=to_account.id,
                    note=note,
                )
            )

            db.commit()
            success_rows += 1
        except Exception as exc:
            db.rollback()
            errors.append(BackupImportError(row=row_num, message=str(exc)))

    write_audit_log(
        db,
        action="backup_import_transfers",
        target_type=TARGET_TYPE_BACKUP,
        actor_user_id=current_admin.id,
        target_id=target_user.id,
        meta_json={
            "success_rows": success_rows,
            "failed_rows": len(errors),
            "total_rows": len(rows),
        },
    )
    db.commit()

    return BackupImportResult(
        total_rows=len(rows),
        success_rows=success_rows,
        failed_rows=len(errors),
        errors=errors,
    )