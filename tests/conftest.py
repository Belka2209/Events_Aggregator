"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def api_key() -> str:
    """Return test API key."""
    return "test-api-key"


@pytest.fixture
def base_url() -> str:
    """Return test base URL."""
    return "http://test-events-provider.com"
