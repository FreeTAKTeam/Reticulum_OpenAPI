from dataclasses import dataclass
from typing import List, Union
from reticulum_openapi.model import dataclass_to_json, dataclass_from_json


@dataclass
class Item:
    name: str
    value: int


@dataclass
class ItemList:
    items: List[Item]


def test_serialization_roundtrip():
    item = Item(name="foo", value=42)
    data = dataclass_to_json(item)
    obj = dataclass_from_json(Item, data)
    assert obj == item


def test_list_of_items_roundtrip():
    obj = ItemList(items=[Item(name="a", value=1), Item(name="b", value=2)])
    data = dataclass_to_json(obj)
    reconstructed = dataclass_from_json(ItemList, data)
    assert reconstructed == obj


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
