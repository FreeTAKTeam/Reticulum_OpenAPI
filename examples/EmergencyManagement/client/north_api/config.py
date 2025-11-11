"""Configuration helpers for the emergency management north API client."""

from __future__ import annotations

from pathlib import Path

from reticulum_openapi.integrations.fastapi import LXMFClientSettings
from reticulum_openapi.integrations.fastapi import create_settings_loader
from reticulum_openapi.integrations.fastapi import load_lxmf_client_settings


CONFIG_JSON_ENV_VAR = "NORTH_API_CONFIG_JSON"
CONFIG_PATH_ENV_VAR = "NORTH_API_CONFIG_PATH"
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "client_config.json"
)

NorthAPIClientSettings = LXMFClientSettings

_SETTINGS_LOADER = create_settings_loader(
    default_path=DEFAULT_CONFIG_PATH,
    env_json_var=CONFIG_JSON_ENV_VAR,
    env_path_var=CONFIG_PATH_ENV_VAR,
    require_server_identity=True,
)


def load_config() -> NorthAPIClientSettings:
    """Create a configuration model populated with LXMF client values."""

    return load_lxmf_client_settings(
        default_path=DEFAULT_CONFIG_PATH,
        env_json_var=CONFIG_JSON_ENV_VAR,
        env_path_var=CONFIG_PATH_ENV_VAR,
        require_server_identity=True,
    )


get_config = _SETTINGS_LOADER


__all__ = ["NorthAPIClientSettings", "get_config", "load_config"]
