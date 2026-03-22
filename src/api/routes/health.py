"""Health check endpoint."""

from fastapi import APIRouter

from src.schemas.api_schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status.
    """
    return {"status": "ok"}
