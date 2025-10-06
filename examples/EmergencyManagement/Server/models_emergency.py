from dataclasses import dataclass

from typing import Any, Literal, Optional, Union

from reticulum_openapi.model import BaseModel
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, JSON

Base = declarative_base()

# Am I correct in understanding that the Dataclass' are meant as a sort of DTO
# to avoid coupling the DB to the internal domain representation?


class EmergencyActionMessageORM(Base):
    __tablename__ = "emergency_action_messages"
    callsign = Column(String, primary_key=True)
    groupName = Column(String, nullable=True)
    securityStatus = Column(String, nullable=True)
    securityCapability = Column(String, nullable=True)
    preparednessStatus = Column(String, nullable=True)
    medicalStatus = Column(String, nullable=True)
    mobilityStatus = Column(String, nullable=True)
    commsStatus = Column(String, nullable=True)
    commsMethod = Column(String, nullable=True)


class EventORM(Base):
    __tablename__ = "events"
    uid = Column(Integer, primary_key=True)
    how = Column(String, nullable=True)
    version = Column(Integer, nullable=True)
    time = Column(Integer, nullable=True)
    type = Column(String, nullable=True)
    stale = Column(String, nullable=True)
    start = Column(String, nullable=True)
    access = Column(String, nullable=True)
    opex = Column(Integer, nullable=True)
    qos = Column(Integer, nullable=True)
    detail = Column(JSON, nullable=True)
    point = Column(JSON, nullable=True)


class EAMStatus(str):
    Red = "Red"
    Yellow = "Yellow"
    Green = "Green"


@dataclass
class EmergencyActionMessage(BaseModel):
    callsign: str
    groupName: Optional[str] = None
    securityStatus: Optional[EAMStatus] = None
    securityCapability: Optional[EAMStatus] = None
    preparednessStatus: Optional[EAMStatus] = None
    medicalStatus: Optional[EAMStatus] = None
    mobilityStatus: Optional[EAMStatus] = None
    commsStatus: Optional[EAMStatus] = None
    commsMethod: Optional[str] = None
    __orm_model__ = EmergencyActionMessageORM


@dataclass
class Detail(BaseModel):
    emergencyActionMessage: Optional[EmergencyActionMessage] = None


@dataclass
class Point(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    ce: Optional[float] = None
    le: Optional[float] = None
    hae: Optional[float] = None


@dataclass
class Event(BaseModel):
    uid: int
    how: Optional[str] = None
    version: Optional[int] = None
    time: Optional[int] = None
    type: Optional[str] = None
    stale: Optional[str] = None
    start: Optional[str] = None
    access: Optional[str] = None
    opex: Optional[int] = None
    qos: Optional[int] = None
    detail: Optional[Detail] = None
    point: Optional[Point] = None
    __orm_model__ = EventORM


# --- Additional example models demonstrating allOf/oneOf/anyOf ---


@dataclass
class BaseVehicle(BaseModel):
    manufacturer: str


@dataclass
class Car(BaseVehicle):
    doors: int


@dataclass
class Bike(BaseModel):
    handlebar: str


Vehicle = Union[Car, Bike]


@dataclass
class TransportRecord(BaseModel):
    owner: str
    vehicle: Vehicle


@dataclass
class DeleteEmergencyActionMessageResult(BaseModel):
    status: Literal["deleted", "not_found"]
    callsign: str


@dataclass
class DeleteEventResult(BaseModel):
    status: Literal["deleted", "not_found"]
    uid: int


@dataclass
class NotificationMessage(BaseModel):
    title: str
    payload: Optional[Any] = None
    payload_raw: Optional[str] = None
