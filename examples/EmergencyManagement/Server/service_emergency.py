from reticulum_openapi.service import LXMFService
from examples.EmergencyManagement.Server.controllers_emergency import (
    EmergencyController,
    EventController,
)
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    Event,
)


class EmergencyService(LXMFService):
    """Service with routes for the emergency management example."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        eamc = EmergencyController()
        evc = EventController()

        self.add_route(
            "CreateEmergencyActionMessage",
            eamc.CreateEmergencyActionMessage,
            EmergencyActionMessage,
        )
        self.add_route("DeleteEmergencyActionMessage", eamc.DeleteEmergencyActionMessage)
        self.add_route("ListEmergencyActionMessage", eamc.ListEmergencyActionMessage)
        self.add_route(
            "PutEmergencyActionMessage",
            eamc.PutEmergencyActionMessage,
            EmergencyActionMessage,
        )
        self.add_route("RetrieveEmergencyActionMessage", eamc.RetrieveEmergencyActionMessage)

        self.add_route("CreateEvent", evc.CreateEvent, Event)
        self.add_route("DeleteEvent", evc.DeleteEvent)
        self.add_route("ListEvent", evc.ListEvent)
        self.add_route("PutEvent", evc.PutEvent, Event)
        self.add_route("RetrieveEvent", evc.RetrieveEvent)
