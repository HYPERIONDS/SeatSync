from datetime import timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from redis import Redis
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.audit.service import record_audit
from app.bookings.models import (
    Booking,
    BookingSeat,
    BookingSeatStatus,
    BookingStatus,
    IdempotencyRecord,
)
from app.bookings.schemas import BookingConfirm
from app.core.config import get_settings
from app.core.time import as_utc, utcnow
from app.events.models import Event
from app.notifications.service import create_notification, dispatch_notification
from app.payments.models import PaymentAttempt, PaymentOutcome, PaymentStatus, Refund
from app.payments.service import simulate_payment
from app.seat_holds.service import read_hold, release_hold
from app.shows.models import Show, ShowPrice, ShowStatus
from app.users.models import User, UserRole
from app.venues.models import Seat


def _booking_json(booking: Booking, payment_status: PaymentStatus, message: str) -> dict:
    return {
        "booking": {
            "id": str(booking.id),
            "show_id": str(booking.show_id),
            "status": booking.status.value,
            "total_minor": booking.total_minor,
            "currency": booking.currency,
            "created_at": booking.created_at.isoformat(),
            "confirmed_at": booking.confirmed_at.isoformat() if booking.confirmed_at else None,
            "cancelled_at": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
            "seats": [
                {
                    "seat_id": str(item.seat_id),
                    "category": item.category.value,
                    "price_minor": item.price_minor,
                    "status": item.status.value,
                }
                for item in booking.seats
            ],
        },
        "payment_status": payment_status.value,
        "replayed": False,
        "message": message,
    }


def _load_booking(db: Session, booking_id: UUID) -> Booking:
    return db.scalar(
        select(Booking).where(Booking.id == booking_id).options(selectinload(Booking.seats))
    )


def confirm_booking(
    db: Session,
    redis: Redis,
    customer: User,
    data: BookingConfirm,
    idempotency_key: str,
) -> tuple[int, dict]:
    if not 8 <= len(idempotency_key) <= 120:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be 8-120 characters")
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        lock_value = f"{customer.id}:{idempotency_key}"
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:value))"), {"value": lock_value})
    existing = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == customer.id,
            IdempotencyRecord.key == idempotency_key,
        )
    )
    if existing:
        response = dict(existing.response_json)
        response["replayed"] = True
        return existing.status_code, response

    payload = read_hold(redis, data.hold_id)
    if payload is None:
        raise HTTPException(status_code=409, detail="Hold has expired")
    if payload["customer_id"] != str(customer.id):
        raise HTTPException(status_code=403, detail="This hold belongs to another customer")
    show = db.get(Show, UUID(payload["show_id"]))
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")
    if show.status != ShowStatus.SCHEDULED or as_utc(show.starts_at) <= utcnow():
        raise HTTPException(status_code=409, detail="Past or cancelled shows cannot be booked")

    seat_ids = [UUID(value) for value in payload["seat_ids"]]
    seats = db.scalars(
        select(Seat).where(Seat.id.in_(seat_ids), Seat.venue_id == show.venue_id).with_for_update()
    ).all()
    if len(seats) != len(seat_ids):
        raise HTTPException(status_code=409, detail="Hold contains invalid seats")
    conflict = db.scalar(
        select(BookingSeat.id).where(
            BookingSeat.show_id == show.id,
            BookingSeat.seat_id.in_(seat_ids),
            BookingSeat.status == BookingSeatStatus.CONFIRMED,
        )
    )
    if conflict:
        raise HTTPException(status_code=409, detail="One or more seats were already booked")
    prices = {
        price.category: price.amount_minor
        for price in db.scalars(select(ShowPrice).where(ShowPrice.show_id == show.id))
    }
    if any(seat.category not in prices for seat in seats):
        raise HTTPException(status_code=409, detail="A selected seat has no configured price")
    total = sum(prices[seat.category] for seat in seats)
    event = db.get(Event, show.event_id)
    booking = Booking(
        id=uuid4(),
        customer_id=customer.id,
        organizer_id=event.organizer_id,
        show_id=show.id,
        status=BookingStatus.PENDING,
        total_minor=total,
        currency=show.currency,
        hold_id=str(data.hold_id),
    )
    db.add(booking)
    payment_status = simulate_payment(data.payment_outcome)
    db.add(
        PaymentAttempt(
            booking_id=booking.id,
            requested_outcome=data.payment_outcome,
            status=payment_status,
            amount_minor=total,
            currency=show.currency,
        )
    )
    if payment_status == PaymentStatus.SUCCEEDED:
        booking.status = BookingStatus.CONFIRMED
        booking.confirmed_at = utcnow()
        for seat in seats:
            booking.seats.append(
                BookingSeat(
                    show_id=show.id,
                    seat_id=seat.id,
                    category=seat.category,
                    price_minor=prices[seat.category],
                    status=BookingSeatStatus.CONFIRMED,
                )
            )
        status_code = 201
        message = "Booking confirmed. Payment was simulated; no real money was processed."
    else:
        booking.status = BookingStatus.EXPIRED
        status_code = 402 if data.payment_outcome == PaymentOutcome.FAILURE else 504
        message = (
            "Simulated payment failed; seats were released."
            if data.payment_outcome == PaymentOutcome.FAILURE
            else "Simulated payment timed out; seats were released."
        )
    notification_id = None
    if booking.status == BookingStatus.CONFIRMED:
        record_audit(
            db,
            customer.id,
            "BOOKING_CONFIRMED",
            "Booking",
            str(booking.id),
            {"show_id": str(show.id), "seat_count": len(seats), "total_minor": total},
        )
        notification = create_notification(
            db,
            booking.id,
            customer.email,
            "BOOKING_CONFIRMATION",
            "Your SeatSync booking is confirmed",
            f"Booking {booking.id} is confirmed. Payment was simulated; "
            "no real money was processed.",
        )
        notification_id = notification.id
    try:
        db.flush()
        booking = _load_booking(db, booking.id)
        response = _booking_json(booking, payment_status, message)
        db.add(
            IdempotencyRecord(
                user_id=customer.id,
                key=idempotency_key,
                endpoint="bookings.confirm",
                status_code=status_code,
                response_json=response,
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Seat conflict: the database prevented a duplicate confirmed booking",
        ) from exc
    try:
        release_hold(redis, customer, data.hold_id)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
    if notification_id:
        dispatch_notification(notification_id)
    return status_code, response


def list_customer_bookings(db: Session, customer: User) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking)
            .where(Booking.customer_id == customer.id)
            .options(selectinload(Booking.seats))
            .order_by(Booking.created_at.desc())
        ).all()
    )


def cancel_booking(db: Session, actor: User, booking_id: UUID) -> Booking:
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.seats))
        .with_for_update()
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if actor.role is not UserRole.ADMIN and booking.customer_id != actor.id:
        raise HTTPException(status_code=403, detail="Booking belongs to another customer")
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Only confirmed bookings can be cancelled")
    show = db.get(Show, booking.show_id)
    cutoff = utcnow() + timedelta(hours=get_settings().cancellation_cutoff_hours)
    if as_utc(show.starts_at) <= cutoff:
        raise HTTPException(status_code=409, detail="Cancellation window has closed")
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = utcnow()
    for item in booking.seats:
        item.status = BookingSeatStatus.CANCELLED
    db.add(
        Refund(
            booking_id=booking.id,
            amount_minor=booking.total_minor,
            currency=booking.currency,
            status="SIMULATED",
        )
    )
    record_audit(
        db,
        actor.id,
        "BOOKING_CANCELLED",
        "Booking",
        str(booking.id),
        {"show_id": str(booking.show_id), "refund_minor": booking.total_minor},
    )
    customer = db.get(User, booking.customer_id)
    notification = create_notification(
        db,
        booking.id,
        customer.email,
        "BOOKING_CANCELLATION",
        "Your SeatSync booking was cancelled",
        f"Booking {booking.id} was cancelled. A simulated refund was recorded; "
        "no real money moved.",
    )
    db.commit()
    dispatch_notification(notification.id)
    return booking
