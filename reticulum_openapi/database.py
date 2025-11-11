"""Async database configuration helpers for Reticulum OpenAPI projects."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

from dotenv import load_dotenv
from sqlalchemy import MetaData
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()


def normalise_database_url(
    candidate: Optional[str],
    *,
    default_url: str,
    env_var: Optional[str] = None,
) -> str:
    """Convert ``candidate`` into an async SQLAlchemy database URL.

    Args:
        candidate (Optional[str]): Potential override provided via configuration
            files, CLI arguments, or direct helper invocation.
        default_url (str): URL to return when no overrides are provided.
        env_var (Optional[str]): Environment variable used as a secondary
            override before falling back to :data:`default_url`.

    Returns:
        str: The normalised SQLAlchemy database URL suitable for async engines.
    """

    if not candidate and env_var:
        env_value = os.getenv(env_var)
        candidate = env_value if env_value else None

    if not candidate:
        candidate = default_url

    if "://" not in candidate:
        db_path = Path(candidate).expanduser().resolve()
        return f"sqlite+aiosqlite:///{db_path}"

    return candidate


def create_async_engine_and_session(
    url: str,
    *,
    echo: bool = False,
    engine_kwargs: Optional[Dict[str, Any]] = None,
    session_kwargs: Optional[Dict[str, Any]] = None,
) -> Tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create an async engine and session factory for ``url``.

    Args:
        url (str): Database URL to connect to.
        echo (bool): When ``True`` SQLAlchemy will log SQL statements. Defaults
            to ``False``.
        engine_kwargs (Optional[Dict[str, Any]]): Additional keyword arguments
            forwarded to :func:`sqlalchemy.ext.asyncio.create_async_engine`.
        session_kwargs (Optional[Dict[str, Any]]): Keyword arguments applied to
            :func:`sqlalchemy.ext.asyncio.async_sessionmaker`.

    Returns:
        Tuple[AsyncEngine, async_sessionmaker[AsyncSession]]: Configured engine
        and session factory pair.
    """

    engine_options = engine_kwargs.copy() if engine_kwargs else {}
    engine = create_async_engine(url, echo=echo, **engine_options)

    session_options = {"expire_on_commit": False, "class_": AsyncSession}
    if session_kwargs:
        session_options.update(session_kwargs)

    session_factory = async_sessionmaker(engine, **session_options)
    return engine, session_factory


def _run_upgrade_hooks(
    connection: Connection,
    hooks: Sequence[Callable[[Connection], None]],
) -> None:
    """Execute upgrade hooks against a synchronous SQLAlchemy connection."""

    for hook in hooks:
        hook(connection)


async def initialise_database(
    engine: AsyncEngine,
    *,
    metadata: MetaData,
    upgrade_hooks: Optional[Sequence[Callable[[Connection], None]]] = None,
) -> None:
    """Initialise database schema and run upgrade hooks.

    Args:
        engine (AsyncEngine): Engine used to issue schema commands.
        metadata (MetaData): Metadata describing the schema to create.
        upgrade_hooks (Optional[Sequence[Callable[[Connection], None]]]):
            Iterable of callables executed after :meth:`MetaData.create_all`.
            Each hook receives a synchronous :class:`sqlalchemy.engine.Connection`.

    Returns:
        None: Completes once the schema exists and hooks have been executed.
    """

    hooks: Sequence[Callable[[Connection], None]] = upgrade_hooks if upgrade_hooks else ()

    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
        if hooks:
            await connection.run_sync(_run_upgrade_hooks, hooks)
