"""
SQLAlchemy session + engine.

Central place for DB access. Replaces the Supabase-client pattern for all new
code. Supports Postgres (prod) and SQLite (tests) via DATABASE_URL.
"""
from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DB_URL = "postgresql://postgres:postgres@127.0.0.1:5432/crossfit"


def _resolve_db_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DB_URL)


def _make_engine(url: str | None = None):
    db_url = url or _resolve_db_url()
    kwargs: dict = {"future": True, "pool_pre_ping": True}
    if db_url.startswith("sqlite"):
        # Needed for sharing an in-memory SQLite DB across threads in tests.
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(db_url, **kwargs)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and closes it after the request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def reset_engine_for_tests(url: str):
    """Swap the global engine + sessionmaker — used only by the test fixture."""
    global engine, SessionLocal
    engine.dispose()
    engine = _make_engine(url)
    SessionLocal.configure(bind=engine)
