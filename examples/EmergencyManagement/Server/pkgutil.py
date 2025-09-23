"""Bootstrap module to expose the standard library ``pkgutil`` when sys.path is restricted."""

import sys


def _load_stdlib_pkgutil():
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidate_templates = [
        "{base}/{lib}/{version}/pkgutil.py",
        "{base}/{lib}/pkgutil.py",
    ]

    for base_dir in {sys.base_prefix, sys.exec_prefix, sys.prefix}:
        if not base_dir:
            continue

        for lib_dir in ("lib", "Lib"):
            for template in candidate_templates:
                candidate = template.format(
                    base=base_dir,
                    lib=lib_dir,
                    version=version,
                )

                try:
                    with open(candidate, "r", encoding="utf-8") as handle:
                        source = handle.read()
                except (FileNotFoundError, OSError):
                    continue

                module = type(sys)("pkgutil")
                module.__file__ = candidate
                exec(compile(source, candidate, "exec"), module.__dict__)
                return module

    raise ModuleNotFoundError("Unable to locate standard library pkgutil")


_real_pkgutil = _load_stdlib_pkgutil()

sys.modules.setdefault("pkgutil", _real_pkgutil)

globals().update(_real_pkgutil.__dict__)

__all__ = getattr(_real_pkgutil, "__all__", [])
