"""Helpers for reporting Reticulum interface status."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import RNS
from RNS.Interfaces import Interface as RNSInterface


def _resolve_interface_mode_name(mode: Optional[int]) -> Optional[str]:
    """Return a descriptive name for a Reticulum interface mode."""

    if mode is None:
        return None
    mapping = {
        RNSInterface.Interface.MODE_FULL: "full",
        RNSInterface.Interface.MODE_ACCESS_POINT: "access_point",
        RNSInterface.Interface.MODE_POINT_TO_POINT: "point_to_point",
        RNSInterface.Interface.MODE_ROAMING: "roaming",
    }
    return mapping.get(mode, str(mode))


def _resolve_interface_name(interface: Any, index: int) -> str:
    """Return a human readable name for a Reticulum interface."""

    name_value = getattr(interface, "name", None)
    if isinstance(name_value, str) and name_value.strip():
        return name_value.strip()
    return f"Interface-{index}"


def _coerce_optional_int(value: Any) -> Optional[int]:
    """Return an integer value when possible."""

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return None


def gather_interface_status() -> List[Dict[str, Any]]:
    """Return status metadata for all configured Reticulum interfaces."""

    statuses: List[Dict[str, Any]] = []
    for index, interface in enumerate(RNS.Transport.interfaces):
        mode_value = getattr(interface, "mode", None)
        bitrate_value = _coerce_optional_int(getattr(interface, "bitrate", None))
        statuses.append(
            {
                "id": f"{type(interface).__name__}:{index}",
                "name": _resolve_interface_name(interface, index),
                "type": type(interface).__name__,
                "online": bool(getattr(interface, "online", False)),
                "mode": _resolve_interface_mode_name(mode_value),
                "bitrate": bitrate_value,
            }
        )
    return statuses
