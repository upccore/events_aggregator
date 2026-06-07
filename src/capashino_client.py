import urllib.parse

import httpx

from src.config import CAPASHINO_API_KEY, CAPASHINO_URL


class CapashinoClient:
    def __init__(
        self,
        base_url: str = CAPASHINO_URL,
        api_key: str = CAPASHINO_API_KEY,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key

    async def send_notification(
        self,
        message: str,
        reference_id: str,
        idempotency_key: str,
    ) -> dict:
        url = urllib.parse.urljoin(self.base_url, "api/notifications")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json={
                    "message": message,
                    "reference_id": reference_id,
                    "idempotency_key": idempotency_key,
                },
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                },
            )
            response.raise_for_status()
            return response.json()
