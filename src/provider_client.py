import time
import urllib.parse

import httpx

from src.config import EVENTS_PROVIDER_API_KEY, EVENTS_PROVIDER_URL
from src.metrics import (
    events_provider_request_duration_seconds,
    events_provider_requests_total,
)


class EventsProviderClient:
    def __init__(
        self,
        base_url: str = EVENTS_PROVIDER_URL,
        api_key: str = EVENTS_PROVIDER_API_KEY,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key

    async def get_events(self, changed_at: str, cursor: str | None = None) -> dict:
        if cursor:
            url = cursor
            params = None
        else:
            url = urllib.parse.urljoin(self.base_url, "api/events/")
            params = {"changed_at": changed_at}

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url, params=params, headers={"x-api-key": self.api_key}
            )
        duration = time.monotonic() - start
        events_provider_requests_total.labels(
            endpoint="/events", status=response.status_code
        ).inc()
        events_provider_request_duration_seconds.labels(endpoint="/events").observe(
            duration
        )
        response.raise_for_status()
        return response.json()

    async def get_seats(self, event_id: str) -> list[str]:
        url = urllib.parse.urljoin(self.base_url, f"api/events/{event_id}/seats/")

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers={"x-api-key": self.api_key})
        duration = time.monotonic() - start
        events_provider_requests_total.labels(
            endpoint="/seats", status=response.status_code
        ).inc()
        events_provider_request_duration_seconds.labels(endpoint="/seats").observe(
            duration
        )
        if response.status_code == 500:
            raise ValueError("Event not published")
        response.raise_for_status()
        return response.json()["seats"]

    async def register(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> str:
        url = urllib.parse.urljoin(self.base_url, f"api/events/{event_id}/register/")

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "seat": seat,
                },
                headers={"x-api-key": self.api_key},
            )
        duration = time.monotonic() - start
        events_provider_requests_total.labels(
            endpoint="/registration", status=response.status_code
        ).inc()
        events_provider_request_duration_seconds.labels(
            endpoint="/registration"
        ).observe(duration)
        response.raise_for_status()
        return response.json()["ticket_id"]

    async def unregister(self, event_id: str, ticket_id: str) -> bool:
        url = urllib.parse.urljoin(self.base_url, f"api/events/{event_id}/unregister/")

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method="DELETE",
                url=url,
                json={"ticket_id": ticket_id},
                headers={"x-api-key": self.api_key},
            )
        duration = time.monotonic() - start
        events_provider_requests_total.labels(
            endpoint="/registration", status=response.status_code
        ).inc()
        events_provider_request_duration_seconds.labels(
            endpoint="/registration"
        ).observe(duration)
        response.raise_for_status()
        return response.json()["success"]
