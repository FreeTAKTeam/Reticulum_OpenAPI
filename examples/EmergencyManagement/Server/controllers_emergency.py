import asyncio
from dataclasses import asdict
from reticulum_openapi.controller import Controller, handle_exceptions
from examples.EmergencyManagement.Server.database import async_session
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    Event,
    EAMStatus,
    Detail,
    Point,
)


class EmergencyController(Controller):
    @handle_exceptions
    async def CreateEmergencyActionMessage(self, req: EmergencyActionMessage):
        self.logger.info(f"CreateEAM: {req}")
        async with async_session() as session:
            await EmergencyActionMessage.create(session, **asdict(req))
        return req

    @handle_exceptions
    async def DeleteEmergencyActionMessage(self, callsign: str):
        self.logger.info(f"DeleteEAM callsign={callsign}")
        async with async_session() as session:
            deleted = await EmergencyActionMessage.delete(session, callsign)
        return {"status": "deleted" if deleted else "not_found", "callsign": callsign}

    @handle_exceptions
    async def ListEmergencyActionMessage(self):
        self.logger.info("ListEAM")
        async with async_session() as session:
            items = await EmergencyActionMessage.list(session)
        return items

    @handle_exceptions
    async def PatchEmergencyActionMessage(self, req: EmergencyActionMessage):
        self.logger.info(f"PatchEAM: {req}")
        async with async_session() as session:
            updated = await EmergencyActionMessage.update(session, req.callsign, **asdict(req))
        return updated

    @handle_exceptions
    async def RetrieveEmergencyActionMessage(self, callsign: str):
        self.logger.info(f"RetrieveEAM callsign={callsign}")
        async with async_session() as session:
            item = await EmergencyActionMessage.get(session, callsign)
        return item


class EventController(Controller):
    @handle_exceptions
    async def CreateEvent(self, req: Event):
        self.logger.info(f"CreateEvent: {req}")
        async with async_session() as session:
            await Event.create(session, **asdict(req))
        return req

    @handle_exceptions
    async def DeleteEvent(self, uid: str):
        self.logger.info(f"DeleteEvent uid={uid}")
        async with async_session() as session:
            deleted = await Event.delete(session, int(uid))
        return {"status": "deleted" if deleted else "not_found", "uid": uid}

    @handle_exceptions
    async def ListEvent(self):
        self.logger.info("ListEvent")
        async with async_session() as session:
            events = await Event.list(session)
        return events

    @handle_exceptions
    async def PatchEvent(self, req: Event):
        self.logger.info(f"PatchEvent: {req}")
        async with async_session() as session:
            updated = await Event.update(session, req.uid, **asdict(req))
        return updated

    @handle_exceptions
    async def RetrieveEvent(self, uid: str):
        self.logger.info(f"RetrieveEvent uid={uid}")
        async with async_session() as session:
            event = await Event.get(session, int(uid))
        return event
