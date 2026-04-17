"""Tests for Capashino client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.capashino_client import (
    CapashinoClient,
    CapashinoError,
)


class TestCapashinoClient:
    """Tests for CapashinoClient."""

    @pytest.mark.asyncio
    async def test_create_notification_success(self):
        """Test successful notification creation."""
        client = CapashinoClient()
        client._base_url = "http://test"
        client._api_key = "test-key"
        client._timeout = 30.0

        mock_response = {
            "id": "notif-123",
            "user_id": "user-456",
            "message": "Test message",
            "reference_id": "ticket-789",
            "created_at": "2024-01-01T00:00:00Z",
        }

        with patch("httpx.AsyncClient") as mock_client:

            async def mock_post(*args, **kwargs):
                response = MagicMock()
                response.status_code = 201
                response.json.return_value = mock_response
                return response

            mock_instance = MagicMock()
            mock_instance.post = mock_post
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await client.create_notification(
                message="Test message",
                reference_id="ticket-789",
            )

            assert result.id == "notif-123"
            assert result.message == "Test message"
            assert result.reference_id == "ticket-789"

    @pytest.mark.asyncio
    async def test_create_notification_409_conflict(self):
        """Test notification creation with 409 conflict (idempotency)."""
        client = CapashinoClient()
        client._base_url = "http://test"
        client._api_key = "test-key"
        client._timeout = 30.0

        mock_response = {
            "id": "notif-123",
            "user_id": "user-456",
            "message": "Test message",
            "reference_id": "ticket-789",
            "created_at": "2024-01-01T00:00:00Z",
            "idempotency_key": "key-123",
        }

        with patch("httpx.AsyncClient") as mock_client:

            async def mock_post(*args, **kwargs):
                response = MagicMock()
                response.status_code = 409
                response.json.return_value = mock_response
                return response

            mock_instance = MagicMock()
            mock_instance.post = mock_post
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await client.create_notification(
                message="Test message",
                reference_id="ticket-789",
                idempotency_key="key-123",
            )

            assert result.id == "notif-123"

    @pytest.mark.asyncio
    async def test_create_notification_400_error(self):
        """Test notification creation with 400 error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            client = CapashinoClient()
            client._base_url = "http://test"
            client._api_key = "test-key"

            with pytest.raises(CapashinoError) as exc_info:
                await client.create_notification(
                    message="Test message",
                    reference_id="ticket-789",
                )

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_create_notification_401_error(self):
        """Test notification creation with 401 error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            client = CapashinoClient()
            client._base_url = "http://test"
            client._api_key = "invalid-key"

            with pytest.raises(CapashinoError) as exc_info:
                await client.create_notification(
                    message="Test message",
                    reference_id="ticket-789",
                )

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_create_notification_server_error(self):
        """Test notification creation with 500 error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            client = CapashinoClient()
            client._base_url = "http://test"
            client._api_key = "test-key"

            with pytest.raises(CapashinoError) as exc_info:
                await client.create_notification(
                    message="Test message",
                    reference_id="ticket-789",
                )

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_create_notification_connection_error(self):
        """Test notification creation with connection error."""
        with patch("httpx.AsyncClient") as mock_client:
            import httpx

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )

            client = CapashinoClient()
            client._base_url = "http://test"
            client._api_key = "test-key"

            with pytest.raises(CapashinoError):
                await client.create_notification(
                    message="Test message",
                    reference_id="ticket-789",
                )
