mport asyncio
from reticulum_openapi.controller import Controller, handle_exceptions, APIException
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage, Event, EAMStatus
)

class EmergencyController(Controller):
    @handle_exceptions
    async def CreateEmergencyActionMessage(self, req: EmergencyActionMessage):
        self.logger.info(f"CreateEAM: {req}")
        await asyncio.sleep(0.1)
        return req

    @handle_exceptions
    async def DeleteEmergencyActionMessage(self, callsign: str):
        self.logger.info(f"DeleteEAM callsign={callsign}")
        await asyncio.sleep(0.1)
        return {"status":"deleted","callsign":callsign}

    @handle_exceptions
    async def ListEmergencyActionMessage(self):
        self.logger.info("ListEAM")
        await asyncio.sleep(0.1)
        return []

    @handle_exceptions
    async def PatchEmergencyActionMessage(self, req: EmergencyActionMessage):
        self.logger.info(f"PatchEAM: {req}")
        await asyncio.sleep(0.1)
        return req

    @handle_exceptions
    async def RetrieveEmergencyActionMessage(self, callsign: str):
        self.logger.info(f"RetrieveEAM callsign={callsign}")
        await asyncio.sleep(0.1)
        return EmergencyActionMessage(
            callsign=callsign, groupName="Alpha",
            securityStatus=EAMStatus.Green, securityCapability=EAMStatus.Green,
            preparednessStatus=EAMStatus.Green, medicalStatus=EAMStatus.Green,
            mobilityStatus=EAMStatus.Green, commsStatus=EAMStatus.Green,
            commsMethod="Radio"
        )

class EventController(Controller):
    @handle_exceptions
    async def CreateEvent(self, req: Event):
        self.logger.info(f"CreateEvent: {req}")
        await asyncio.sleep(0.1)
        return req

    @handle_exceptions
    async def DeleteEvent(self, uid: str):
        self.logger.info(f"DeleteEvent uid={uid}")
        await asyncio.sleep(0.1)
        return {"status":"deleted","uid":uid}

    @handle_exceptions
    async def ListEvent(self):
        self.logger.info("ListEvent")
        await asyncio.sleep(0.1)
        return []

    @handle_exceptions
    async def PatchEvent(self, req: Event):
        self.logger.info(f"PatchEvent: {req}")
        await asyncio.sleep(0.1)
        return req

    @handle_exceptions
    async def RetrieveEvent(self, uid: str):
        self.logger.info(f"RetrieveEvent uid={uid}")
        await asyncio.sleep(0.1)
        return Event(
            uid=int(uid), how="m-g", version=1, time=0, type="Emergency",
            stale="PT1H", start="PT0S", access="public",
            opex=0, qos=1,
            detail=Detail(emergencyActionMessage=None),
            point=Point(0,0,0,0,0)
        )
