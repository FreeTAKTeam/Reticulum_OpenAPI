"""Database configuration helpers for the Emergency Management example."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import inspect
from sqlalchemy import literal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from reticulum_openapi.database import create_async_engine_and_session
from reticulum_openapi.database import initialise_database
from reticulum_openapi.database import normalise_database_url

from .models_emergency import Base
from .models_emergency import EventDetailORM, EventORM, EventPointORM


DATABASE_ENV_VAR = "EMERGENCY_DATABASE_URL"
_DEFAULT_DATABASE_PATH = Path(__file__).resolve().with_name("emergency.db")
_DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{_DEFAULT_DATABASE_PATH}"

DATABASE_URL = _DEFAULT_DATABASE_URL
engine: Optional[AsyncEngine] = None
async_session: Optional[async_sessionmaker[AsyncSession]] = None


def _load_json_if_string(value: Optional[str]) -> Optional[Any]:
    """Return ``value`` decoded from JSON when represented as a string."""

    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        return decoded
    return value


def _backfill_event_components(connection) -> None:
    """Populate new event detail and point tables from legacy JSON columns."""

    inspector = inspect(connection)
    if "events" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("events")}
    has_detail_column = "detail" in columns
    has_point_column = "point" in columns

    if not has_detail_column and not has_point_column:
        return

    detail_table = EventDetailORM.__table__
    point_table = EventPointORM.__table__
    event_table = EventORM.__table__

    existing_detail = {
        row[0]
        for row in connection.execute(select(detail_table.c.event_uid))
    }
    existing_point = {
        row[0]
        for row in connection.execute(select(point_table.c.event_uid))
    }

    detail_column = (
        event_table.c.get("detail")
        if has_detail_column
        else literal(None).label("detail")
    )
    point_column = (
        event_table.c.get("point")
        if has_point_column
        else literal(None).label("point")
    )

    rows = connection.execute(
        select(
            event_table.c.uid,
            detail_column,
            point_column,
        )
    )

    for uid, raw_detail, raw_point in rows:
        if has_detail_column and uid not in existing_detail:
            detail_payload = _load_json_if_string(raw_detail)
            if isinstance(detail_payload, dict):
                message_payload = _load_json_if_string(
                    detail_payload.get("emergencyActionMessage")
                )
                connection.execute(
                    detail_table.insert().values(
                        event_uid=uid,
                        emergencyActionMessage=message_payload,
                    )
                )
                existing_detail.add(uid)

        if has_point_column and uid not in existing_point:
            point_payload = _load_json_if_string(raw_point)
            if isinstance(point_payload, dict):
                connection.execute(
                    point_table.insert().values(
                        event_uid=uid,
                        lat=point_payload.get("lat"),
                        lon=point_payload.get("lon"),
                        ce=point_payload.get("ce"),
                        le=point_payload.get("le"),
                        hae=point_payload.get("hae"),
                    )
                )
                existing_point.add(uid)


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

    resolved_url = normalise_database_url(
        url,
        default_url=_DEFAULT_DATABASE_URL,
        env_var=DATABASE_ENV_VAR,
    )

    if (
        resolved_url == DATABASE_URL
        and engine is not None
        and async_session is not None
    ):
        return DATABASE_URL

    created_engine, session_factory = create_async_engine_and_session(resolved_url)
    DATABASE_URL = resolved_url
    engine = created_engine
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

    await initialise_database(
        engine,
        metadata=Base.metadata,
        upgrade_hooks=(_backfill_event_components,),
    )


# Initialise the module-level engine and session factory using the default
# configuration or any environment override available during import.
configure_database(None)
