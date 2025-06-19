from dataclasses import dataclass
from typing import Union
from reticulum_openapi.model import dataclass_to_json, dataclass_from_json


@dataclass
class Item:
    name: str
    value: int


def test_serialization_roundtrip():
    item = Item(name="foo", value=42)
    data = dataclass_to_json(item)
    obj = dataclass_from_json(Item, data)
    assert obj == item


@dataclass
class BaseVehicle:
    manufacturer: str


@dataclass
class Car(BaseVehicle):
    doors: int


@dataclass
class Bike:
    handlebar: str


Vehicle = Union[Car, Bike]


@dataclass
class TransportRecord:
    owner: str
    vehicle: Vehicle


def test_union_deserialization_root():
    data = dataclass_to_json(Car(manufacturer="Acme", doors=2))
    obj = dataclass_from_json(Vehicle, data)
    assert isinstance(obj, Car)
    assert obj.doors == 2


def test_union_deserialization_nested():
    record = TransportRecord(owner="bob", vehicle=Bike(handlebar="drop"))
    data = dataclass_to_json(record)
    obj = dataclass_from_json(TransportRecord, data)
    assert isinstance(obj.vehicle, Bike)
