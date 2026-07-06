from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import SolarGuardError


def get_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    resolved_url = database_url or settings.database_url
    return _cached_engine(resolved_url)


def build_engine(database_url: str | None) -> Engine:
    resolved_url = database_url
    if not resolved_url:
        raise SolarGuardError(
            "DATABASE_URL is required for Neon/PostgreSQL persistence",
            code="DB_CONFIG_MISSING",
        )
    return create_engine(_normalise_database_url(resolved_url), pool_pre_ping=True)


@lru_cache(maxsize=4)
def _cached_engine(database_url: str | None) -> Engine:
    return build_engine(database_url)


def _normalise_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def get_db_session() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def check_database_ready() -> bool:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
