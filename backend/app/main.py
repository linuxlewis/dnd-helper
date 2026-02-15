import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.logging_config import setup_logging
from app.models import (  # noqa: F401 - import to register with SQLModel metadata
    Character,
    CharacterItem,
    HistoryEntry,
    Inventory,
    Item,
)
from app.routers import (
    currency_router,
    history_router,
    inventories_router,
    items_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure logging and create database tables on startup."""
    setup_logging(settings.log_file, settings.log_level)
    logging.info("Backend starting up...")
    await init_db()
    yield
    logging.info("Backend shutting down...")


app = FastAPI(title="D&D Party Inventory Manager", version="0.1.0", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(inventories_router)
app.include_router(items_router)
app.include_router(currency_router)
app.include_router(history_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
