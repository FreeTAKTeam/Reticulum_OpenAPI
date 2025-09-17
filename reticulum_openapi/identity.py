"""Utilities for loading persistent Reticulum identities."""

from __future__ import annotations

import os
from typing import Optional

import RNS


def _resolve_config_directory(config_path: Optional[str]) -> Optional[str]:
    """Determine the configuration directory that should contain the identity file.

    Args:
        config_path (Optional[str]): Explicit configuration directory or file path.

    Returns:
        Optional[str]: Directory path expected to hold the ``identity`` file.
    """
    candidates = []
    if config_path:
        expanded = os.path.abspath(os.path.expanduser(config_path))
        candidates.append(expanded)
        parent = os.path.dirname(expanded)
        if parent and parent != expanded:
            candidates.append(parent)
    reticulum_dir = getattr(RNS.Reticulum, "configdir", None)
    if reticulum_dir:
        candidates.append(os.path.abspath(os.path.expanduser(reticulum_dir)))
    ordered = []
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        ordered.append(candidate)
    for candidate in ordered:
        if os.path.isdir(candidate):
            return candidate
    return ordered[0] if ordered else None


def load_or_create_identity(config_path: Optional[str] = None) -> RNS.Identity:
    """Load or create the Reticulum identity located in the configuration directory.

    Args:
        config_path (Optional[str]): Explicit configuration directory or config file
            path. Defaults to ``None`` to rely on ``RNS.Reticulum.configdir``.

    Returns:
        RNS.Identity: The loaded or newly created identity instance.
    """
    config_dir = _resolve_config_directory(config_path)
    identity_path = os.path.join(config_dir, "identity") if config_dir else None
    identity = None
    loader = getattr(RNS.Identity, "from_file", None)
    if identity_path and callable(loader) and os.path.isfile(identity_path):
        try:
            identity = loader(identity_path)
        except Exception as exc:  # pragma: no cover - defensive logging
            RNS.log(
                f"Failed to load Reticulum identity from {identity_path}: {exc}",
                RNS.LOG_WARNING,
            )
            identity = None
        if identity is None:
            RNS.log(
                f"Stored Reticulum identity at {identity_path} was invalid; generating a new one.",
                RNS.LOG_WARNING,
            )
    if identity is not None:
        return identity
    identity = RNS.Identity()
    if identity_path and hasattr(identity, "to_file"):
        directory = os.path.dirname(identity_path)
        try:
            if directory:
                os.makedirs(directory, exist_ok=True)
            identity.to_file(identity_path)
        except Exception as exc:  # pragma: no cover - defensive logging
            RNS.log(
                f"Could not persist Reticulum identity to {identity_path}: {exc}",
                RNS.LOG_WARNING,
            )
    return identity
