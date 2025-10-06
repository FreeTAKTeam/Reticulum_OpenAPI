"""Dataclasses and ORM models for the Emergency Management example."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Dict, Literal, Optional, Union

from reticulum_openapi.model import BaseModel
from sqlalchemy import Column, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import declarative_base, relationship

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
    detail_payload = Column("detail", JSON, nullable=True)
    point_payload = Column("point", JSON, nullable=True)

    detail = relationship(
        "EventDetailORM",
        uselist=False,
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    point = relationship(
        "EventPointORM",
        uselist=False,
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class EventDetailORM(Base):
    __tablename__ = "event_details"
    event_uid = Column(
        Integer,
        ForeignKey("events.uid", ondelete="CASCADE"),
        primary_key=True,
    )
    emergencyActionMessage = Column(JSON, nullable=True)

    event = relationship("EventORM", back_populates="detail", uselist=False)


class EventPointORM(Base):
    __tablename__ = "event_points"
    event_uid = Column(
        Integer,
        ForeignKey("events.uid", ondelete="CASCADE"),
        primary_key=True,
    )
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    ce = Column(Float, nullable=True)
    le = Column(Float, nullable=True)
    hae = Column(Float, nullable=True)

    event = relationship("EventORM", back_populates="point", uselist=False)


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
    __orm_model__ = EventDetailORM

    @staticmethod
    def _maybe_load_mapping(value: Any) -> Optional[Dict[str, Any]]:
        """Return ``value`` as a mapping when possible."""

        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return None
            if isinstance(decoded, dict):
                return decoded
            return None
        return None

    @staticmethod
    def _coerce_emergency_action_message(
        value: Any,
    ) -> Optional[EmergencyActionMessage]:
        """Convert ``value`` into an :class:`EmergencyActionMessage`."""

        if value is None:
            return None
        if isinstance(value, EmergencyActionMessage):
            return value
        if isinstance(value, dict):
            return EmergencyActionMessage(**value)
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return None
            if isinstance(decoded, dict):
                return EmergencyActionMessage(**decoded)
        return None

    @classmethod
    def from_mapping(cls, data: Any) -> Optional["Detail"]:
        """Return a dataclass instance constructed from ``data``."""

        if data is None:
            return None
        if isinstance(data, cls):
            return data
        if isinstance(data, EmergencyActionMessage):
            return cls(emergencyActionMessage=data)
        mapping = cls._maybe_load_mapping(data)
        if mapping is None:
            return None
        payload = cls._coerce_emergency_action_message(
            mapping.get("emergencyActionMessage")
        )
        return cls(emergencyActionMessage=payload)

    @classmethod
    def from_orm(cls, orm_obj: EventDetailORM) -> "Detail":
        """Construct from an ORM payload."""

        mapping: Dict[str, Any] = {
            "emergencyActionMessage": getattr(orm_obj, "emergencyActionMessage"),
        }
        instance = cls.from_mapping(mapping)
        return instance if instance is not None else cls(emergencyActionMessage=None)

    def to_record(self) -> Dict[str, Any]:
        """Return a serialisable mapping for persistence."""

        payload = None
        if isinstance(self.emergencyActionMessage, EmergencyActionMessage):
            payload = asdict(self.emergencyActionMessage)
        return {"emergencyActionMessage": payload}

    def to_orm(self) -> EventDetailORM:
        """Return the ORM payload associated with this dataclass."""

        record = self.to_record()
        return self.__orm_model__(
            emergencyActionMessage=record.get("emergencyActionMessage")
        )


@dataclass
class Point(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    ce: Optional[float] = None
    le: Optional[float] = None
    hae: Optional[float] = None
    __orm_model__ = EventPointORM

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        """Convert ``value`` into a ``float`` when possible."""

        if value is None:
            return None
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    @classmethod
    def from_mapping(cls, data: Any) -> Optional["Point"]:
        """Return a dataclass instance constructed from ``data``."""

        if data is None:
            return None
        if isinstance(data, cls):
            return data
        if isinstance(data, str):
            try:
                decoded = json.loads(data)
            except json.JSONDecodeError:
                return None
            if isinstance(decoded, dict):
                data = decoded
            else:
                return None
        if not isinstance(data, dict):
            return None
        return cls(
            lat=cls._coerce_float(data.get("lat")),
            lon=cls._coerce_float(data.get("lon")),
            ce=cls._coerce_float(data.get("ce")),
            le=cls._coerce_float(data.get("le")),
            hae=cls._coerce_float(data.get("hae")),
        )

    @classmethod
    def from_orm(cls, orm_obj: EventPointORM) -> "Point":
        """Construct from an ORM payload."""

        return cls(
            lat=cls._coerce_float(getattr(orm_obj, "lat", None)),
            lon=cls._coerce_float(getattr(orm_obj, "lon", None)),
            ce=cls._coerce_float(getattr(orm_obj, "ce", None)),
            le=cls._coerce_float(getattr(orm_obj, "le", None)),
            hae=cls._coerce_float(getattr(orm_obj, "hae", None)),
        )

    def to_record(self) -> Dict[str, Optional[float]]:
        """Return a serialisable mapping for persistence."""

        return {
            "lat": self.lat,
            "lon": self.lon,
            "ce": self.ce,
            "le": self.le,
            "hae": self.hae,
        }

    def to_orm(self) -> EventPointORM:
        """Return the ORM payload associated with this dataclass."""

        return self.__orm_model__(**self.to_record())


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

    @staticmethod
    def _normalise_detail(raw_detail: Any) -> Optional[Detail]:
        """Return a :class:`Detail` instance built from ``raw_detail``."""

        return Detail.from_mapping(raw_detail)

    @staticmethod
    def _normalise_point(raw_point: Any) -> Optional[Point]:
        """Return a :class:`Point` instance built from ``raw_point``."""

        return Point.from_mapping(raw_point)

    @classmethod
    async def create(cls, session, **kwargs) -> "Event":
        raw_detail = kwargs.pop("detail", None)
        raw_point = kwargs.pop("point", None)

        detail_obj = cls._normalise_detail(raw_detail)
        point_obj = cls._normalise_point(raw_point)

        orm_obj = cls.__orm_model__(**kwargs)

        if detail_obj is not None:
            orm_obj.detail = detail_obj.to_orm()
            orm_obj.detail_payload = detail_obj.to_record()
        else:
            orm_obj.detail_payload = raw_detail

        if point_obj is not None:
            orm_obj.point = point_obj.to_orm()
            orm_obj.point_payload = point_obj.to_record()
        else:
            orm_obj.point_payload = raw_point

        session.add(orm_obj)
        await session.commit()
        await session.refresh(orm_obj)
        return cls.from_orm(orm_obj)

    @classmethod
    async def update(cls, session, id_, **kwargs) -> Optional["Event"]:
        raw_detail = kwargs.pop("detail", None)
        raw_point = kwargs.pop("point", None)

        orm_obj = await session.get(cls.__orm_model__, id_)
        if orm_obj is None:
            return None

        for attr, value in kwargs.items():
            setattr(orm_obj, attr, value)

        if raw_detail is not None:
            detail_obj = cls._normalise_detail(raw_detail)
            if detail_obj is None:
                orm_obj.detail = None
            else:
                if orm_obj.detail is None:
                    orm_obj.detail = detail_obj.to_orm()
                else:
                    orm_obj.detail.emergencyActionMessage = detail_obj.to_record().get(
                        "emergencyActionMessage"
                    )
            orm_obj.detail_payload = (
                detail_obj.to_record() if detail_obj is not None else raw_detail
            )

        if raw_point is not None:
            point_obj = cls._normalise_point(raw_point)
            if point_obj is None:
                orm_obj.point = None
            else:
                if orm_obj.point is None:
                    orm_obj.point = point_obj.to_orm()
                else:
                    for attr, value in point_obj.to_record().items():
                        setattr(orm_obj.point, attr, value)
            orm_obj.point_payload = (
                point_obj.to_record() if point_obj is not None else raw_point
            )

        session.add(orm_obj)
        await session.commit()
        await session.refresh(orm_obj)
        return cls.from_orm(orm_obj)

    @classmethod
    def from_orm(cls, orm_obj: EventORM) -> "Event":
        """Construct an :class:`Event` dataclass from an ORM instance."""

        detail: Optional[Detail] = None
        if getattr(orm_obj, "detail", None) is not None:
            detail = Detail.from_orm(orm_obj.detail)
        elif getattr(orm_obj, "detail_payload", None) is not None:
            detail = Detail.from_mapping(orm_obj.detail_payload)

        point: Optional[Point] = None
        if getattr(orm_obj, "point", None) is not None:
            point = Point.from_orm(orm_obj.point)
        elif getattr(orm_obj, "point_payload", None) is not None:
            point = Point.from_mapping(orm_obj.point_payload)

        return cls(
            uid=orm_obj.uid,
            how=orm_obj.how,
            version=orm_obj.version,
            time=orm_obj.time,
            type=orm_obj.type,
            stale=orm_obj.stale,
            start=orm_obj.start,
            access=orm_obj.access,
            opex=orm_obj.opex,
            qos=orm_obj.qos,
            detail=detail,
            point=point,
        )


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
