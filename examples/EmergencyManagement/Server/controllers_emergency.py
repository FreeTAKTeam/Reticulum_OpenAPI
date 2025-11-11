from typing import Dict
from typing import List
from typing import Optional

from reticulum_openapi.controller import Controller
from reticulum_openapi.controller import handle_exceptions
from reticulum_openapi.sqlalchemy_controller import SQLAlchemyControllerMixin
from reticulum_openapi.sqlalchemy_controller import SessionFactory

from examples.EmergencyManagement.Server import database
from examples.EmergencyManagement.Server.models_emergency import EmergencyActionMessage
from examples.EmergencyManagement.Server.models_emergency import Event


class _BaseDatabaseController(SQLAlchemyControllerMixin, Controller):
    """Shared database integration helpers for emergency controllers."""

    def get_default_session_factory(self) -> Optional[SessionFactory]:
        """Return the configured async session factory from the database module."""

        return database.async_session


class EmergencyController(_BaseDatabaseController):
    @handle_exceptions
    async def CreateEmergencyActionMessage(
        self, req: EmergencyActionMessage
    ) -> EmergencyActionMessage:
        self.logger.info(f"CreateEAM: {req}")
        return await self._create_instance(EmergencyActionMessage, req)

    @handle_exceptions
    async def DeleteEmergencyActionMessage(self, callsign: str) -> Dict[str, str]:
        self.logger.info(f"DeleteEAM callsign={callsign}")
        deleted = await self._delete_instance(EmergencyActionMessage, callsign)
        return {"status": "deleted" if deleted else "not_found", "callsign": callsign}

    @handle_exceptions
    async def ListEmergencyActionMessage(
        self,
    ) -> List[EmergencyActionMessage]:
        self.logger.info("ListEAM")
        return await self._list_instances(EmergencyActionMessage)

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
        return await self._update_instance(EmergencyActionMessage, req)

    @handle_exceptions
    async def RetrieveEmergencyActionMessage(
        self, callsign: str
    ) -> Optional[EmergencyActionMessage]:
        self.logger.info(f"RetrieveEAM callsign={callsign}")
        return await self._retrieve_instance(EmergencyActionMessage, callsign)


class EventController(_BaseDatabaseController):
    @handle_exceptions
    async def CreateEvent(self, req: Event) -> Event:
        self.logger.info(f"CreateEvent: {req}")
        return await self._create_instance(Event, req)

    @handle_exceptions
    async def DeleteEvent(self, uid: str) -> Dict[str, str]:
        self.logger.info(f"DeleteEvent uid={uid}")
        deleted = await self._delete_instance(Event, uid)
        return {"status": "deleted" if deleted else "not_found", "uid": uid}

    @handle_exceptions
    async def ListEvent(self) -> List[Event]:
        self.logger.info("ListEvent")
        return await self._list_instances(Event)

    @handle_exceptions
    async def PutEvent(self, req: Event) -> Optional[Event]:
        """Update an event record.

        Args:
            req (Event): New values for the event.

        Returns:
            Optional[Event]: Updated dataclass instance or ``None`` if not found.
        """
        self.logger.info(f"PutEvent: {req}")
        return await self._update_instance(Event, req)

    @handle_exceptions
    async def RetrieveEvent(self, uid: str) -> Optional[Event]:
        self.logger.info(f"RetrieveEvent uid={uid}")
        return await self._retrieve_instance(Event, uid)
