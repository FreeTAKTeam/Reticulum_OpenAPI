from typing import Any
from typing import Dict
from typing import Final

from reticulum_openapi.service import LXMFService
from examples.EmergencyManagement.Server.controllers_emergency import (
    EmergencyController,
    EventController,
)
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    Event,
)


_EAM_CALLSIGN_SCHEMA: Final[Dict[str, Any]] = {
    "type": "string",
    "minLength": 1,
    "description": "Callsign identifying the emergency action message.",
}

_EVENT_IDENTIFIER_SCHEMA: Final[Dict[str, Any]] = {
    "oneOf": [
        {"type": "integer"},
        {
            "type": "string",
            "pattern": r"^-?\\d+$",
            "description": "Numeric identifier encoded as a string.",
        },
    ],
    "description": "Unique identifier for the event record.",
}


class EmergencyService(LXMFService):
    """Service with routes for the emergency management example."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("announce_app_data", "emergency_management")
        super().__init__(*args, **kwargs)

        eamc = EmergencyController()
        evc = EventController()

        self.add_route(
            "CreateEmergencyActionMessage",
            eamc.CreateEmergencyActionMessage,
            EmergencyActionMessage,
        )
        self.add_route(
            "DeleteEmergencyActionMessage",
            eamc.DeleteEmergencyActionMessage,
            payload_schema=_EAM_CALLSIGN_SCHEMA,
        )
        self.add_route("ListEmergencyActionMessage", eamc.ListEmergencyActionMessage)
        self.add_route(
            "PutEmergencyActionMessage",
            eamc.PutEmergencyActionMessage,
            EmergencyActionMessage,
        )
        self.add_route(
            "RetrieveEmergencyActionMessage",
            eamc.RetrieveEmergencyActionMessage,
            payload_schema=_EAM_CALLSIGN_SCHEMA,
        )

        self.add_route("CreateEvent", evc.CreateEvent, Event)
        self.add_route(
            "DeleteEvent",
            evc.DeleteEvent,
            payload_schema=_EVENT_IDENTIFIER_SCHEMA,
        )
        self.add_route("ListEvent", evc.ListEvent)
        self.add_route("PutEvent", evc.PutEvent, Event)
        self.add_route(
            "RetrieveEvent",
            evc.RetrieveEvent,
            payload_schema=_EVENT_IDENTIFIER_SCHEMA,
        )
