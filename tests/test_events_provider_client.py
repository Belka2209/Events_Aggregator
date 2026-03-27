"""Tests for EventsProviderClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.events_provider_client import EventsProviderClient


class AsyncContextManagerMock:
    """Async context manager mock for httpx.AsyncClient."""

    def __init__(self, client_mock: MagicMock):
        self._client_mock = client_mock

    async def __aenter__(self) -> MagicMock:
        return self._client_mock

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class TestEventsProviderClient:
    """Tests for EventsProviderClient."""

    @pytest.fixture
    def client(self, api_key: str, base_url: str) -> EventsProviderClient:
        """Create EventsProviderClient instance."""
        return EventsProviderClient(api_key=api_key)

    def test_init_with_api_key(self, api_key: str):
        """Test client initialization with API key."""
        client = EventsProviderClient(api_key=api_key)
        assert client._api_key == api_key

    def test_init_with_default_timeout(self, api_key: str):
        """Test client initialization with default timeout."""
        client = EventsProviderClient(api_key=api_key)
        assert client._timeout == 30.0

    def test_init_with_custom_timeout(self, api_key: str):
        """Test client initialization with custom timeout."""
        client = EventsProviderClient(api_key=api_key, timeout=60.0)
        assert client._timeout == 60.0

    def test_get_headers(self, client: EventsProviderClient, api_key: str):
        """Test headers generation."""
        headers = client._get_headers()
        assert headers["x-api-key"] == api_key
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_events_success(self, client: EventsProviderClient):
        """Test successful events fetch."""
        # Mock response data
        mock_data = {
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": "event-uuid-1",
                    "name": "Test Event",
                    "place": {
                        "id": "place-uuid-1",
                        "name": "Test Place",
                        "city": "Moscow",
                        "address": "Test Address",
                        "seats_pattern": "A1-100,B1-200",
                        "changed_at": "2025-01-01T00:00:00+00:00",
                        "created_at": "2025-01-01T00:00:00+00:00",
                    },
                    "event_time": "2026-01-11T17:00:00+00:00",
                    "registration_deadline": "2026-01-10T17:00:00+00:00",
                    "status": "published",
                    "number_of_visitors": 5,
                    "changed_at": "2026-01-04T22:28:35.325270+00:00",
                    "created_at": "2026-01-04T22:28:35.325302+00:00",
                    "status_changed_at": "2026-01-04T22:28:35.325386+00:00",
                }
            ],
        }

        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None

        # Create mock client
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Create async context manager
        context_manager = AsyncContextManagerMock(mock_client)

        with patch(
            "src.services.events_provider_client.httpx.AsyncClient",
            return_value=context_manager,
        ):
            events, next_cursor = await client.events(changed_at="2000-01-01")

        # Assertions
        assert len(events) == 1
        assert next_cursor is None
        assert events[0].id == "event-uuid-1"
        assert events[0].name == "Test Event"
        assert events[0].place.id == "place-uuid-1"
        assert events[0].place.city == "Moscow"

    @pytest.mark.asyncio
    async def test_events_with_pagination(self, client: EventsProviderClient):
        """Test events fetch with pagination."""
        mock_data = {
            "next": "http://test.com/api/events/?changed_at=2000-01-01&cursor=abc123",
            "previous": None,
            "results": [
                {
                    "id": "event-uuid-1",
                    "name": "Test Event 1",
                    "place": {
                        "id": "place-uuid-1",
                        "name": "Test Place",
                        "city": "Moscow",
                        "address": "Test Address",
                        "seats_pattern": None,
                        "changed_at": None,
                        "created_at": None,
                    },
                    "event_time": "2026-01-11T17:00:00+00:00",
                    "registration_deadline": None,
                    "status": "new",
                    "number_of_visitors": 0,
                    "changed_at": "2026-01-04T22:28:35.325270+00:00",
                    "created_at": "2026-01-04T22:28:35.325302+00:00",
                    "status_changed_at": None,
                }
            ],
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        context_manager = AsyncContextManagerMock(mock_client)

        with patch(
            "src.services.events_provider_client.httpx.AsyncClient",
            return_value=context_manager,
        ):
            events, next_cursor = await client.events(changed_at="2000-01-01")

        assert len(events) == 1
        assert next_cursor is not None
        assert "cursor=abc123" in next_cursor

    @pytest.mark.asyncio
    async def test_get_seats_success(self, client: EventsProviderClient):
        """Test successful seats fetch."""
        mock_data = {"seats": ["A1", "A2", "A3", "B1"]}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        context_manager = AsyncContextManagerMock(mock_client)

        with patch(
            "src.services.events_provider_client.httpx.AsyncClient",
            return_value=context_manager,
        ):
            seats = await client.get_seats("event-uuid-1")

        assert seats.seats == ["A1", "A2", "A3", "B1"]

    @pytest.mark.asyncio
    async def test_register_success(self, client: EventsProviderClient):
        """Test successful registration."""
        mock_data = {"ticket_id": "ticket-uuid-123"}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        context_manager = AsyncContextManagerMock(mock_client)

        with patch(
            "src.services.events_provider_client.httpx.AsyncClient",
            return_value=context_manager,
        ):
            registration = await client.register(
                event_id="event-uuid-1",
                first_name="Ivan",
                last_name="Ivanov",
                email="ivan@example.com",
                seat="A15",
            )

        assert registration.ticket_id == "ticket-uuid-123"

    @pytest.mark.asyncio
    async def test_unregister_success(self, client: EventsProviderClient):
        """Test successful unregistration."""
        mock_data = {"success": True}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.is_error = False
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        context_manager = AsyncContextManagerMock(mock_client)

        with patch(
            "src.services.events_provider_client.httpx.AsyncClient",
            return_value=context_manager,
        ):
            result = await client.unregister(event_id="event-uuid-1", ticket_id="ticket-uuid-123")

        mock_client.request.assert_called_once_with(
            "DELETE",
            f"{client._base_url}/api/events/event-uuid-1/unregister/",
            json={"ticket_id": "ticket-uuid-123"},
            headers=client._get_headers(),
        )
        assert result.success is True
