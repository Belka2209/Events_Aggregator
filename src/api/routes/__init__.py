"""API routes."""

from src.api.routes.events import router as events_router
from src.api.routes.health import router as health_router
from src.api.routes.seats import router as seats_router
from src.api.routes.sync import router as sync_router
from src.api.routes.tickets import router as tickets_router

__all__ = [
    "events_router",
    "health_router",
    "seats_router",
    "sync_router",
    "tickets_router",
]
