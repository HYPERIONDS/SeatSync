from datetime import UTC, datetime, timedelta

import fakeredis

from app.main import app
from app.seat_holds.redis_client import get_redis
from tests.test_catalog import register_and_login


def create_catalog(client, seat_count=2, organizer_email="discover@example.com"):
    headers = register_and_login(client, organizer_email)
    venue = client.post(
        "/api/v1/venues",
        headers=headers,
        json={
            "name": "Discovery Hall",
            "city": "Bengaluru",
            "address": "42 Query Lane",
            "sections": [{"name": "Main", "rows": [{"label": "A", "seat_count": seat_count}]}],
        },
    ).json()
    event = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "Distributed Ideas",
            "description": "A detailed technical conference",
            "category": "TECH",
        },
    ).json()
    starts = datetime.now(UTC) + timedelta(days=2)
    show = client.post(
        f"/api/v1/events/{event['id']}/shows",
        headers=headers,
        json={
            "venue_id": venue["id"],
            "starts_at": starts.isoformat(),
            "ends_at": (starts + timedelta(hours=2)).isoformat(),
            "prices": [{"category": "STANDARD", "amount_minor": 75000}],
        },
    ).json()
    return venue, event, show


def test_discovery_filters_and_seat_map_is_derived(client):
    redis = fakeredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: redis
    venue, event, show = create_catalog(client)
    discovered = client.get("/api/v1/events?city=Bengaluru&category=TECH&page=1&page_size=5")
    assert discovered.status_code == 200
    assert discovered.json()["total"] == 1
    assert discovered.json()["items"][0]["id"] == event["id"]

    seats = venue["sections"][0]["seats"]
    redis.set(f"seat:{show['id']}:{seats[0]['id']}", "hold-1", ex=300)
    seat_map = client.get(f"/api/v1/shows/{show['id']}/seats")
    assert seat_map.status_code == 200
    assert [item["state"] for item in seat_map.json()["seats"]] == ["HELD", "AVAILABLE"]
