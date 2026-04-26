"""Load testing for parking payment APIs.

Run with: locust -f tests/load/locustfile.py --host http://localhost:8000
"""

from locust import HttpUser, between, task


class ParkingApiUser(HttpUser):
    """Simulates POS operator performing common actions."""

    wait_time = between(1, 3)

    def on_start(self):
        """Login and obtain session cookie."""
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        if response.status_code != 200:
            self.environment.runner.quit()

    @task(5)
    def health_check(self):
        self.client.get("/api/health")

    @task(3)
    def list_transactions(self):
        self.client.get("/api/transactions?limit=20")

    @task(2)
    def get_settings(self):
        self.client.get("/api/settings")

    @task(1)
    def list_settlements(self):
        self.client.get("/api/settlements?limit=10")
