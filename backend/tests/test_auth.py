def test_register_login_profile_and_refresh_rotation(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "graduate@example.com",
            "password": "StrongPass123!",
            "full_name": "Recent Graduate",
            "role": "CUSTOMER",
        },
    )
    assert registered.status_code == 201
    assert "password" not in registered.text

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "graduate@example.com", "password": "StrongPass123!"},
    )
    assert login.status_code == 200
    tokens = login.json()
    profile = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert profile.status_code == 200
    assert profile.json()["role"] == "CUSTOMER"

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401


def test_duplicate_email_and_admin_self_registration_are_rejected(client):
    payload = {
        "email": "same@example.com",
        "password": "StrongPass123!",
        "full_name": "First User",
        "role": "CUSTOMER",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409
    payload["email"] = "admin@example.com"
    payload["role"] = "ADMIN"
    assert client.post("/api/v1/auth/register", json=payload).status_code == 422
