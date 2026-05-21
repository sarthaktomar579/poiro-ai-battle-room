"""SQLAlchemy engine, session factory, and ORM declarative base.

SQLite is the default and is the simplest store that satisfies every entity
in the assignment (users, rooms, rounds, participants, submissions, jobs,
scores, events). Switching to Postgres requires only ``DATABASE_URL`` env.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()


def _prepare_sqlite_path(url: str) -> str:
    """Make sure the directory for a sqlite file URL actually exists."""
    if url.startswith("sqlite:///") and ":memory:" not in url:
        # sqlite:///./data/poiro.db  ->  ./data/poiro.db
        path = url.replace("sqlite:///", "", 1)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return url


DATABASE_URL = _prepare_sqlite_path(settings.database_url)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


def get_db():
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
