from uuid import UUID

from app.database.session import SessionLocal
from app.notifications.tasks import celery_app
from app.reporting.service import generate_attendee_csv


@celery_app.task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def generate_attendee_export(export_id: str) -> str:
    with SessionLocal() as db:
        return str(generate_attendee_csv(db, UUID(export_id)))
