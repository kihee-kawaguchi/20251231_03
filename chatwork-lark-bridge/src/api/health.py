"""Health check endpoints."""

from fastapi import APIRouter, status
from pydantic import BaseModel

from ..services.redis_client import redis_client
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    redis: bool
    details: dict = {}


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns the health status of the application and its dependencies.
    """
    redis_healthy = await redis_client.health_check()

    is_healthy = redis_healthy

    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        redis=redis_healthy,
        details={
            "redis": "connected" if redis_healthy else "disconnected",
        },
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Readiness check endpoint.

    Returns 200 if the application is ready to receive traffic.
    """
    redis_healthy = await redis_client.health_check()

    if not redis_healthy:
        logger.warning("readiness_check_failed", reason="redis_unhealthy")
        return {"ready": False, "reason": "Redis not connected"}

    return {"ready": True}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    Liveness check endpoint.

    Returns 200 if the application is alive.
    """
    return {"alive": True}
