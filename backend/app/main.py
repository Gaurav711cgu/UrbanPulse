"""
UrbanPulse Backend — FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import junctions, traffic, forecast, websocket
from app.services.signal_controller import SignalController
from app.services.mock_data import MockDataService


signal_controller: SignalController | None = None
mock_service: MockDataService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    global signal_controller, mock_service

    # Initialize DB tables
    await init_db()

    # Start signal controller (runs DQN inference loop)
    signal_controller = SignalController()
    await signal_controller.start()

    # Start mock data service in dev mode
    if settings.ENV == "development":
        mock_service = MockDataService()
        await mock_service.start()

    yield

    # Shutdown
    if signal_controller:
        await signal_controller.stop()
    if mock_service:
        await mock_service.stop()


app = FastAPI(
    title="UrbanPulse API",
    description="AI-Powered Traffic & Transport Optimization API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(junctions.router, prefix="/api/v1/junctions", tags=["Junctions"])
app.include_router(traffic.router, prefix="/api/v1/traffic", tags=["Traffic"])
app.include_router(forecast.router, prefix="/api/v1/forecast", tags=["Forecast"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "project": "UrbanPulse",
        "status": "operational",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
