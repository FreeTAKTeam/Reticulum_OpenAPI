"""Database configuration helpers for the Emergency Management example."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models_emergency import Base


DATABASE_ENV_VAR = "EMERGENCY_DATABASE_URL"
_DEFAULT_DATABASE_PATH = Path(__file__).resolve().with_name("emergency.db")
_DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{_DEFAULT_DATABASE_PATH}"

DATABASE_URL = _DEFAULT_DATABASE_URL
engine: Optional[AsyncEngine] = None
async_session: Optional[async_sessionmaker[AsyncSession]] = None


def _normalise_database_url(candidate: Optional[str]) -> str:
    """Convert ``candidate`` into a SQLAlchemy database URL.

    Args:
        candidate (Optional[str]): Potential override provided via the
            environment, CLI, or direct helper invocation.

    Returns:
        str: The normalised SQLAlchemy database URL.
    """

    if not candidate:
        env_value = os.getenv(DATABASE_ENV_VAR)
        candidate = env_value if env_value else None

    if not candidate:
        return _DEFAULT_DATABASE_URL

    if "://" not in candidate:
        db_path = Path(candidate).expanduser().resolve()
        return f"sqlite+aiosqlite:///{db_path}"

    return candidate


def _create_engine_and_session(
    url: str,
) -> Tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create an async engine and session factory for ``url``.

    Args:
        url (str): Database URL to connect to.

    Returns:
        Tuple[AsyncEngine, async_sessionmaker[AsyncSession]]: Engine and
        session factory pair configured for the provided URL.
    """

    engine = create_async_engine(url, echo=False)
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return engine, session_factory


def configure_database(url: Optional[str] = None) -> str:
    """Configure the database engine and session factory.

    Args:
        url (Optional[str]): Optional override for the database URL. File paths
            are converted into SQLite URLs automatically. When ``None``, the
            helper honours :data:`DATABASE_ENV_VAR` or falls back to the default
            database file next to this module.

    Returns:
        str: The database URL that was applied.
    """

    global DATABASE_URL
    global engine
    global async_session

    resolved_url = _normalise_database_url(url)

    if (
        resolved_url == DATABASE_URL
        and engine is not None
        and async_session is not None
    ):
        return DATABASE_URL

    engine, session_factory = _create_engine_and_session(resolved_url)
    DATABASE_URL = resolved_url
    async_session = session_factory
    return DATABASE_URL


async def init_db(url: Optional[str] = None) -> None:
    """Initialise the database schema if it does not exist.

    Args:
        url (Optional[str]): Optional override passed through to
            :func:`configure_database`.

    Returns:
        None: The coroutine completes once the schema has been created.
    """

    configure_database(url)
    if engine is None:
        raise RuntimeError("Database engine is not configured")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Initialise the module-level engine and session factory using the default
# configuration or any environment override available during import.
configure_database(None)
