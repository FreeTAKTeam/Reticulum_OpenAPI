"""Tests for the reticulum_openapi.conversion module."""

from typing import List

from examples.EmergencyManagement.Server.models_emergency import Event
from examples.EmergencyManagement.Server.models_emergency import Point
from reticulum_openapi.conversion import decode_payload
from reticulum_openapi.conversion import normalise_response
from reticulum_openapi.conversion import prepare_dataclass_payload
from reticulum_openapi.model import compress_json
from reticulum_openapi.model import dataclass_to_json_bytes
from reticulum_openapi.model import dataclass_to_msgpack


def test_decode_payload_returns_default_for_missing_lists() -> None:
    """Lists default to empty when no payload is provided."""

    decoded = decode_payload(None, List[Event])
    assert decoded == []


def test_prepare_dataclass_payload_merges_overrides() -> None:
    """Dataclass payload preparation applies overrides with type coercion."""

    payload = prepare_dataclass_payload(
        Event,
        {"type": "Exercise", "point": {"lat": 1.0, "lon": 2.0}},
        overrides={"uid": "42"},
    )
    assert isinstance(payload, Event)
    assert payload.uid == 42
    assert payload.point is not None
    assert payload.point.lat == 1.0


def test_normalise_response_converts_nested_dataclasses() -> None:
    """Normalisation flattens dataclasses into JSON-serialisable primitives."""

    point = Point(lat=3.0, lon=4.0)
    event = Event(uid=7, type="Drill", point=point)
    payload = normalise_response(event)
    assert payload == {"uid": 7, "type": "Drill", "point": {"lat": 3.0, "lon": 4.0}}


def test_decode_payload_supports_json_and_messagepack() -> None:
    """Decoding handles both MessagePack and compressed JSON payloads."""

    event = Event(uid=9, type="Alert", point=Point(lat=9, lon=10))
    msgpack_payload = dataclass_to_msgpack(event)
    json_payload = compress_json(dataclass_to_json_bytes(event))

    decoded_msgpack = decode_payload(msgpack_payload, Event)
    decoded_json = decode_payload(json_payload, Event)

    assert decoded_msgpack == decoded_json
    assert decoded_msgpack.uid == event.uid
    assert decoded_msgpack.point == event.point
