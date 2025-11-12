"""Compatibility helpers for multiprocessing start method quirks.

Some third-party modules (for example LXMF/LXStamper) unconditionally call
``multiprocessing.set_start_method("fork")`` on import when running on Linux.
If another library (such as uvicorn's reload subsystem) has already selected
and locked a different start method, Python raises ``RuntimeError: context has
already been set`` which prevents the application from starting.

To keep the gateway usable we intercept repeated ``set_start_method`` calls and
silently ignore attempts to change the method after it has been initialised.
"""

from __future__ import annotations

import logging
import multiprocessing
from typing import Any

_LOGGER = logging.getLogger(__name__)

_ORIGINAL_SET_START_METHOD = multiprocessing.set_start_method


def _safe_set_start_method(method: str, /, *args: Any, **kwargs: Any) -> Any:
    """Wrap ``multiprocessing.set_start_method`` with duplicate protection."""

    try:
        return _ORIGINAL_SET_START_METHOD(method, *args, **kwargs)
    except RuntimeError as exc:  # pragma: no cover - defensive guard
        message = str(exc)
        if "context has already been set" not in message:
            raise

        existing = "unknown"
        try:
            existing = multiprocessing.get_start_method(allow_none=True)
        except TypeError:
            # Python versions <3.8 do not support allow_none. Best effort.
            try:
                existing = multiprocessing.get_start_method()
            except Exception:  # pragma: no cover - diagnostic only
                pass

        _LOGGER.debug(
            "multiprocessing start method already %s; ignoring request to set %s",
            existing,
            method,
        )
        return None


multiprocessing.set_start_method = _safe_set_start_method  # type: ignore[assignment]
