"""Configuration helpers for the emergency management north API client."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


load_dotenv()

CONFIG_JSON_ENV_VAR = "NORTH_API_CONFIG_JSON"
CONFIG_PATH_ENV_VAR = "NORTH_API_CONFIG_PATH"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "client_config.json"


class NorthAPIClientSettings(BaseModel):
    """Pydantic model describing LXMF client configuration values."""

    server_identity_hash: str = Field(..., min_length=1)
    client_display_name: str = Field("EmergencyClient", min_length=1)
    request_timeout_seconds: float = Field(300.0, ge=0.0)
    lxmf_config_path: Optional[str] = None
    lxmf_storage_path: Optional[str] = None
    shared_instance_rpc_key: Optional[str] = None

    @field_validator("server_identity_hash")
    def _validate_server_identity_hash(cls, value: str) -> str:
        """Ensure the server identity hash contains hexadecimal characters."""

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("server_identity_hash cannot be empty")
        return cleaned.lower()

    @field_validator("client_display_name")
    def _validate_display_name(cls, value: str) -> str:
        """Ensure the display name is not blank."""

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("client_display_name cannot be empty")
        return cleaned

    @field_validator("lxmf_config_path", "lxmf_storage_path", mode="before")
    def _normalise_optional_paths(cls, value: Optional[str]) -> Optional[str]:
        """Return ``None`` when optional string values are empty."""

        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("shared_instance_rpc_key", mode="before")
    def _validate_shared_instance_rpc_key(
        cls, value: Optional[str]
    ) -> Optional[str]:
        """Normalise and validate optional RPC key overrides."""

        if value is None:
            return None

        cleaned = str(value).strip()
        if not cleaned:
            return None

        try:
            bytes.fromhex(cleaned)
        except ValueError as exc:
            raise ValueError(
                "shared_instance_rpc_key must be a hexadecimal string"
            ) from exc

        return cleaned.lower()


def _load_config_from_json(raw_json: str) -> Dict[str, Any]:
    """Return configuration data parsed from a raw JSON string."""

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive logging
        raise ValueError("Invalid JSON supplied via environment variable") from exc


def _load_config_from_path(path: Path) -> Dict[str, Any]:
    """Return configuration data parsed from a JSON file."""

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_config_source() -> Dict[str, Any]:
    """Return configuration data from environment or default JSON file."""

    raw_json = os.getenv(CONFIG_JSON_ENV_VAR)
    if raw_json:
        return _load_config_from_json(raw_json)

    path_override = os.getenv(CONFIG_PATH_ENV_VAR)
    config_path = Path(path_override) if path_override else DEFAULT_CONFIG_PATH
    return _load_config_from_path(config_path)


def load_config() -> NorthAPIClientSettings:
    """Create a configuration model populated with LXMF client values."""

    data = _resolve_config_source()
    return NorthAPIClientSettings(**data)


@lru_cache(maxsize=1)
def get_config() -> NorthAPIClientSettings:
    """Return a cached configuration instance for dependency injection."""

    return load_config()


__all__ = ["NorthAPIClientSettings", "get_config", "load_config"]
