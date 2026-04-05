from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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

class AdminUserStatusUpdateRequest(BaseModel):
    is_active: bool