from dataclasses import dataclass
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
