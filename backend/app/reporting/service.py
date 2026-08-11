import csv
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from redis import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.bookings.models import Booking, BookingSeat, BookingSeatStatus, BookingStatus
from app.core.config import get_settings
from app.core.time import utcnow
from app.events.models import Event
from app.payments.models import PaymentAttempt, PaymentStatus, Refund
from app.reporting.models import AttendeeExport, ExportStatus
from app.shows.models import Show, ShowStatus
from app.users.models import User, UserRole
from app.venues.models import Seat


def dashboard(db: Session, redis: Redis, organizer: User) -> dict:
    owner_filter = True if organizer.role is UserRole.ADMIN else Event.organizer_id == organizer.id
    event_ids = select(Event.id).where(owner_filter)
    events = db.scalar(select(func.count(Event.id)).where(owner_filter)) or 0
    upcoming = db.scalars(
        select(Show).where(
            Show.event_id.in_(event_ids),
            Show.status == ShowStatus.SCHEDULED,
            Show.starts_at > utcnow(),
        )
    ).all()
    show_ids = [show.id for show in upcoming]
    confirmed = (
        db.scalar(
            select(func.count(Booking.id)).where(
                Booking.organizer_id == organizer.id,
                Booking.status == BookingStatus.CONFIRMED,
            )
        )
        if organizer.role is not UserRole.ADMIN
        else db.scalar(
            select(func.count(Booking.id)).where(Booking.status == BookingStatus.CONFIRMED)
        )
    ) or 0
    gross_query = (
        select(func.coalesce(func.sum(PaymentAttempt.amount_minor), 0))
        .join(Booking, Booking.id == PaymentAttempt.booking_id)
        .where(PaymentAttempt.status == PaymentStatus.SUCCEEDED)
    )
    refund_query = select(func.coalesce(func.sum(Refund.amount_minor), 0)).join(
        Booking, Booking.id == Refund.booking_id
    )
    if organizer.role is not UserRole.ADMIN:
        gross_query = gross_query.where(Booking.organizer_id == organizer.id)
        refund_query = refund_query.where(Booking.organizer_id == organizer.id)
    gross = db.scalar(gross_query) or 0
    refunds = db.scalar(refund_query) or 0
    available = 0
    for show in upcoming:
        seat_ids = list(db.scalars(select(Seat.id).where(Seat.venue_id == show.venue_id)).all())
        booked_ids = set(
            db.scalars(
                select(BookingSeat.seat_id).where(
                    BookingSeat.show_id == show.id,
                    BookingSeat.status == BookingSeatStatus.CONFIRMED,
                )
            ).all()
        )
        hold_values = redis.mget([f"seat:{show.id}:{seat_id}" for seat_id in seat_ids])
        held_ids = {
            seat_id
            for seat_id, hold_id in zip(seat_ids, hold_values, strict=True)
            if hold_id and seat_id not in booked_ids
        }
        available += len(seat_ids) - len(booked_ids) - len(held_ids)
    return {
        "events": events,
        "upcoming_shows": len(show_ids),
        "available_seats": available,
        "confirmed_bookings": confirmed,
        "gross_revenue_minor": gross,
        "simulated_refunds_minor": refunds,
        "net_revenue_minor": gross - refunds,
        "currency_note": "Values are simulated payment totals in each show's minor units.",
    }


def assert_show_owner(db: Session, organizer: User, show_id: UUID) -> Show:
    show = db.get(Show, show_id)
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")
    event = db.get(Event, show.event_id)
    if organizer.role is not UserRole.ADMIN and event.organizer_id != organizer.id:
        raise HTTPException(status_code=403, detail="Show belongs to another organizer")
    return show


def generate_attendee_csv(db: Session, export_id: UUID) -> Path:
    job = db.get(AttendeeExport, export_id)
    if job is None:
        raise ValueError("Export job not found")
    export_dir = get_settings().export_directory.resolve()
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"attendees-{job.id}.csv"
    rows = db.execute(
        select(User.full_name, User.email, Booking.id, Seat.identifier)
        .join(Booking, Booking.customer_id == User.id)
        .join(BookingSeat, BookingSeat.booking_id == Booking.id)
        .join(Seat, Seat.id == BookingSeat.seat_id)
        .where(
            Booking.show_id == job.show_id,
            Booking.organizer_id == job.organizer_id,
            Booking.status == BookingStatus.CONFIRMED,
            BookingSeat.status == BookingSeatStatus.CONFIRMED,
        )
        .order_by(User.full_name, Seat.identifier)
    ).all()
    grouped: dict[tuple[str, str, UUID], list[str]] = {}
    for full_name, email, booking_id, identifier in rows:
        grouped.setdefault((full_name, email, booking_id), []).append(identifier)
    try:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["booking_id", "attendee_name", "email", "seats"])
            for (name, email, booking_id), identifiers in grouped.items():
                writer.writerow([booking_id, name, email, ", ".join(identifiers)])
    except OSError:
        job.status = ExportStatus.FAILED
        db.commit()
        raise
    job.status = ExportStatus.COMPLETED
    job.file_path = str(path)
    job.completed_at = utcnow()
    db.commit()
    return path
