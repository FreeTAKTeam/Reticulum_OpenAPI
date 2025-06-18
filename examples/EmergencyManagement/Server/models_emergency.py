from dataclasses import dataclass
from reticulum_openapi.model import BaseModel
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, JSON

Base = declarative_base()


class EmergencyActionMessageORM(Base):
    __tablename__ = "emergency_action_messages"
    callsign = Column(String, primary_key=True)
    groupName = Column(String)
    securityStatus = Column(String)
    securityCapability = Column(String)
    preparednessStatus = Column(String)
    medicalStatus = Column(String)
    mobilityStatus = Column(String)
    commsStatus = Column(String)
    commsMethod = Column(String)


class EventORM(Base):
    __tablename__ = "events"
    uid = Column(Integer, primary_key=True)
    how = Column(String)
    version = Column(Integer)
    time = Column(Integer)
    type = Column(String)
    stale = Column(String)
    start = Column(String)
    access = Column(String)
    opex = Column(Integer)
    qos = Column(Integer)
    detail = Column(JSON)
    point = Column(JSON)


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
    __orm_model__ = EmergencyActionMessageORM


@dataclass
class Detail(BaseModel):
    emergencyActionMessage: EmergencyActionMessage


@dataclass
class Point(BaseModel):
    lat: float
    lon: float
    ce: float
    le: float
    hae: float


@dataclass
class Event(BaseModel):
    uid: int
    how: str
    version: int
    time: int
    type: str
    stale: str
    start: str
    access: str
    opex: int
    qos: int
    detail: Detail
    point: Point
    __orm_model__ = EventORM
