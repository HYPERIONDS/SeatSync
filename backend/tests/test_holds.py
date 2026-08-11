import time
from uuid import UUID

import fakeredis

from app.main import app
from app.seat_holds.redis_client import get_redis
from app.seat_holds.schemas import HoldCreate
from app.seat_holds.service import create_hold, read_hold, seat_key
from app.shows.models import Show
from app.users.models import User
from tests.test_catalog import register_and_login
from tests.test_discovery import create_catalog


def customer_headers(client, email):
    return register_and_login(client, email, "CUSTOMER")


def test_atomic_conflict_owner_release_and_expiration(client, db):
    redis = fakeredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: redis
    venue, _, show_data = create_catalog(client)
    first_headers = customer_headers(client, "holder1@example.com")
    second_headers = customer_headers(client, "holder2@example.com")
    seat_id = venue["sections"][0]["seats"][0]["id"]
    request = {"show_id": show_data["id"], "seat_ids": [seat_id]}

    first = client.post("/api/v1/holds", headers=first_headers, json=request)
    assert first.status_code == 201
    assert client.post("/api/v1/holds", headers=second_headers, json=request).status_code == 409
    assert (
        client.delete(
            f"/api/v1/holds/{first.json()['hold_id']}", headers=second_headers
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/holds/{first.json()['hold_id']}", headers=first_headers).status_code
        == 204
    )

    show = db.get(Show, UUID(show_data["id"]))
    customer = db.query(User).filter(User.email == "holder1@example.com").one()
    short = create_hold(db, redis, customer, HoldCreate(**request), ttl_seconds=1)
    assert read_hold(redis, short["hold_id"]) is not None
    time.sleep(1.05)
    assert read_hold(redis, short["hold_id"]) is None
    assert redis.get(seat_key(show.id, seat_id)) is None


def test_customer_cannot_exceed_five_active_seats(client):
    redis = fakeredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: redis
    venue, _, show = create_catalog(client, seat_count=6, organizer_email="six@example.com")
    headers = customer_headers(client, "five@example.com")
    seat_ids = [seat["id"] for seat in venue["sections"][0]["seats"]]
    first = client.post(
        "/api/v1/holds",
        headers=headers,
        json={"show_id": show["id"], "seat_ids": seat_ids[:5]},
    )
    assert first.status_code == 201
    duplicate = client.post(
        "/api/v1/holds",
        headers=headers,
        json={"show_id": show["id"], "seat_ids": [seat_ids[5]]},
    )
    assert duplicate.status_code == 409
    assert "at most five" in duplicate.json()["detail"]
