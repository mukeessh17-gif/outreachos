"""Locust workload for a local fake-data API test."""

import os

from locust import HttpUser, between, task


class OutreachUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self) -> None:
        token = os.getenv("LOADTEST_TOKEN")
        if not token:
            raise RuntimeError("Set LOADTEST_TOKEN from a local fake test account.")
        self.client.headers["Authorization"] = f"Bearer {token}"

    @task(5)
    def list_leads(self) -> None:
        self.client.get("/leads?limit=100", name="/leads")

    @task(3)
    def dashboard(self) -> None:
        self.client.get("/analytics/dashboard")

    @task(2)
    def pipeline(self) -> None:
        self.client.get("/pipeline")
