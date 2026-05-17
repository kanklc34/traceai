import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .core.anomaly_manager import anomaly_manager
from .api.v1.endpoints import router as api_v1_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("traceai")

anomaly_queue = asyncio.Queue(maxsize=50)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (WAL Mode, etc.)
    await init_db()
    
    # Start Background Workers
    app.state.t1 = asyncio.create_task(anomaly_manager.start_worker(anomaly_queue))
    app.state.t2 = asyncio.create_task(anomaly_manager.start_ai_worker(anomaly_queue))
    
    logger.info("[SYSTEM] TraceAI Gemma 4 Agent Operational")
    yield
    # Graceful Shutdown
    app.state.t1.cancel()
    app.state.t2.cancel()
    logger.info("[SYSTEM] Pipeline shutdown complete")

app = FastAPI(
    title="TraceAI API",
    description="Gemma 4 incident investigation agent for critical systems",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(api_v1_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)