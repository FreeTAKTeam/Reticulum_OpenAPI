from dataclasses import asdict
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar

from reticulum_openapi.controller import Controller
from reticulum_openapi.controller import handle_exceptions
from reticulum_openapi.model import BaseModel

from examples.EmergencyManagement.Server import database
from examples.EmergencyManagement.Server.models_emergency import EmergencyActionMessage
from examples.EmergencyManagement.Server.models_emergency import Event


ModelT = TypeVar("ModelT", bound=BaseModel)

# Backwards compatibility shim allowing tests to override the session factory.
async_session = None


def _require_session_factory():
    """Return the configured async session factory or raise an error."""

    if async_session is not None:
        return async_session
    if database.async_session is None:
        raise RuntimeError("Database session factory is not configured")
    return database.async_session


def _get_primary_key_column(model: Type[ModelT]):
    """Return the SQLAlchemy column representing the model primary key."""

    orm_model = getattr(model, "__orm_model__", None)
    if orm_model is None:
        raise RuntimeError(f"{model.__name__} does not define an ORM mapping")
    primary_key_columns = list(orm_model.__table__.primary_key.columns)
    if len(primary_key_columns) != 1:
        raise RuntimeError(
            f"{model.__name__} must define exactly one primary key column"
        )
    return primary_key_columns[0]


def _coerce_identifier(model: Type[ModelT], identifier: Any) -> Any:
    """Convert an identifier into the Python type expected by the ORM column."""

    column = _get_primary_key_column(model)
    python_type = getattr(column.type, "python_type", None)
    if python_type is None or isinstance(identifier, python_type):
        return identifier
    try:
        return python_type(identifier)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid identifier for {model.__name__}: {identifier!r}"
        ) from exc


async def _create_instance(model: Type[ModelT], payload: ModelT) -> ModelT:
    """Persist ``payload`` using the model helper and return the stored instance."""

    session_factory = _require_session_factory()
    async with session_factory() as session:
        return await model.create(session, **asdict(payload))


async def _update_instance(model: Type[ModelT], payload: ModelT) -> Optional[ModelT]:
    """Update ``payload`` using the model helper and return the refreshed instance."""

    identifier_name = _get_primary_key_column(model).name
    identifier = getattr(payload, identifier_name)
    session_factory = _require_session_factory()
    async with session_factory() as session:
        return await model.update(session, identifier, **asdict(payload))


async def _retrieve_instance(model: Type[ModelT], identifier: Any) -> Optional[ModelT]:
    """Return a stored instance or ``None`` when the identifier is unknown."""

    resolved_identifier = _coerce_identifier(model, identifier)
    session_factory = _require_session_factory()
    async with session_factory() as session:
        return await model.get(session, resolved_identifier)


async def _delete_instance(model: Type[ModelT], identifier: Any) -> bool:
    """Delete the record referenced by ``identifier``."""

    resolved_identifier = _coerce_identifier(model, identifier)
    session_factory = _require_session_factory()
    async with session_factory() as session:
        return await model.delete(session, resolved_identifier)


async def _list_instances(model: Type[ModelT]) -> List[ModelT]:
    """Return all stored instances for ``model``."""

    session_factory = _require_session_factory()
    async with session_factory() as session:
        return await model.list(session)


class EmergencyController(Controller):
    @handle_exceptions
    async def CreateEmergencyActionMessage(
        self, req: EmergencyActionMessage
    ) -> EmergencyActionMessage:
        self.logger.info(f"CreateEAM: {req}")
        return await _create_instance(EmergencyActionMessage, req)

    @handle_exceptions
    async def DeleteEmergencyActionMessage(self, callsign: str) -> Dict[str, str]:
        self.logger.info(f"DeleteEAM callsign={callsign}")
        deleted = await _delete_instance(EmergencyActionMessage, callsign)
        return {"status": "deleted" if deleted else "not_found", "callsign": callsign}

    @handle_exceptions
    async def ListEmergencyActionMessage(
        self,
    ) -> List[EmergencyActionMessage]:
        self.logger.info("ListEAM")
        return await _list_instances(EmergencyActionMessage)

    @handle_exceptions
    async def PutEmergencyActionMessage(
        self, req: EmergencyActionMessage
    ) -> Optional[EmergencyActionMessage]:
        """Update an existing emergency action message.

        Args:
            req (EmergencyActionMessage): New values for the message.

        Returns:
            Optional[EmergencyActionMessage]: Updated dataclass instance or ``None`` if not found.
        """
        self.logger.info(f"PutEAM: {req}")
        return await _update_instance(EmergencyActionMessage, req)

    @handle_exceptions
    async def RetrieveEmergencyActionMessage(
        self, callsign: str
    ) -> Optional[EmergencyActionMessage]:
        self.logger.info(f"RetrieveEAM callsign={callsign}")
        return await _retrieve_instance(EmergencyActionMessage, callsign)


class EventController(Controller):
    @handle_exceptions
    async def CreateEvent(self, req: Event) -> Event:
        self.logger.info(f"CreateEvent: {req}")
        return await _create_instance(Event, req)

    @handle_exceptions
    async def DeleteEvent(self, uid: str) -> Dict[str, str]:
        self.logger.info(f"DeleteEvent uid={uid}")
        deleted = await _delete_instance(Event, uid)
        return {"status": "deleted" if deleted else "not_found", "uid": uid}

    @handle_exceptions
    async def ListEvent(self) -> List[Event]:
        self.logger.info("ListEvent")
        return await _list_instances(Event)

    @handle_exceptions
    async def PutEvent(self, req: Event) -> Optional[Event]:
        """Update an event record.

        Args:
            req (Event): New values for the event.

        Returns:
            Optional[Event]: Updated dataclass instance or ``None`` if not found.
        """
        self.logger.info(f"PutEvent: {req}")
        return await _update_instance(Event, req)

    @handle_exceptions
    async def RetrieveEvent(self, uid: str) -> Optional[Event]:
        self.logger.info(f"RetrieveEvent uid={uid}")
        return await _retrieve_instance(Event, uid)
