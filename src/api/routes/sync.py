"""Sync endpoints."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.repositories.event_repository import SQLAlchemyEventRepository
from src.repositories.place_repository import SQLAlchemyPlaceRepository
from src.repositories.sync_state_repository import SQLAlchemySyncStateRepository
from src.schemas.api_schemas import SyncTriggerResponse
from src.services.events_provider_client import EventsProviderClient
from src.usecases.sync_events import SyncEventsUsecase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/sync/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    session: AsyncSession = Depends(get_session),
) -> SyncTriggerResponse:
    """Trigger manual synchronization.

    Returns:
        Sync status and statistics.
    """
    logger.info("Manual sync triggered")

    # Create repositories
    event_repo = SQLAlchemyEventRepository(session)
    place_repo = SQLAlchemyPlaceRepository(session)
    sync_state_repo = SQLAlchemySyncStateRepository(session)

    # Create client and usecase
    client = EventsProviderClient()
    usecase = SyncEventsUsecase(
        client=client,
        event_repo=event_repo,
        place_repo=place_repo,
        sync_state_repo=sync_state_repo,
    )

    # Execute sync
    stats = await usecase.execute()

    return SyncTriggerResponse(
        status="success",
        message="Synchronization completed",
        stats=stats,
    )
