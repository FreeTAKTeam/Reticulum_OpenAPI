"""Emergency Management example package."""

from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Server as _ServerPackage  # noqa: F401
    from . import client as _ClientPackage  # noqa: F401


def load_submodule(name: str) -> ModuleType:
    """Import a submodule from the Emergency Management package.

    Args:
        name (str): The dotted path suffix of the submodule to load.

    Returns:
        ModuleType: The imported submodule.
    """

    return import_module(f"{__name__}.{name}")


__all__ = ["load_submodule"]
