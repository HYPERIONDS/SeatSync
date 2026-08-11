from datetime import UTC, datetime, timedelta


def register_and_login(client, email="organizer@example.com", role="ORGANIZER"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123!",
            "full_name": "Venue Owner",
            "role": role,
        },
    )
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "StrongPass123!"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_organizer_generates_unique_venue_seats_and_rejects_overlap(client):
    headers = register_and_login(client)
    venue = client.post(
        "/api/v1/venues",
        headers=headers,
        json={
            "name": "Graduate Arena",
            "city": "Pune",
            "address": "1 Engineering Road",
            "sections": [
                {"name": "Floor", "rows": [{"label": "A", "seat_count": 3, "category": "VIP"}]}
            ],
        },
    )
    assert venue.status_code == 201
    seats = venue.json()["sections"][0]["seats"]
    assert [seat["identifier"] for seat in seats] == ["FLOOR-A-1", "FLOOR-A-2", "FLOOR-A-3"]

    event = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "Compiler Live",
            "description": "A sufficiently detailed event",
            "category": "TECH",
        },
    )
    assert event.status_code == 201
    starts = datetime.now(UTC) + timedelta(days=3)
    payload = {
        "venue_id": venue.json()["id"],
        "starts_at": starts.isoformat(),
        "ends_at": (starts + timedelta(hours=2)).isoformat(),
        "prices": [{"category": "VIP", "amount_minor": 250000}],
    }
    first_show = client.post(
        f"/api/v1/events/{event.json()['id']}/shows", headers=headers, json=payload
    )
    assert first_show.status_code == 201
    payload["starts_at"] = (starts + timedelta(hours=1)).isoformat()
    payload["ends_at"] = (starts + timedelta(hours=3)).isoformat()
    overlap = client.post(
        f"/api/v1/events/{event.json()['id']}/shows", headers=headers, json=payload
    )
    assert overlap.status_code == 409


def test_customer_cannot_create_venue(client):
    headers = register_and_login(client, "customer2@example.com", "CUSTOMER")
    response = client.post(
        "/api/v1/venues",
        headers=headers,
        json={
            "name": "Forbidden Venue",
            "city": "Pune",
            "address": "2 Engineering Road",
            "sections": [{"name": "Main", "rows": [{"label": "A", "seat_count": 1}]}],
        },
    )
    assert response.status_code == 403
