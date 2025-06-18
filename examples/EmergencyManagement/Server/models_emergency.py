from dataclasses import dataclass
from reticulum_openapi.model import BaseModel

class EAMStatus(str):
    Red = "Red"
    Yellow = "Yellow"
    Green = "Green"

@dataclass
class EmergencyActionMessage(BaseModel):
    callsign: str
    groupName: str
    securityStatus: EAMStatus
    securityCapability: EAMStatus
    preparednessStatus: EAMStatus
    medicalStatus: EAMStatus
    mobilityStatus: EAMStatus
    commsStatus: EAMStatus
    commsMethod: str

@dataclass
class Detail(BaseModel):
    emergencyActionMessage: EmergencyActionMessage

@dataclass
class Point(BaseModel):
    lat: float; lon: float; ce: float; le: float; hae: float

@dataclass
class Event(BaseModel):
    uid: int; how: str; version: int; time: int; type: str
    stale: str; start: str; access: str; opex: int; qos: int
    detail: Detail; point: Point
