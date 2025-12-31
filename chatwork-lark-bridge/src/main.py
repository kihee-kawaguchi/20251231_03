"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .core.config import settings
from .core.logging import setup_logging, get_logger
from .core.exceptions import BridgeException
from .services.redis_client import redis_client
from .services.mapping_loader import mapping_loader
from .services.chatwork_client import chatwork_client
from .api import chatwork, lark, health

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("application_starting", env=settings.env)

    # Connect to Redis
    await redis_client.connect()

    # Load room and user mappings
    try:
        room_count = await mapping_loader.load_room_mappings()
        user_count = await mapping_loader.load_user_mappings()
        logger.info(
            "mappings_loaded_successfully",
            rooms=room_count,
            users=user_count,
        )
    except Exception as e:
        logger.error("failed_to_load_mappings", error=str(e))
        # Continue startup even if mappings fail to load

    yield

    # Shutdown
    logger.info("application_shutting_down")
    await redis_client.disconnect()
    await chatwork_client.close()


# Create FastAPI app
app = FastAPI(
    title="Chatwork-Lark Bridge",
    description="Bidirectional message synchronization between Chatwork and Lark",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)


# Exception handlers
@app.exception_handler(BridgeException)
async def bridge_exception_handler(request: Request, exc: BridgeException):
    """Handle custom bridge exceptions."""
    logger.error(
        "bridge_exception",
        exception_type=type(exc).__name__,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "ValidationError", "details": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        "unexpected_exception",
        exception_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
        },
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(chatwork.router, prefix="/webhook/chatwork", tags=["chatwork"])
app.include_router(lark.router, prefix="/webhook/lark", tags=["lark"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Chatwork-Lark Bridge",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.env,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
