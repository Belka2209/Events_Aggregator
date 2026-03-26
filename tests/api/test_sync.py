"""Tests for sync API."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_trigger_sync(client: AsyncClient):
    """Test manual sync trigger."""
    # We mock the usecase to avoid background tasks issues in tests
    with patch("src.api.routes.sync.SyncEventsUsecase") as mock_use_case_class:
        mock_instance = mock_use_case_class.return_value
        mock_instance.execute = AsyncMock(
            return_value={"created": 1, "updated": 0, "errors": 0}
        )

        response = await client.post("/api/sync/trigger")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "Synchronization started" in data["message"]
