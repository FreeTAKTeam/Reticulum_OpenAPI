"""Utilities for converting LXMF payloads to and from Python types."""

from __future__ import annotations

import inspect
import json
import sys
import zlib
from dataclasses import fields
from dataclasses import is_dataclass
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import MutableMapping
from typing import MutableSequence
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union
from typing import get_args
from typing import get_origin
from typing import get_type_hints

from .codec_msgpack import CodecError
from .codec_msgpack import decode_payload_bytes


T = TypeVar("T")
_JSON_PREFIX = 0x78
_SENTINEL = object()


def _type_allows_none(expected_type: Any) -> bool:
    """Return ``True`` when ``expected_type`` permits ``None`` values.

    Args:
        expected_type (Any): Typing annotation to evaluate.

    Returns:
        bool: ``True`` when ``None`` is an accepted value for ``expected_type``.
    """

    origin = get_origin(expected_type)
    if origin is Union:
        return any(
            arg is type(None) or _type_allows_none(arg)
            for arg in get_args(expected_type)
        )
    return expected_type in {Any, object, type(None)}


def _default_for_type(expected_type: Any) -> Any:
    """Return the default fallback for ``expected_type`` or ``_SENTINEL``.

    Args:
        expected_type (Any): Typing annotation to inspect for default behaviour.

    Returns:
        Any: Default value compatible with ``expected_type`` when available.
    """

    origin = get_origin(expected_type)
    if origin in {list, List, Sequence, MutableSequence, tuple, Tuple, set, frozenset}:
        return []
    if origin is Union:
        args = get_args(expected_type)
        if any(arg is type(None) for arg in args):
            return None
    if expected_type in {
        list,
        List,
        Sequence,
        MutableSequence,
        tuple,
        Tuple,
        set,
        frozenset,
    }:
        return []
    if expected_type in {dict, Dict, Mapping, MutableMapping}:
        return {}
    if expected_type in {Any, object}:
        return None
    return _SENTINEL


def convert_value(expected_type: Any, value: Any) -> Any:
    """Recursively convert ``value`` into the supplied ``expected_type``.

    Args:
        expected_type (Any): Dataclass, typing annotation, or primitive type that describes
            the desired shape.
        value (Any): JSON-compatible payload to convert.

    Returns:
        Any: Converted value matching ``expected_type``.

    Raises:
        TypeError: If ``value`` cannot be converted to ``expected_type``.
        ValueError: When conversion fails due to semantic mismatches, such as invalid
            literal choices or failed numeric parsing.
    """

    if expected_type in {Any, object}:
        return value

    if value is None:
        if _type_allows_none(expected_type):
            return None
        default = _default_for_type(expected_type)
        if default is not _SENTINEL:
            return default
        raise TypeError(f"Value None is not valid for type {expected_type}")

    origin = get_origin(expected_type)
    if origin is not None:
        if origin is Union:
            last_error: Optional[Exception] = None
            for arg in get_args(expected_type):
                if arg is type(None):
                    if value is None:
                        return None
                    continue
                try:
                    return convert_value(arg, value)
                except (TypeError, ValueError) as exc:
                    last_error = exc
                    continue
            if last_error is not None:
                raise ValueError(
                    f"Unable to match value {value!r} to type {expected_type}"
                ) from last_error
            raise ValueError(f"Unable to match value {value!r} to type {expected_type}")
        if origin is tuple or origin is Tuple:
            item_types = list(get_args(expected_type))
            if not isinstance(value, (list, tuple)):
                raise TypeError(f"Expected tuple for type {expected_type}")
            if not item_types:
                return tuple(value)
            if len(item_types) == 2 and item_types[1] is Ellipsis:
                item_type = item_types[0]
                return tuple(convert_value(item_type, item) for item in value)
            if len(value) != len(item_types):
                raise ValueError(
                    f"Expected {len(item_types)} items for tuple {expected_type}, got {len(value)}"
                )
            return tuple(convert_value(t, item) for t, item in zip(item_types, value))
        if origin in {list, List, Sequence, MutableSequence, set, frozenset}:
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                raise TypeError(f"Expected list for type {expected_type}")
            item_types = get_args(expected_type)
            item_type = item_types[0] if item_types else Any
            converted = [convert_value(item_type, item) for item in value]
            if origin in {set, frozenset}:
                return set(converted)
            return list(converted)
        if origin in {dict, Dict, Mapping, MutableMapping}:
            if not isinstance(value, Mapping):
                raise TypeError(f"Expected mapping for type {expected_type}")
            key_type, value_type = (Any, Any)
            args = get_args(expected_type)
            if len(args) == 2:
                key_type, value_type = args
            result: Dict[Any, Any] = {}
            for raw_key, raw_value in value.items():
                key = (
                    convert_value(key_type, raw_key)
                    if key_type not in {Any, object}
                    else raw_key
                )
                result[str(key)] = convert_value(value_type, raw_value)
            return result
        from typing import Literal  # Local import to avoid circular typing deps

        if origin is Literal:
            allowed = get_args(expected_type)
            if value in allowed:
                return value
            raise ValueError(
                f"Value {value!r} is not permitted for literal {expected_type}"
            )
        # typing.Annotated compatibility
        if getattr(origin, "__qualname__", None) == "Annotated":
            annotated_args = get_args(expected_type)
            if not annotated_args:
                return value
            return convert_value(annotated_args[0], value)

    if inspect.isclass(expected_type):
        if issubclass(expected_type, Enum):
            if isinstance(value, expected_type):
                return value
            try:
                return expected_type(value)
            except ValueError as exc:
                raise ValueError(
                    f"Value {value!r} is not valid for enum {expected_type.__name__}"
                ) from exc
        if expected_type is str:
            if isinstance(value, str):
                return value
            if isinstance(value, (bytes, bytearray, memoryview)):
                try:
                    return bytes(value).decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ValueError("Unable to decode bytes to string") from exc
            raise TypeError(f"Expected string for type {expected_type}")
        if expected_type is int:
            if isinstance(value, bool):
                raise TypeError("Boolean value is not a valid integer")
            if isinstance(value, int):
                return value
            if isinstance(value, float) and value.is_integer():
                return int(value)
            if isinstance(value, str):
                try:
                    return int(value.strip(), 10)
                except ValueError as exc:
                    raise ValueError(f"Unable to convert {value!r} to int") from exc
            raise TypeError(f"Expected integer for type {expected_type}")
        if expected_type is float:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value.strip())
                except ValueError as exc:
                    raise ValueError(f"Unable to convert {value!r} to float") from exc
            raise TypeError(f"Expected float for type {expected_type}")
        if expected_type is bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes", "on"}:
                    return True
                if lowered in {"false", "0", "no", "off"}:
                    return False
            raise TypeError(f"Expected boolean for type {expected_type}")
        if is_dataclass(expected_type):
            if isinstance(value, expected_type):
                return value
            if not isinstance(value, Mapping):
                raise TypeError(
                    f"Expected object for dataclass {expected_type.__name__}"
                )
            return build_dataclass(expected_type, value)

    return value


def build_dataclass(cls: Type[T], data: Mapping[str, Any]) -> T:
    """Construct ``cls`` from ``data`` applying type conversions.

    Args:
        cls (Type[T]): Dataclass type to instantiate.
        data (Mapping[str, Any]): Mapping containing payload values.

    Returns:
        T: Instance of ``cls`` populated with converted values.

    Raises:
        TypeError: If ``data`` is not a mapping type.
    """

    if not isinstance(data, Mapping):
        raise TypeError("Request payload must be a mapping")

    module = sys.modules.get(cls.__module__)
    globalns = vars(module) if module is not None else {}
    type_hints = get_type_hints(cls, globalns=globalns)

    kwargs: Dict[str, Any] = {}
    for field in fields(cls):
        if field.name not in data:
            continue
        expected_type = type_hints.get(field.name, field.type)
        kwargs[field.name] = convert_value(expected_type, data[field.name])
    return cls(**kwargs)


def _attempt_json_decode(payload: bytes) -> Any:
    """Return decoded JSON when ``payload`` appears to be compressed JSON.

    Args:
        payload (bytes): Raw payload returned by LXMF.

    Returns:
        Any: Decoded JSON data or ``_SENTINEL`` when decoding fails.
    """

    if len(payload) < 2 or payload[0] != _JSON_PREFIX:
        return _SENTINEL
    try:
        json_bytes = zlib.decompress(payload)
    except zlib.error:
        json_bytes = payload
    try:
        text = json_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return _SENTINEL
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _SENTINEL


def decode_payload(payload: Optional[bytes], expected_type: Any) -> Any:
    """Decode ``payload`` into ``expected_type`` using JSON or MessagePack heuristics.

    Args:
        payload (Optional[bytes]): Raw payload to decode.
        expected_type (Any): Dataclass or typing annotation describing the desired structure.

    Returns:
        Any: Decoded payload coerced into ``expected_type``.

    Raises:
        ValueError: If the payload cannot be decoded or violates ``expected_type``.
    """

    if not payload:
        default = _default_for_type(expected_type)
        if default is not _SENTINEL:
            return default
        raise ValueError("Response payload is required")

    json_candidate = _attempt_json_decode(payload)
    data: Any
    if json_candidate is not _SENTINEL:
        data = json_candidate
    else:
        try:
            data = decode_payload_bytes(payload)
        except CodecError as exc:
            raise ValueError("Unable to decode payload bytes") from exc

    if data is None:
        default = _default_for_type(expected_type)
        if default is not _SENTINEL:
            return default
        raise ValueError("Decoded payload cannot be null")

    return convert_value(expected_type, data)


def prepare_dataclass_payload(
    expected_type: Optional[Any],
    payload: Optional[Mapping[str, Any]] = None,
    *,
    overrides: Optional[Mapping[str, Any]] = None,
) -> Any:
    """Build a dataclass or primitive payload for LXMF commands.

    Args:
        expected_type (Optional[Any]): Dataclass or typing annotation describing the payload.
        payload (Optional[Mapping[str, Any]]): Base payload values supplied by the caller.
        overrides (Optional[Mapping[str, Any]]): Additional values that override ``payload``.

    Returns:
        Any: Dataclass instance or primitive structure prepared for transport.
    """

    if expected_type is None:
        if payload is not None:
            return payload
        if overrides is not None:
            if len(overrides) == 1:
                return next(iter(overrides.values()))
            return dict(overrides)
        return None

    combined: Dict[str, Any] = {}
    if payload is not None:
        combined.update(payload)
    if overrides is not None:
        combined.update(overrides)

    if is_dataclass(expected_type):
        return build_dataclass(expected_type, combined)
    return convert_value(expected_type, combined)


def normalise_response(value: Any) -> Any:
    """Convert dataclasses, enums, and iterables into JSON-compatible primitives.

    Args:
        value (Any): Object returned from LXMF or service handlers.

    Returns:
        Any: JSON-serialisable representation of ``value``.
    """

    if value is None:
        return None
    if is_dataclass(value):
        result: Dict[str, Any] = {}
        for field in fields(value):
            field_value = getattr(value, field.name)
            if field_value is None:
                continue
            result[field.name] = normalise_response(field_value)
        return result
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): normalise_response(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [normalise_response(item) for item in value]
    return value


__all__ = [
    "convert_value",
    "build_dataclass",
    "decode_payload",
    "prepare_dataclass_payload",
    "normalise_response",
]
