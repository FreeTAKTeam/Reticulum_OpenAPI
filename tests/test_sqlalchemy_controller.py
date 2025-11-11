"""Unit tests for :mod:`reticulum_openapi.sqlalchemy_controller`."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
import pytest_asyncio
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base

from reticulum_openapi.controller import Controller
from reticulum_openapi.model import BaseModel
from reticulum_openapi.sqlalchemy_controller import SQLAlchemyControllerMixin


Base = declarative_base()


class DummyORM(Base):
    """SQLAlchemy ORM model used to exercise the controller mixin."""

    __tablename__ = "dummy_records"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


@dataclass
class DummyModel(BaseModel):
    """Dataclass backed by :class:`DummyORM` for CRUD tests."""

    id: int
    name: str


DummyModel.__orm_model__ = DummyORM


class DummyController(SQLAlchemyControllerMixin, Controller):
    """Minimal controller implementation exposing the mixin helpers."""

    def __init__(self, session_factory=None) -> None:
        super().__init__(session_factory=session_factory)


@pytest_asyncio.fixture
async def dummy_session_factory():
    """Create an in-memory SQLite session factory for tests."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    yield session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_mixin_requires_session_factory() -> None:
    """The mixin raises when no session factory is configured."""

    controller = DummyController()

    with pytest.raises(RuntimeError):
        await controller._list_instances(DummyModel)


@pytest.mark.asyncio
async def test_mixin_crud_flow(dummy_session_factory) -> None:
    """CRUD helpers persist, retrieve, update, list, and delete records."""

    controller = DummyController(session_factory=dummy_session_factory)

    created = await controller._create_instance(
        DummyModel, DummyModel(id=1, name="Alpha")
    )
    assert created.name == "Alpha"

    retrieved = await controller._retrieve_instance(DummyModel, "1")
    assert retrieved is not None
    assert retrieved.id == 1
    assert retrieved.name == "Alpha"

    with pytest.raises(ValueError):
        await controller._retrieve_instance(DummyModel, "not-a-number")

    updated = await controller._update_instance(
        DummyModel,
        DummyModel(id=1, name="Beta"),
    )
    assert updated is not None
    assert updated.name == "Beta"

    listing = await controller._list_instances(DummyModel)
    assert [item.name for item in listing] == ["Beta"]

    deleted = await controller._delete_instance(DummyModel, 1)
    assert deleted is True

    missing = await controller._delete_instance(DummyModel, 1)
    assert missing is False


@pytest.mark.asyncio
async def test_mixin_class_level_session_factory(dummy_session_factory) -> None:
    """Controllers may rely on the class-level session factory configuration."""

    DummyController.configure_session_factory(dummy_session_factory)
    try:
        controller = DummyController()
        result = await controller._create_instance(
            DummyModel,
            DummyModel(id=5, name="Gamma"),
        )
        assert result.id == 5
    finally:
        DummyController.configure_session_factory(None)
