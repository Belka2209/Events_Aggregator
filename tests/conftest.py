"""Pytest configuration and fixtures."""

import pytest
from alembic.config import Config
from alembic import command



@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    yield
    command.downgrade(alembic_cfg, "base")


@pytest.fixture
def api_key() -> str:
    """Return test API key."""
    return "test-api-key"


@pytest.fixture
def base_url() -> str:
    """Return test base URL."""
    return "http://test-events-provider.com"
