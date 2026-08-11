import smtplib
from uuid import UUID

from celery import Celery

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.notifications.service import deliver_notification

settings = get_settings()
celery_app = Celery(
    "seatsync", broker=settings.celery_broker_url, backend=settings.celery_result_backend
)
celery_app.conf.update(task_acks_late=True, task_reject_on_worker_lost=True)


@celery_app.task(
    bind=True,
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_notification(self, notification_id: str) -> bool:
    with SessionLocal() as db:
        return deliver_notification(db, UUID(notification_id))
