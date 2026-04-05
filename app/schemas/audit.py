from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: UUID
    actor_user_id: UUID | None = None
    action: str
    target_type: str
    target_id: UUID | None = None
    meta_json: dict | None = None
    created_at: datetime

    class Config:
        from_attributes = True