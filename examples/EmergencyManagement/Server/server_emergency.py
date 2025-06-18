import asyncio
from reticulum_openapi.service import LXMFService
from examples.EmergencyManagement.Server.controllers_emergency import (
    EmergencyController, EventController
)
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    Event,
)


async def main():
    svc = LXMFService()
    eamc = EmergencyController()
    evc = EventController()
    svc.add_route("CreateEmergencyActionMessage", eamc.CreateEmergencyActionMessage, EmergencyActionMessage)
    svc.add_route("DeleteEmergencyActionMessage", eamc.DeleteEmergencyActionMessage)
    svc.add_route("ListEmergencyActionMessage", eamc.ListEmergencyActionMessage)
    svc.add_route("PatchEmergencyActionMessage", eamc.PatchEmergencyActionMessage, EmergencyActionMessage)
    svc.add_route("RetrieveEmergencyActionMessage", eamc.RetrieveEmergencyActionMessage)
    svc.add_route("CreateEvent", evc.CreateEvent, Event)
    svc.add_route("DeleteEvent", evc.DeleteEvent)
    svc.add_route("ListEvent", evc.ListEvent)
    svc.add_route("PatchEvent", evc.PatchEvent, Event)
    svc.add_route("RetrieveEvent", evc.RetrieveEvent)
    svc.announce()
    service_task = asyncio.create_task(svc.start())
    try:
        await asyncio.sleep(30)  # Run for 30 seconds then stop
    finally:
        await svc.stop()
        await service_task

if __name__ == "__main__":
    asyncio.run(main())
