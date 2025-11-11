"""Shared SQLAlchemy controller helpers for async CRUD operations."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import asdict
from typing import Any, Callable, Optional, Type, TypeVar

from .model import BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)
SessionFactory = Callable[[], AbstractAsyncContextManager[Any]]


class SQLAlchemyControllerMixin:
    """Provide reusable async CRUD helpers for SQLAlchemy-backed controllers."""

    session_factory: Optional[SessionFactory] = None

    def __init__(
        self,
        session_factory: Optional[SessionFactory] = None,
        **kwargs: Any,
    ) -> None:
        """Initialise the mixin with an optional session factory override."""

        super().__init__(**kwargs)
        self._session_factory_override = session_factory

    @classmethod
    def configure_session_factory(
        cls,
        session_factory: Optional[SessionFactory],
    ) -> None:
        """Set a class-level session factory used by all controller instances."""

        cls.session_factory = session_factory

    def get_default_session_factory(self) -> Optional[SessionFactory]:
        """Return the default session factory for this controller instance."""

        return None

    def _require_session_factory(self) -> SessionFactory:
        """Return the configured session factory or raise an error."""

        for candidate in (
            getattr(self, "_session_factory_override", None),
            getattr(type(self), "session_factory", None),
            self.get_default_session_factory(),
        ):
            if candidate is not None:
                return candidate
        raise RuntimeError("Database session factory is not configured")

    @staticmethod
    def _get_primary_key_column(model: Type[ModelT]):
        """Return the SQLAlchemy column representing the model primary key."""

        orm_model = getattr(model, "__orm_model__", None)
        if orm_model is None:
            raise RuntimeError(f"{model.__name__} does not define an ORM mapping")
        primary_key_columns = list(orm_model.__table__.primary_key.columns)  # type: ignore[attr-defined]
        if len(primary_key_columns) != 1:
            raise RuntimeError(
                f"{model.__name__} must define exactly one primary key column"
            )
        return primary_key_columns[0]

    @classmethod
    def _coerce_identifier(cls, model: Type[ModelT], identifier: Any) -> Any:
        """Convert an identifier into the Python type expected by the ORM column."""

        column = cls._get_primary_key_column(model)
        python_type = getattr(column.type, "python_type", None)
        if python_type is None or isinstance(identifier, python_type):
            return identifier
        try:
            return python_type(identifier)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid identifier for {model.__name__}: {identifier!r}"
            ) from exc

    async def _create_instance(self, model: Type[ModelT], payload: ModelT) -> ModelT:
        """Persist ``payload`` using the model helper and return the stored instance."""

        session_factory = self._require_session_factory()
        async with session_factory() as session:
            return await model.create(session, **asdict(payload))

    async def _update_instance(
        self,
        model: Type[ModelT],
        payload: ModelT,
    ) -> Optional[ModelT]:
        """Update ``payload`` using the model helper and return the refreshed instance."""

        identifier_name = self._get_primary_key_column(model).name
        identifier = getattr(payload, identifier_name)
        session_factory = self._require_session_factory()
        async with session_factory() as session:
            return await model.update(session, identifier, **asdict(payload))

    async def _retrieve_instance(
        self,
        model: Type[ModelT],
        identifier: Any,
    ) -> Optional[ModelT]:
        """Return a stored instance or ``None`` when the identifier is unknown."""

        resolved_identifier = self._coerce_identifier(model, identifier)
        session_factory = self._require_session_factory()
        async with session_factory() as session:
            return await model.get(session, resolved_identifier)

    async def _delete_instance(self, model: Type[ModelT], identifier: Any) -> bool:
        """Delete the record referenced by ``identifier``."""

        resolved_identifier = self._coerce_identifier(model, identifier)
        session_factory = self._require_session_factory()
        async with session_factory() as session:
            return await model.delete(session, resolved_identifier)

    async def _list_instances(self, model: Type[ModelT]) -> list[ModelT]:
        """Return all stored instances for ``model``."""

        session_factory = self._require_session_factory()
        async with session_factory() as session:
            return await model.list(session)
