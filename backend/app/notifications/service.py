import smtplib
from email.message import EmailMessage
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utcnow
from app.notifications.models import Notification, NotificationStatus


def create_notification(
    db: Session,
    booking_id: UUID,
    recipient: str,
    kind: str,
    subject: str,
    body: str,
) -> Notification:
    notification = Notification(
        id=uuid4(),
        booking_id=booking_id,
        recipient=recipient,
        kind=kind,
        subject=subject,
        body=body,
        deduplication_key=f"{booking_id}:{kind}",
        status=NotificationStatus.PENDING,
    )
    db.add(notification)
    return notification


def deliver_notification(db: Session, notification_id: UUID, smtp_factory=smtplib.SMTP) -> bool:
    notification = db.get(Notification, notification_id, with_for_update=True)
    if notification is None:
        return False
    if notification.sent_at is not None or notification.status == NotificationStatus.SENT:
        return False
    notification.attempts += 1
    message = EmailMessage()
    message["From"] = get_settings().email_from
    message["To"] = notification.recipient
    message["Subject"] = notification.subject
    message["Message-ID"] = f"<{notification.deduplication_key}@seatsync.local>"
    message.set_content(notification.body)
    try:
        with smtp_factory(get_settings().smtp_host, get_settings().smtp_port) as smtp:
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        notification.status = NotificationStatus.FAILED
        db.commit()
        raise
    notification.status = NotificationStatus.SENT
    notification.sent_at = utcnow()
    db.commit()
    return True


def dispatch_notification(notification_id: UUID) -> None:
    if get_settings().app_env == "testing":
        return
    from app.notifications.tasks import send_notification

    send_notification.delay(str(notification_id))
