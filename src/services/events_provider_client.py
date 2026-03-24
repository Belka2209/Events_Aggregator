"""Events Provider API client."""

from dataclasses import dataclass

import httpx
from fastapi import HTTPException

from src.core.settings import settings


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
    status: str
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
        url = f"{self._base_url}/api/events/"
        params = {"changed_at": changed_at}
        if cursor:
            params["cursor"] = cursor

        print(f"Requesting events: url={url}, params={params}")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()
            print(f"Response status: {response.status_code}")

            response.raise_for_status()
            data = response.json()
            print(f"Response has {len(data.get('results', []))} results")
            print(f"Next URL: {data.get('next')}")

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
                status=event_data["status"],
                number_of_visitors=event_data.get("number_of_visitors", 0),
                changed_at=event_data["changed_at"],
                created_at=event_data["created_at"],
                status_changed_at=event_data.get("status_changed_at"),
            )
            events.append(event)
        print(f"Returning {len(events)} events")
        return events, data.get("next")

    async def get_seats(self, event_id: str) -> SeatsData:
        """Get available seats for an event.

        Args:
            event_id: Event UUID.

        Returns:
            SeatsData with list of available seats.
        """
        url = f"{self._base_url}/api/events/{event_id}/seats/"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
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
        url = f"{self._base_url}/api/events/{event_id}/register/"
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "seat": seat,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
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
        url = f"{self._base_url}/api/events/{event_id}/unregister/"
        payload = {"ticket_id": ticket_id}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(
                "DELETE", url, json=payload, headers=self._get_headers()
            )
            if response.is_error:
                detail = response.text
                try:
                    detail = response.json().get("detail", detail)
                except Exception:
                    pass
                raise HTTPException(status_code=response.status_code, detail=detail)

            data = response.json()

        return UnregisterData(success=data["success"])
