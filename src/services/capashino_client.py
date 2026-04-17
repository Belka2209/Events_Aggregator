"""Capashino notification service client."""

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from src.core.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class CapashinoNotificationResponse:
    """Capashino notification response."""

    id: str
    user_id: str
    message: str
    reference_id: str
    created_at: str
    idempotency_key: str | None = None


class CapashinoError(Exception):
    """Capashino API error."""

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize error."""
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class CapashinoClient:
    """Client for Capashino notification service."""

    def __init__(self) -> None:
        """Initialize client."""
        self._base_url = settings.capashino_base_url.rstrip("/")
        self._api_key = settings.capashino_api_key
        self._timeout = 30.0

    def _notifications_url(self) -> str:
        """Build notifications endpoint URL from base URL.

        Supports both variants:
        - CAPASHINO_BASE_URL=https://host
        - CAPASHINO_BASE_URL=https://host/api
        """
        if self._base_url.endswith("/api"):
            return f"{self._base_url}/notifications"
        return f"{self._base_url}/api/notifications"

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        """Extract readable error details from response body."""
        try:
            data = response.json()
            if isinstance(data, dict):
                return str(data.get("detail", data))
            return str(data)
        except ValueError:
            return response.text or "Unknown Capashino error"

    async def create_notification(
        self,
        message: str,
        reference_id: str,
        idempotency_key: str | None = None,
    ) -> CapashinoNotificationResponse:
        """Create a notification.

        Args:
            message: Notification message text.
            reference_id: Reference ID (e.g., ticket_id).
            idempotency_key: Optional idempotency key.

        Returns:
            Notification response.

        Raises:
            CapashinoError: If the API returns an error.
        """
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self._api_key,
        }

        payload: dict[str, Any] = {
            "message": message,
            "reference_id": reference_id,
        }

        # Capashino contract uses idempotency key for deduplication,
        # so we always send one even if caller omitted it.
        payload["idempotency_key"] = idempotency_key or f"capashino-{reference_id}"

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
            ) as client:
                response = await client.post(
                    self._notifications_url(),
                    json=payload,
                    headers=headers,
                )
        except httpx.RequestError as e:
            logger.error("Failed to connect to Capashino: %s", e)
            raise CapashinoError("Failed to connect to Capashino") from e

        if response.status_code == 201:
            data = response.json()
            return CapashinoNotificationResponse(
                id=data["id"],
                user_id=data["user_id"],
                message=data["message"],
                reference_id=data["reference_id"],
                created_at=data["created_at"],
                idempotency_key=data.get("idempotency_key"),
            )

        if response.status_code == 400:
            raise CapashinoError(self._extract_error_detail(response), 400)
        if response.status_code == 401:
            raise CapashinoError(self._extract_error_detail(response), 401)
        if response.status_code == 409:
            data = response.json()
            return CapashinoNotificationResponse(
                id=data.get("id", ""),
                user_id=data.get("user_id", ""),
                message=data.get("message", ""),
                reference_id=data.get("reference_id", ""),
                created_at=data.get("created_at", ""),
                idempotency_key=data.get("idempotency_key"),
            )
        if response.status_code == 422:
            raise CapashinoError(self._extract_error_detail(response), 422)
        if response.status_code >= 500:
            raise CapashinoError(
                self._extract_error_detail(response),
                response.status_code,
            )

        raise CapashinoError(
            f"Unexpected error: {response.status_code}", response.status_code
        )


capashino_client = CapashinoClient()
