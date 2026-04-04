from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from uuid import UUID


class TransactionCreate(BaseModel):
    transaction_type: str
    transaction_date: date
    amount: Decimal
    category_id: UUID
    account_id: UUID
    note: str | None = None


class TransactionUpdate(BaseModel):
    transaction_type: str
    transaction_date: date
    amount: Decimal
    category_id: UUID
    account_id: UUID
    note: str | None = None


class TransactionResponse(BaseModel):
    id: UUID
    transaction_type: str
    transaction_date: date
    amount: Decimal
    category_id: UUID
    account_id: UUID
    note: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True