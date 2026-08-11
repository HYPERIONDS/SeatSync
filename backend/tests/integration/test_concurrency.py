import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from redis import Redis
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.bookings.models import BookingSeat, BookingSeatStatus
from app.bookings.schemas import BookingConfirm
from app.bookings.service import confirm_booking
from app.core.time import utcnow
from app.database.base import Base
from app.events.models import Event
from app.payments.models import PaymentOutcome
from app.seat_holds.schemas import HoldCreate
from app.seat_holds.service import create_hold, release_hold
from app.shows.models import Show, ShowPrice
from app.users.models import User, UserRole
from app.venues.models import Seat, SeatCategory, Venue, VenueSection

pytestmark = pytest.mark.integration
ATTEMPTS = 50


def infrastructure():
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://seatsync:seatsync@localhost:5433/seatsync_test",
    )
    redis_url = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15")
    engine = create_engine(database_url, pool_size=60, max_overflow=10)
    redis = Redis.from_url(redis_url, decode_responses=True)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        redis.ping()
    except Exception as exc:
        pytest.skip(f"PostgreSQL/Redis integration services unavailable: {exc}")
    Base.metadata.create_all(engine)
    redis.flushdb()
    return engine, sessionmaker(bind=engine, expire_on_commit=False), redis


def seed_contention(session_factory):
    suffix = uuid4().hex
    with session_factory() as db:
        organizer = User(
            email=f"race-organizer-{suffix}@example.com",
            password_hash="integration-only",  # noqa: S106
            full_name="Race Organizer",
            role=UserRole.ORGANIZER,
        )
        customers = [
            User(
                email=f"race-{index}-{suffix}@example.com",
                password_hash="integration-only",  # noqa: S106
                full_name=f"Racer {index}",
                role=UserRole.CUSTOMER,
            )
            for index in range(ATTEMPTS)
        ]
        db.add_all([organizer, *customers])
        db.flush()
        venue = Venue(
            organizer_id=organizer.id,
            name=f"Race Hall {suffix}",
            city="Test City",
            address="1 Contention Way",
        )
        section = VenueSection(name="Main", sort_order=0)
        venue.sections.append(section)
        db.add(venue)
        db.flush()
        seat = Seat(
            venue_id=venue.id,
            section_id=section.id,
            row_label="A",
            number=1,
            identifier="MAIN-A-1",
            category=SeatCategory.STANDARD,
        )
        event = Event(
            organizer_id=organizer.id,
            title=f"Race Event {suffix}",
            description="A real database contention integration test.",
            category="TEST",
        )
        db.add_all([seat, event])
        db.flush()
        show = Show(
            event_id=event.id,
            venue_id=venue.id,
            starts_at=utcnow() + timedelta(days=1),
            ends_at=utcnow() + timedelta(days=1, hours=2),
            currency="INR",
        )
        db.add(show)
        db.flush()
        db.add(ShowPrice(show_id=show.id, category=SeatCategory.STANDARD, amount_minor=10000))
        db.commit()
        return organizer.id, [customer.id for customer in customers], show.id, seat.id


def summarize(results):
    return {
        "successful": sum(value == "successful" for value in results),
        "rejected": sum(value == "rejected" for value in results),
        "failed": sum(value == "failed" for value in results),
    }


def test_fifty_customers_one_seat_report():
    engine, sessions, redis = infrastructure()
    _, customer_ids, show_id, seat_id = seed_contention(sessions)
    barrier = threading.Barrier(ATTEMPTS)

    def hold_worker(customer_id):
        with sessions() as db:
            customer = db.get(User, customer_id)
            barrier.wait()
            try:
                payload = create_hold(
                    db, redis, customer, HoldCreate(show_id=show_id, seat_ids=[seat_id])
                )
                return "successful", payload
            except HTTPException as exc:
                return ("rejected" if exc.status_code == 409 else "failed"), None
            except Exception:
                return "failed", None

    hold_results = []
    winning_hold = None
    with ThreadPoolExecutor(max_workers=ATTEMPTS) as pool:
        for future in as_completed([pool.submit(hold_worker, value) for value in customer_ids]):
            outcome, payload = future.result()
            hold_results.append(outcome)
            winning_hold = payload or winning_hold
    hold_summary = summarize(hold_results)
    assert hold_summary == {"successful": 1, "rejected": 49, "failed": 0}
    with sessions() as db:
        winner = db.get(User, customer_ids[0])
        actual_winner = db.scalar(select(User).where(User.id == UUID(winning_hold["customer_id"])))
        release_hold(redis, actual_winner or winner, winning_hold["hold_id"])

    # Simulate delayed/stale Redis state: every customer has a seemingly valid hold.
    hold_ids = {}
    for customer_id in customer_ids:
        hold_id = uuid4()
        hold_ids[customer_id] = hold_id
        redis.set(
            f"hold:{hold_id}",
            json.dumps(
                {
                    "hold_id": str(hold_id),
                    "customer_id": str(customer_id),
                    "show_id": str(show_id),
                    "seat_ids": [str(seat_id)],
                    "expires_at": (utcnow() + timedelta(minutes=5)).isoformat(),
                }
            ),
            ex=300,
        )
    barrier = threading.Barrier(ATTEMPTS)

    def booking_worker(customer_id):
        with sessions() as db:
            customer = db.get(User, customer_id)
            barrier.wait()
            try:
                code, _ = confirm_booking(
                    db,
                    redis,
                    customer,
                    BookingConfirm(
                        hold_id=hold_ids[customer_id], payment_outcome=PaymentOutcome.SUCCESS
                    ),
                    f"concurrency-{customer_id}",
                )
                return "successful" if code == 201 else "failed"
            except HTTPException as exc:
                return "rejected" if exc.status_code == 409 else "failed"
            except Exception:
                return "failed"

    with ThreadPoolExecutor(max_workers=ATTEMPTS) as pool:
        booking_results = list(pool.map(booking_worker, customer_ids))
    booking_summary = summarize(booking_results)
    with sessions() as db:
        confirmed_rows = db.scalar(
            select(func.count(BookingSeat.id)).where(
                BookingSeat.show_id == show_id,
                BookingSeat.seat_id == seat_id,
                BookingSeat.status == BookingSeatStatus.CONFIRMED,
            )
        )
    report = {
        "attempts": ATTEMPTS,
        "hold_race": hold_summary,
        "database_confirmation_race_with_stale_redis": booking_summary,
        "confirmed_booking_seat_rows": confirmed_rows,
        "result": "PASS" if booking_summary["successful"] == 1 and confirmed_rows == 1 else "FAIL",
    }
    report_path = Path(__file__).with_name("concurrency-report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    assert booking_summary == {"successful": 1, "rejected": 49, "failed": 0}
    assert confirmed_rows == 1
    engine.dispose()
