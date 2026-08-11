from datetime import UTC, datetime, timedelta
from uuid import UUID

import fakeredis

from app.main import app
from app.seat_holds.redis_client import get_redis
from app.shows.models import Show, ShowStatus
from tests.test_discovery import create_catalog
from tests.test_holds import customer_headers


def test_cancelled_and_past_shows_reject_holds(client, db):
    redis = fakeredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: redis
    venue, _, show_data = create_catalog(client, organizer_email="rules@example.com")
    headers = customer_headers(client, "rule-customer@example.com")
    request = {
        "show_id": show_data["id"],
        "seat_ids": [venue["sections"][0]["seats"][0]["id"]],
    }
    show = db.get(Show, UUID(show_data["id"]))
    show.status = ShowStatus.CANCELLED
    db.commit()
    assert client.post("/api/v1/holds", headers=headers, json=request).status_code == 409
    show.status = ShowStatus.SCHEDULED
    show.starts_at = datetime.now(UTC) - timedelta(hours=2)
    show.ends_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()
    assert client.post("/api/v1/holds", headers=headers, json=request).status_code == 409
