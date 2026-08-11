from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.database.session import get_db
from app.users.dependencies import require_roles
from app.users.models import User, UserRole

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def audit_history(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    events = db.scalars(
        select(AuditEvent)
        .order_by(desc(AuditEvent.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "actor_id": item.actor_id,
                "action": item.action,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "metadata": item.details,
                "timestamp": item.created_at,
            }
            for item in events
        ],
        "page": page,
        "page_size": page_size,
    }
