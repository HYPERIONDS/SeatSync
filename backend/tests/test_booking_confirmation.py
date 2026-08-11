from uuid import UUID, uuid4

import fakeredis
import pytest
from sqlalchemy.exc import IntegrityError

from app.bookings.models import Booking, BookingSeat, BookingSeatStatus, BookingStatus
from app.events.models import Event
from app.main import app
from app.seat_holds.redis_client import get_redis
from app.seat_holds.service import hold_key, seat_key
from app.shows.models import Show
from app.users.models import User
from app.venues.models import Seat
from tests.test_discovery import create_catalog
from tests.test_holds import customer_headers


def booking_setup(client, db, redis, email="buyer@example.com", seat_count=2):
    app.dependency_overrides[get_redis] = lambda: redis
    venue, _, show = create_catalog(
        client, seat_count=seat_count, organizer_email=f"organizer-{email}"
    )
    headers = customer_headers(client, email)
    seats = venue["sections"][0]["seats"]
    hold = client.post(
        "/api/v1/holds",
        headers=headers,
        json={"show_id": show["id"], "seat_ids": [seat["id"] for seat in seats]},
    )
    assert hold.status_code == 201
    return venue, show, seats, headers, hold.json()


def confirm(client, headers, hold_id, key, outcome="SUCCESS"):
    return client.post(
        "/api/v1/bookings/confirm",
        headers={**headers, "Idempotency-Key": key},
        json={"hold_id": hold_id, "payment_outcome": outcome},
    )


def test_success_and_duplicate_idempotency_key_replay(client, db):
    redis = fakeredis.FakeRedis(decode_responses=True)
    _, _, _, headers, hold = booking_setup(client, db, redis)
    first = confirm(client, headers, hold["hold_id"], "checkout-unique-001")
    assert first.status_code == 201
    assert first.json()["booking"]["status"] == "CONFIRMED"
    replay = confirm(client, headers, hold["hold_id"], "checkout-unique-001")
    assert replay.status_code == 201
    assert replay.json()["replayed"] is True
    assert replay.json()["booking"]["id"] == first.json()["booking"]["id"]
    assert db.query(Booking).count() == 1


def test_other_user_hold_and_partial_conflict_are_rejected(client, db):
    redis = fakeredis.FakeRedis(decode_responses=True)
    _, show_data, seats, owner_headers, hold = booking_setup(client, db, redis, "owner@example.com")
    attacker_headers = customer_headers(client, "attacker@example.com")
    stolen = confirm(client, attacker_headers, hold["hold_id"], "attacker-key-001")
    assert stolen.status_code == 403

    show = db.get(Show, UUID(show_data["id"]))
    owner = db.query(User).filter(User.email == "owner@example.com").one()
    seat = db.get(Seat, UUID(seats[0]["id"]))
    existing = Booking(
        id=uuid4(),
        customer_id=owner.id,
        organizer_id=db.get(Event, show.event_id).organizer_id,
        show_id=show.id,
        status=BookingStatus.CONFIRMED,
        total_minor=75000,
        currency=show.currency,
        hold_id="stale-race",
    )
    existing.seats.append(
        BookingSeat(
            show_id=show.id,
            seat_id=seat.id,
            category=seat.category,
            price_minor=75000,
            status=BookingSeatStatus.CONFIRMED,
        )
    )
    db.add(existing)
    db.commit()
    conflict = confirm(client, owner_headers, hold["hold_id"], "partial-conflict-001")
    assert conflict.status_code == 409
    assert db.query(BookingSeat).filter(BookingSeat.seat_id == UUID(seats[1]["id"])).count() == 0
    duplicate = Booking(
        id=uuid4(),
        customer_id=owner.id,
        organizer_id=existing.organizer_id,
        show_id=show.id,
        status=BookingStatus.CONFIRMED,
        total_minor=75000,
        currency=show.currency,
        hold_id="database-guard",
    )
    duplicate.seats.append(
        BookingSeat(
            show_id=show.id,
            seat_id=seat.id,
            category=seat.category,
            price_minor=75000,
            status=BookingSeatStatus.CONFIRMED,
        )
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_failure_and_timeout_are_recorded_and_release_holds(client, db):
    redis = fakeredis.FakeRedis(decode_responses=True)
    for index, outcome in enumerate(["FAILURE", "TIMEOUT"]):
        _, show, seats, headers, hold = booking_setup(
            client, db, redis, f"failed{index}@example.com", seat_count=1
        )
        response = confirm(client, headers, hold["hold_id"], f"failed-payment-{index}", outcome)
        assert response.status_code == (402 if outcome == "FAILURE" else 504)
        assert response.json()["booking"]["status"] == "EXPIRED"
        assert redis.get(hold_key(hold["hold_id"])) is None
        assert redis.get(seat_key(show["id"], seats[0]["id"])) is None
