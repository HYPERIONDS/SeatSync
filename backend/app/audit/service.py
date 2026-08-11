from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.models import AuditEvent


def record_audit(
    db: Session,
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
    )
    db.add(event)
    return event
