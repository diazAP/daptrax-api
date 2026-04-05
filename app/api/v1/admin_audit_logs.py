from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/admin/audit-logs", tags=["admin-audit-logs"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = (
        select(AuditLog)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()