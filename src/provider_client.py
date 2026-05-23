import os

import httpx

API_KEY = os.getenv("EVENTS_PROVIDER_API_KEY", "")
BASE_URL = os.getenv(
    "EVENTS_PROVIDER_URL",
    "http://student-system-events-provider-web.student-system-events-provider.svc:8000",
)


class EventsProviderClient:
    def __init__(self, base_url: str = BASE_URL, api_key: str = API_KEY):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def get_events(self, changed_at: str, cursor: str | None = None) -> dict:
        if cursor:
            url = cursor
            params = None
        else:
            url = f"{self.base_url}/api/events/"
            params = {"changed_at": changed_at}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url, params=params, headers={"x-api-key": self.api_key}
            )
            response.raise_for_status()
            return response.json()

    async def get_seats(self, event_id: str) -> list[str]:
        url = f"{self.base_url}/api/events/{event_id}/seats/"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers={"x-api-key": self.api_key})
            if response.status_code == 500:
                raise ValueError("Event not published")
            response.raise_for_status()
            return response.json()["seats"]

    async def register(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> str:
        url = f"{self.base_url}/api/events/{event_id}/register/"

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
            response.raise_for_status()
            return response.json()["ticket_id"]

    async def unregister(self, event_id: str, ticket_id: str) -> bool:
        url = f"{self.base_url}/api/events/{event_id}/unregister/"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                url, json={"ticket_id": ticket_id}, headers={"x-api-key": self.api_key}
            )
            response.raise_for_status()
            return response.json()["success"]
