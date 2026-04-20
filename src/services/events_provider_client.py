"""Events Provider API client."""

import logging
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from src.core.settings import settings
from src.models.enums import EventStatus

logger = logging.getLogger(__name__)


def _build_provider_url(base_url: str, path: str) -> str:
    """Build provider API URL using urljoin."""
    return urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))


def _extract_error_detail(response: httpx.Response) -> str:
    """Extract human-readable error details from provider response."""
    try:
        data = response.json()
        if isinstance(data, dict):
            return str(data.get("detail", data))
        return str(data)
    except Exception:
        return response.text or "Unknown provider error"


class ProviderError(Exception):
    """Exception raised for provider API errors."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Provider error {status_code}: {detail}")


@dataclass
class PlaceData:
    """Place data from Events Provider API."""

    id: str
    name: str
    city: str
    address: str
    seats_pattern: str | None
    changed_at: str | None
    created_at: str | None


@dataclass
class EventData:
    """Event data from Events Provider API."""

    id: str
    name: str
    place: PlaceData
    event_time: str
    registration_deadline: str | None
    status: EventStatus
    number_of_visitors: int
    changed_at: str
    created_at: str
    status_changed_at: str | None


@dataclass
class SeatsData:
    """Seats data from Events Provider API."""

    seats: list[str]


@dataclass
class RegistrationData:
    """Registration data from Events Provider API."""

    ticket_id: str


@dataclass
class UnregisterData:
    """Unregister data from Events Provider API."""

    success: bool


class EventsProviderClient:
    """Client for Events Provider API."""

    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        """Initialize the client.

        Args:
            api_key: API key for authentication. If None, uses settings.
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key or settings.events_provider_api_key
        self._base_url = settings.events_provider_base_url
        self._timeout = timeout

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {"x-api-key": self._api_key, "Content-Type": "application/json"}

    def _raise_provider_error(self, response: httpx.Response) -> None:
        """Raise ProviderError for non-success responses."""
        if response.is_error:
            raise ProviderError(
                status_code=response.status_code,
                detail=_extract_error_detail(response),
            )

    async def events(
        self, changed_at: str, cursor: str | None = None
    ) -> tuple[list[EventData], str | None]:
        """Get events from Events Provider API.

        Args:
            changed_at: Date filter in YYYY-MM-DD format.
            cursor: Pagination cursor for next page.

        Returns:
            Tuple of (list of events, next cursor or None).
        """
        url = _build_provider_url(self._base_url, "/api/events/")
        params = {"changed_at": changed_at}
        if cursor:
            params["cursor"] = cursor

        logger.debug("Requesting events: url=%s, params=%s", url, params)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                )
        except httpx.RequestError as e:
            raise ProviderError(status_code=503, detail=str(e)) from e

        self._raise_provider_error(response)
        data = response.json()
        logger.debug("Response status: %s", response.status_code)
        logger.debug("Response has %d results", len(data.get("results", [])))
        logger.debug("Next URL: %s", data.get("next"))

        events = []
        for event_data in data["results"]:
            place_data = event_data["place"]
            place = PlaceData(
                id=place_data["id"],
                name=place_data["name"],
                city=place_data["city"],
                address=place_data["address"],
                seats_pattern=place_data.get("seats_pattern"),
                changed_at=place_data.get("changed_at"),
                created_at=place_data.get("created_at"),
            )
            event = EventData(
                id=event_data["id"],
                name=event_data["name"],
                place=place,
                event_time=event_data["event_time"],
                registration_deadline=event_data.get("registration_deadline"),
                status=EventStatus(event_data["status"]),
                number_of_visitors=event_data.get("number_of_visitors", 0),
                changed_at=event_data["changed_at"],
                created_at=event_data["created_at"],
                status_changed_at=event_data.get("status_changed_at"),
            )
            events.append(event)
        logger.debug("Returning %d events", len(events))
        return events, data.get("next")

    async def get_seats(self, event_id: str) -> SeatsData:
        """Get available seats for an event.

        Args:
            event_id: Event UUID.

        Returns:
            SeatsData with list of available seats.
        """
        url = _build_provider_url(self._base_url, f"/api/events/{event_id}/seats/")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers=self._get_headers())
        except httpx.RequestError as e:
            raise ProviderError(status_code=503, detail=str(e)) from e

        self._raise_provider_error(response)
        data = response.json()

        return SeatsData(seats=data["seats"])

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> RegistrationData:
        """Register for an event.

        Args:
            event_id: Event UUID.
            first_name: Participant first name.
            last_name: Participant last name.
            email: Participant email.
            seat: Seat identifier.

        Returns:
            RegistrationData with ticket_id.
        """
        url = _build_provider_url(self._base_url, f"/api/events/{event_id}/register/")
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "seat": seat,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                )
        except httpx.RequestError as e:
            raise ProviderError(status_code=503, detail=str(e)) from e

        self._raise_provider_error(response)
        data = response.json()

        return RegistrationData(ticket_id=data["ticket_id"])

    async def unregister(self, event_id: str, ticket_id: str) -> UnregisterData:
        """Unregister from an event.

        Args:
            event_id: Event UUID.
            ticket_id: Ticket UUID.

        Returns:
            UnregisterData with success status.
        """
        url = _build_provider_url(self._base_url, f"/api/events/{event_id}/unregister/")
        payload = {"ticket_id": ticket_id}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    "DELETE",
                    url,
                    json=payload,
                    headers=self._get_headers(),
                )
        except httpx.RequestError as e:
            raise ProviderError(status_code=503, detail=str(e)) from e

        self._raise_provider_error(response)
        data = response.json()

        return UnregisterData(success=data["success"])
