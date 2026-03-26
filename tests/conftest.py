"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.app import app
from src.core.database import Base, get_session
from src.core.dependencies import get_events_provider_client


@pytest.fixture(scope="session")
def api_key() -> str:
    """Return test API key."""
    return "test-api-key"


@pytest.fixture(scope="session")
def base_url() -> str:
    """Return test base URL."""
    return "http://test-events-provider.com"


# Database fixtures
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create test engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_provider_client() -> MagicMock:
    """Create a mock for EventsProviderClient."""
    return MagicMock()


# FastAPI client fixture
@pytest.fixture
async def client(
    db_session: AsyncSession, mock_provider_client: MagicMock
) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session and provider client overrides."""

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_events_provider_client() -> MagicMock:
        return mock_provider_client

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_events_provider_client] = (
        override_get_events_provider_client
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# Repository fixtures
from src.repositories.event_repository import SQLAlchemyEventRepository
from src.repositories.place_repository import SQLAlchemyPlaceRepository
from src.repositories.ticket_repository import SQLAlchemyTicketRepository
from src.repositories.sync_state_repository import SQLAlchemySyncStateRepository


@pytest.fixture
def event_repository(db_session: AsyncSession) -> SQLAlchemyEventRepository:
    """Create event repository fixture."""
    return SQLAlchemyEventRepository(db_session)


@pytest.fixture
def place_repository(db_session: AsyncSession) -> SQLAlchemyPlaceRepository:
    """Create place repository fixture."""
    return SQLAlchemyPlaceRepository(db_session)


@pytest.fixture
def ticket_repository(db_session: AsyncSession) -> SQLAlchemyTicketRepository:
    """Create ticket repository fixture."""
    return SQLAlchemyTicketRepository(db_session)


@pytest.fixture
def sync_state_repository(db_session: AsyncSession) -> SQLAlchemySyncStateRepository:
    """Create sync state repository fixture."""
    return SQLAlchemySyncStateRepository(db_session)


from datetime import datetime, timezone
from src.models.event import Place, Event


@pytest.fixture
async def sample_place(db_session: AsyncSession) -> Place:
    """Create sample place."""
    place = Place(
        id="test-place-id",
        name="Test Place",
        city="Test City",
        address="Test Address",
        seats_pattern="A[1-10]",
    )
    db_session.add(place)
    await db_session.flush()
    return place


@pytest.fixture
async def sample_event(db_session: AsyncSession, sample_place: Place) -> Event:
    """Create sample event."""
    event = Event(
        id="test-event-id",
        name="Test Event",
        place_id=sample_place.id,
        event_time=datetime.now(timezone.utc),
        status="new",
    )
    db_session.add(event)
    await db_session.flush()
    return event
