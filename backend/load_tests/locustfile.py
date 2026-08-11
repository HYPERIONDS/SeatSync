import os
import uuid

from locust import HttpUser, between, task


class SeatContentionUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self):
        suffix = uuid.uuid4().hex
        self.email = f"locust-{suffix}@example.com"
        password = "LoadTest123!"
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.email,
                "password": password,
                "full_name": "Locust Customer",
                "role": "CUSTOMER",
            },
        )
        login = self.client.post(
            "/api/v1/auth/login", json={"email": self.email, "password": password}
        )
        self.headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        self.show_id = os.environ["LOCUST_SHOW_ID"]
        self.seat_id = os.environ["LOCUST_SEAT_ID"]

    @task
    def contend_for_same_seat(self):
        with self.client.post(
            "/api/v1/holds",
            headers=self.headers,
            json={"show_id": self.show_id, "seat_ids": [self.seat_id]},
            name="POST /holds (same seat)",
            catch_response=True,
        ) as response:
            if response.status_code in (201, 409):
                response.success()
            else:
                response.failure(f"Unexpected status {response.status_code}")
