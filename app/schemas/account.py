from decimal import Decimal
from pydantic import BaseModel, Field
from uuid import UUID


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    initial_balance: Decimal = 0
    color_key: str | None = None
    icon_key: str | None = None
    sort_order: int = 0


class AccountUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    initial_balance: Decimal = 0
    color_key: str | None = None
    icon_key: str | None = None
    sort_order: int = 0


class AccountResponse(BaseModel):
    id: UUID
    name: str
    initial_balance: Decimal
    color_key: str | None = None
    icon_key: str | None = None
    sort_order: int

    class Config:
        from_attributes = True