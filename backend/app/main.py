"""FastAPI application entry point.

Run with:

    uvicorn app.main:app --reload --reload-dir app --port 8000

The lifespan hook spins up the in-process job worker pool and creates the
SQLite schema on first boot.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .routers import auth as auth_router
from .routers import rooms as rooms_router
from .routers import rounds as rounds_router
from .routers import ws as ws_router
from .workers.job_worker import job_queue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await job_queue.start()
    try:
        yield
    finally:
        await job_queue.stop()


app = FastAPI(
    title="Poiro AI Battle Room",
    description="Real-time multiplayer AI battle room. See README for architecture.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(rooms_router.router)
app.include_router(rounds_router.router)
app.include_router(ws_router.router)


@app.get("/health", tags=["meta"])
def health():
    return {
        "status": "ok",
        "ai_provider": settings.ai_provider,
        "gemini_configured": bool(settings.gemini_api_key),
    }
