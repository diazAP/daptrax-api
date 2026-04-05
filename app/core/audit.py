from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    action: str,
    target_type: str,
    actor_user_id: UUID | None = None,
    target_id: UUID | None = None,
    meta_json: dict[str, Any] | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        meta_json=meta_json,
    )
    db.add(log)
    return log