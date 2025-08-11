from reticulum_openapi.service import LXMFService
from examples.EmergencyManagement.Server.controllers_emergency import (
    EmergencyController,
    EventController,
)
from examples.EmergencyManagement.Server.schemas_emergency import (
    AUTH_SCHEMA,
    CALLSIGN_SCHEMA,
    EMERGENCY_ACTION_MESSAGE_SCHEMA,
    EVENT_SCHEMA,
    UID_SCHEMA,
)


class EmergencyService(LXMFService):
    """Service with routes for the emergency management example."""

    def __init__(self, *args, auth_token: str | None = None, **kwargs):
        super().__init__(*args, auth_token=auth_token, **kwargs)

        eamc = EmergencyController()
        evc = EventController()

        self.add_route(
            "CreateEmergencyActionMessage",
            eamc.CreateEmergencyActionMessage,
            payload_schema=EMERGENCY_ACTION_MESSAGE_SCHEMA,
        )
        self.add_route(
            "DeleteEmergencyActionMessage",
            eamc.DeleteEmergencyActionMessage,
            payload_schema=CALLSIGN_SCHEMA,
        )
        self.add_route(
            "ListEmergencyActionMessage",
            eamc.ListEmergencyActionMessage,
            payload_schema=AUTH_SCHEMA,
        )
        self.add_route(
            "PutEmergencyActionMessage",
            eamc.PutEmergencyActionMessage,
            payload_schema=EMERGENCY_ACTION_MESSAGE_SCHEMA,
        )
        self.add_route(
            "RetrieveEmergencyActionMessage",
            eamc.RetrieveEmergencyActionMessage,
            payload_schema=CALLSIGN_SCHEMA,
        )

        self.add_route(
            "CreateEvent",
            evc.CreateEvent,
            payload_schema=EVENT_SCHEMA,
        )
        self.add_route(
            "DeleteEvent",
            evc.DeleteEvent,
            payload_schema=UID_SCHEMA,
        )
        self.add_route(
            "ListEvent",
            evc.ListEvent,
            payload_schema=AUTH_SCHEMA,
        )
        self.add_route(
            "PutEvent",
            evc.PutEvent,
            payload_schema=EVENT_SCHEMA,
        )
        self.add_route(
            "RetrieveEvent",
            evc.RetrieveEvent,
            payload_schema=UID_SCHEMA,
        )
