from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MeResponse(BaseModel):
    id: UUID
    email: str | None = None
    username: str | None = None
    full_name: str
    role: str
    auth_provider: str
    is_active: bool
    last_login_at: datetime | None = None

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    id: UUID
    email: str | None = None
    username: str | None = None
    full_name: str
    role: str
    auth_provider: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None

    class Config:
        from_attributes = True


class AdminUserUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150)
    is_active: bool


class AdminUserStatusUpdateRequest(BaseModel):
    is_active: bool