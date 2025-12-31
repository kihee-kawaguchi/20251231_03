"""Demo server with fakeredis for local testing."""
import os
os.environ["ENV"] = "demo"

import asyncio
import fakeredis.aioredis
from src.main import app
from src.services.redis_client import redis_client
import uvicorn

# Override Redis client with fakeredis
async def override_redis():
    """Replace real Redis with fakeredis."""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    redis_client._client = fake
    redis_client._connected = True
    print("[OK] Using fakeredis for demo mode")
    return fake

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Chatwork-Lark Bridge in DEMO mode...")
    print("=" * 60)
    print("Using fakeredis (no real Redis required)")
    print("Server: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health/")
    print("=" * 60)
    print("")
    
    # Run with fakeredis
    async def startup():
        await override_redis()
    
    # Patch the lifespan to use fakeredis
    from src.main import lifespan
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def demo_lifespan(app):
        # Startup
        await override_redis()
        print("[OK] Demo server started successfully!")
        print("[INFO] Press CTRL+C to stop the server")
        print("")
        yield
        # Shutdown
        print("Shutting down demo server...")
    
    # Replace lifespan
    app.router.lifespan_context = demo_lifespan
    
    # Start server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
