from dataclasses import asdict

from reticulum_openapi.controller import Controller, handle_exceptions
from examples.EmergencyManagement.Server.database import async_session
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    Event,
)


class EmergencyController(Controller):
    @handle_exceptions
    async def CreateEmergencyActionMessage(self, req: dict):
        self.logger.info(f"CreateEAM: {req}")
        data = {k: v for k, v in req.items() if k != "auth_token"}
        eam = EmergencyActionMessage(**data)
        async with async_session() as session:
            await EmergencyActionMessage.create(session, **asdict(eam))
        return eam

    @handle_exceptions
    async def DeleteEmergencyActionMessage(self, req: dict):
        callsign = req.get("callsign")
        self.logger.info(f"DeleteEAM callsign={callsign}")
        async with async_session() as session:
            deleted = await EmergencyActionMessage.delete(session, callsign)
        return {"status": "deleted" if deleted else "not_found", "callsign": callsign}

    @handle_exceptions
    async def ListEmergencyActionMessage(self, _payload: dict | None = None):
        self.logger.info("ListEAM")
        async with async_session() as session:
            items = await EmergencyActionMessage.list(session)
        return items

    @handle_exceptions
    async def PutEmergencyActionMessage(self, req: dict):
        self.logger.info(f"PutEAM: {req}")
        data = {k: v for k, v in req.items() if k != "auth_token"}
        async with async_session() as session:
            updated = await EmergencyActionMessage.update(
                session, data["callsign"], **data
            )
        return updated

    @handle_exceptions
    async def RetrieveEmergencyActionMessage(self, req: dict):
        callsign = req.get("callsign")
        self.logger.info(f"RetrieveEAM callsign={callsign}")
        async with async_session() as session:
            item = await EmergencyActionMessage.get(session, callsign)
        return item


class EventController(Controller):
    @handle_exceptions
    async def CreateEvent(self, req: dict):
        self.logger.info(f"CreateEvent: {req}")
        data = {k: v for k, v in req.items() if k != "auth_token"}
        ev = Event(**data)
        async with async_session() as session:
            await Event.create(session, **asdict(ev))
        return ev

    @handle_exceptions
    async def DeleteEvent(self, req: dict):
        uid = req.get("uid")
        self.logger.info(f"DeleteEvent uid={uid}")
        async with async_session() as session:
            deleted = await Event.delete(session, int(uid))
        return {"status": "deleted" if deleted else "not_found", "uid": uid}

    @handle_exceptions
    async def ListEvent(self, _payload: dict | None = None):
        self.logger.info("ListEvent")
        async with async_session() as session:
            events = await Event.list(session)
        return events

    @handle_exceptions
    async def PutEvent(self, req: dict):
        self.logger.info(f"PutEvent: {req}")
        data = {k: v for k, v in req.items() if k != "auth_token"}
        async with async_session() as session:
            updated = await Event.update(session, data["uid"], **data)
        return updated

    @handle_exceptions
    async def RetrieveEvent(self, req: dict):
        uid = req.get("uid")
        self.logger.info(f"RetrieveEvent uid={uid}")
        async with async_session() as session:
            event = await Event.get(session, int(uid))
        return event
