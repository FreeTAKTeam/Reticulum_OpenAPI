"""Integration tests for the shared database helpers."""

from __future__ import annotations

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, text

from reticulum_openapi.database import create_async_engine_and_session
from reticulum_openapi.database import initialise_database
from reticulum_openapi.database import normalise_database_url


def test_normalise_database_url_prefers_candidate_path(tmp_path, monkeypatch) -> None:
    """Explicit candidate paths should override environment defaults."""

    monkeypatch.setenv("RETICULUM_TEST_DB", "sqlite+aiosqlite:///env.db")
    db_path = tmp_path / "custom.sqlite"

    result = normalise_database_url(
        str(db_path),
        default_url="sqlite+aiosqlite:///default.db",
        env_var="RETICULUM_TEST_DB",
    )

    assert result.endswith("custom.sqlite")
    assert result.startswith("sqlite+aiosqlite:///")


def test_normalise_database_url_uses_environment(monkeypatch, tmp_path) -> None:
    """Environment variables should override configured defaults when present."""

    env_path = tmp_path / "env.sqlite"
    monkeypatch.setenv("RETICULUM_TEST_DB", str(env_path))

    result = normalise_database_url(
        None,
        default_url="sqlite+aiosqlite:///default.db",
        env_var="RETICULUM_TEST_DB",
    )

    assert result.endswith("env.sqlite")
    assert result.startswith("sqlite+aiosqlite:///")


@pytest.mark.asyncio
async def test_initialise_database_runs_upgrade_hook(tmp_path) -> None:
    """Upgrade hooks should run after schema creation for new databases."""

    db_path = tmp_path / "integration.sqlite"
    url = f"sqlite+aiosqlite:///{db_path}"

    metadata = MetaData()
    Table("items", metadata, Column("id", Integer, primary_key=True))

    hook_invocations = []

    def upgrade(connection) -> None:
        hook_invocations.append(
            connection.execute(text("SELECT COUNT(*) FROM items")).scalar_one()
        )

    engine, session_factory = create_async_engine_and_session(url)

    try:
        await initialise_database(
            engine,
            metadata=metadata,
            upgrade_hooks=(upgrade,),
        )

        async with session_factory() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM items"))
            assert result.scalar_one() == 0
    finally:
        await engine.dispose()

    assert hook_invocations == [0]
