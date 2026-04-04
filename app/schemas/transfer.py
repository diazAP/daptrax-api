from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from uuid import UUID


class TransferCreate(BaseModel):
    transfer_date: date
    amount: Decimal
    from_account_id: UUID
    to_account_id: UUID
    note: str | None = None


class TransferUpdate(BaseModel):
    transfer_date: date
    amount: Decimal
    from_account_id: UUID
    to_account_id: UUID
    note: str | None = None


class TransferResponse(BaseModel):
    id: UUID
    transfer_date: date
    amount: Decimal
    from_account_id: UUID
    to_account_id: UUID
    note: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True