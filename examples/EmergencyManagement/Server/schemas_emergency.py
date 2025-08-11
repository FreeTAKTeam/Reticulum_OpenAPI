"""JSON Schemas for the EmergencyManagement example."""

EMERGENCY_ACTION_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "auth_token": {"type": "string"},
        "callsign": {"type": "string"},
        "groupName": {"type": ["string", "null"]},
        "securityStatus": {"type": ["string", "null"]},
        "securityCapability": {"type": ["string", "null"]},
        "preparednessStatus": {"type": ["string", "null"]},
        "medicalStatus": {"type": ["string", "null"]},
        "mobilityStatus": {"type": ["string", "null"]},
        "commsStatus": {"type": ["string", "null"]},
        "commsMethod": {"type": ["string", "null"]},
    },
    "required": ["auth_token", "callsign"],
}

EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "auth_token": {"type": "string"},
        "uid": {"type": "integer"},
        "how": {"type": ["string", "null"]},
        "version": {"type": ["integer", "null"]},
        "time": {"type": ["integer", "null"]},
        "type": {"type": ["string", "null"]},
        "stale": {"type": ["string", "null"]},
        "start": {"type": ["string", "null"]},
        "access": {"type": ["string", "null"]},
        "opex": {"type": ["integer", "null"]},
        "qos": {"type": ["integer", "null"]},
        "detail": {"type": ["object", "null"]},
        "point": {"type": ["object", "null"]},
    },
    "required": ["auth_token", "uid"],
}

AUTH_SCHEMA = {
    "type": "object",
    "properties": {"auth_token": {"type": "string"}},
    "required": ["auth_token"],
}

CALLSIGN_SCHEMA = {
    "type": "object",
    "properties": {
        "auth_token": {"type": "string"},
        "callsign": {"type": "string"},
    },
    "required": ["auth_token", "callsign"],
}

UID_SCHEMA = {
    "type": "object",
    "properties": {
        "auth_token": {"type": "string"},
        "uid": {"type": "integer"},
    },
    "required": ["auth_token", "uid"],
}
