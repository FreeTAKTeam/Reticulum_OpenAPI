"""Reticulum OpenAPI package."""

import sys as _sys

from . import logging_config as _logging_config
from .announcer import DestinationAnnouncer
from .controller import APIException
from .controller import Controller
from .controller import handle_exceptions
from .conversion import build_dataclass
from .conversion import convert_value
from .conversion import decode_payload
from .conversion import normalise_response
from .conversion import prepare_dataclass_payload
from .link_client import LinkClient
from .link_service import LinkService
from .model import BaseModel
from .model import compress_json
from .model import dataclass_from_json
from .model import dataclass_from_msgpack
from .model import dataclass_to_json
from .model import dataclass_to_json_bytes
from .model import dataclass_to_msgpack
from .service import LXMFService
from .status import StatusCode

_sys.modules[__name__ + ".logging"] = _logging_config

__all__ = [
    "Controller",
    "APIException",
    "handle_exceptions",
    "convert_value",
    "build_dataclass",
    "decode_payload",
    "prepare_dataclass_payload",
    "normalise_response",
    "BaseModel",
    "compress_json",
    "dataclass_from_json",
    "dataclass_from_msgpack",
    "dataclass_to_json",
    "dataclass_to_json_bytes",
    "dataclass_to_msgpack",
    "DestinationAnnouncer",
    "LinkClient",
    "LinkService",
    "LXMFService",
    "StatusCode",
]
