from uuid import UUID

import fakeredis
import pytest

from app.audit.models import AuditEvent
from app.core.config import get_settings
from app.notifications.models import Notification, NotificationStatus
from app.notifications.service import deliver_notification
from app.payments.models import Refund
from app.reporting.models import AttendeeExport
from app.reporting.service import generate_attendee_csv
from tests.test_booking_confirmation import booking_setup, confirm
from tests.test_catalog import register_and_login


def test_cancel_records_refund_audit_notification_and_releases_seat(client, db):
    redis = fakeredis.FakeRedis(decode_responses=True)
    _, show, seats, headers, hold = booking_setup(client, db, redis, "cancel@example.com", 1)
    booked = confirm(client, headers, hold["hold_id"], "cancel-booking-001")
    booking_id = booked.json()["booking"]["id"]
    cancelled = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert db.query(Refund).filter(Refund.booking_id == UUID(booking_id)).count() == 1
    assert db.query(AuditEvent).filter(AuditEvent.action == "BOOKING_CANCELLED").count() == 1
    assert db.query(Notification).filter(Notification.kind == "BOOKING_CANCELLATION").count() == 1
    seat_map = client.get(f"/api/v1/shows/{show['id']}/seats").json()
    assert seat_map["seats"][0]["id"] == seats[0]["id"]
    assert seat_map["seats"][0]["state"] == "AVAILABLE"


def test_notification_retry_is_idempotent(client, db):
    redis = fakeredis.FakeRedis(decode_responses=True)
    _, _, _, headers, hold = booking_setup(client, db, redis, "notify@example.com", 1)
    confirm(client, headers, hold["hold_id"], "notification-001")
    notification = db.query(Notification).filter(Notification.kind == "BOOKING_CONFIRMATION").one()
    calls = []

    class SMTP:
        failures = 1

        def __init__(self, *_):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def send_message(self, message):
            calls.append(message["Message-ID"])
            if SMTP.failures:
                SMTP.failures -= 1
                raise OSError("temporary mail failure")

    with pytest.raises(OSError):
        deliver_notification(db, notification.id, SMTP)
    assert deliver_notification(db, notification.id, SMTP) is True
    assert deliver_notification(db, notification.id, SMTP) is False
    db.refresh(notification)
    assert notification.status == NotificationStatus.SENT
    assert notification.attempts == 2
    assert len(calls) == 2


def test_organizer_reporting_is_scoped_and_csv_is_generated(client, db, tmp_path, monkeypatch):
    redis = fakeredis.FakeRedis(decode_responses=True)
    _, show, _, customer_headers, hold = booking_setup(client, db, redis, "attendee@example.com", 1)
    confirm(client, customer_headers, hold["hold_id"], "attendee-booking-001")
    organizer_headers = register_and_login(client, "organizer-attendee@example.com")
    dashboard = client.get("/api/v1/organizer/dashboard", headers=organizer_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["confirmed_bookings"] == 1
    queued = client.post(
        f"/api/v1/organizer/shows/{show['id']}/attendees/export", headers=organizer_headers
    )
    assert queued.status_code == 202
    job = db.get(AttendeeExport, UUID(queued.json()["export_id"]))
    monkeypatch.setattr(get_settings(), "export_directory", tmp_path)
    path = generate_attendee_csv(db, job.id)
    content = path.read_text(encoding="utf-8")
    assert "attendee@example.com" in content
    assert "booking_id,attendee_name,email,seats" in content


def test_unrelated_organizer_cannot_export_attendees(client, db):
    redis = fakeredis.FakeRedis(decode_responses=True)
    _, show, _, _, _ = booking_setup(client, db, redis, "private@example.com", 1)
    stranger = register_and_login(client, "stranger-organizer@example.com")
    response = client.post(
        f"/api/v1/organizer/shows/{show['id']}/attendees/export", headers=stranger
    )
    assert response.status_code == 403
