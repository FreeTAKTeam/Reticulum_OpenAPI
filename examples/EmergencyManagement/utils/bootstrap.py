"""Bootstrap utilities shared by Emergency Management examples."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from types import FrameType
from typing import Optional


def _caller_context() -> tuple[Optional[str], Optional[str]]:
    """Return the ``__package__`` and ``__file__`` for the calling module."""

    frame: Optional[FrameType]
    frame = inspect.currentframe()
    package_name: Optional[str] = None
    file_path: Optional[str] = None
    try:
        caller = frame.f_back if frame is not None else None
        if caller is not None:
            package_name = caller.f_globals.get("__package__")
            file_path = caller.f_globals.get("__file__")
    finally:
        del frame
    return package_name, file_path


def ensure_standard_library() -> None:
    """Ensure CPython standard library directories are available."""

    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    zipped = f"python{sys.version_info.major}{sys.version_info.minor}.zip"
    base_dirs = {sys.base_prefix, sys.exec_prefix, sys.prefix}
    lib_dir_names = ["lib", "Lib"]

    for base_dir in base_dirs:
        if not base_dir:
            continue

        for lib_dir_name in lib_dir_names:
            lib_dir = f"{base_dir}/{lib_dir_name}"
            candidates = [
                f"{lib_dir}/{zipped}",
                f"{lib_dir}/{version}",
                f"{lib_dir}/{version}/lib-dynload",
                f"{lib_dir}/{version}/site-packages",
                f"{lib_dir}/{version}/dist-packages",
                f"{lib_dir}/site-packages",
                f"{lib_dir}/dist-packages",
            ]

            for candidate in candidates:
                if candidate and candidate not in sys.path:
                    sys.path.append(candidate)


def ensure_project_root(package_name: Optional[str] = None, file_path: Optional[str] = None) -> None:
    """Ensure the repository root is importable when run as a script."""

    if package_name is None and file_path is None:
        detected_package, detected_file = _caller_context()
        package_name = detected_package if package_name is None else package_name
        file_path = detected_file if file_path is None else file_path

    package_value = package_name or ""
    if "." in package_value:
        return

    target_file = file_path or __file__
    project_root = Path(target_file).resolve().parents[3]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


__all__ = ["ensure_standard_library", "ensure_project_root"]
