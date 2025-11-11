"""Pydantic models and helpers for configuring LXMF FastAPI integrations."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


load_dotenv()


class LXMFClientSettings(BaseModel):
    """Pydantic model describing LXMF client configuration values."""

    server_identity_hash: Optional[str] = Field(default=None)
    client_display_name: str = Field("LXMFClient", min_length=1)
    request_timeout_seconds: float = Field(300.0, ge=0.0)
    lxmf_config_path: Optional[str] = None
    lxmf_storage_path: Optional[str] = None
    shared_instance_rpc_key: Optional[str] = None

    @field_validator("server_identity_hash", mode="before")
    @classmethod
    def _normalise_identity(cls, value: Optional[str]) -> Optional[str]:
        """Return a lowercase hexadecimal identity string when provided."""

        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.lower()

    @field_validator("client_display_name")
    @classmethod
    def _validate_display_name(cls, value: str) -> str:
        """Ensure the display name is not blank."""

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("client_display_name cannot be empty")
        return cleaned

    @field_validator("lxmf_config_path", "lxmf_storage_path", mode="before")
    @classmethod
    def _normalise_optional_paths(
        cls, value: Optional[str]
    ) -> Optional[str]:
        """Return ``None`` when optional string values are empty."""

        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("shared_instance_rpc_key", mode="before")
    @classmethod
    def _normalise_shared_instance_key(
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
        except ValueError as exc:  # pragma: no cover - defensive validation
            raise ValueError(
                "shared_instance_rpc_key must be a hexadecimal string"
            ) from exc

        return cleaned.lower()


def _load_config_from_json(raw_json: str) -> Dict[str, Any]:
    """Return configuration data parsed from a raw JSON string."""

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive logging
        raise ValueError("Invalid JSON supplied via environment variable") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Configuration JSON must decode to a mapping")

    return parsed


def _load_config_from_path(path: Path) -> Dict[str, Any]:
    """Return configuration data parsed from a JSON file."""

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_lxmf_client_settings(
    *,
    default_path: Optional[Path] = None,
    env_json_var: str = "LXMF_CLIENT_CONFIG_JSON",
    env_path_var: str = "LXMF_CLIENT_CONFIG_PATH",
    require_server_identity: bool = False,
) -> LXMFClientSettings:
    """Load LXMF client settings from environment variables or a JSON file.

    Args:
        default_path (Optional[Path]): Path to load when no overrides are supplied.
        env_json_var (str): Name of the environment variable containing raw JSON.
        env_path_var (str): Name of the environment variable pointing to a file.
        require_server_identity (bool): When ``True`` a missing identity raises.

    Returns:
        LXMFClientSettings: Parsed configuration model populated with LXMF values.
    """

    raw_json = os.getenv(env_json_var)
    if raw_json:
        config_data = _load_config_from_json(raw_json)
    else:
        path_override = os.getenv(env_path_var)
        if path_override:
            try:
                candidate_path = Path(path_override).expanduser()
            except (TypeError, ValueError):
                candidate_path = None
            if candidate_path is not None:
                config_data = _load_config_from_path(candidate_path)
            else:
                config_data = {}
        elif default_path is not None:
            config_data = _load_config_from_path(default_path)
        else:
            config_data = {}

    settings = LXMFClientSettings(**config_data)
    if require_server_identity and not settings.server_identity_hash:
        raise ValueError("server_identity_hash must be configured")
    return settings


def create_settings_loader(
    *,
    default_path: Optional[Path] = None,
    env_json_var: str = "LXMF_CLIENT_CONFIG_JSON",
    env_path_var: str = "LXMF_CLIENT_CONFIG_PATH",
    require_server_identity: bool = False,
) -> Callable[[], LXMFClientSettings]:
    """Return a cached callable that loads LXMF client settings."""

    @lru_cache(maxsize=1)
    def _loader() -> LXMFClientSettings:
        return load_lxmf_client_settings(
            default_path=default_path,
            env_json_var=env_json_var,
            env_path_var=env_path_var,
            require_server_identity=require_server_identity,
        )

    return _loader


__all__ = [
    "LXMFClientSettings",
    "create_settings_loader",
    "load_lxmf_client_settings",
]
