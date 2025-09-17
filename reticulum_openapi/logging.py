"""Shared logging configuration for the ``reticulum_openapi`` package."""

from __future__ import annotations

import logging as _logging
from typing import Iterable

PACKAGE_LOGGER_NAME = "reticulum_openapi"
_DEFAULT_LOG_LEVEL = _logging.INFO
_HANDLER_NAME = "reticulum_openapi.stream"
_LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"


def _handler_exists(handlers: Iterable[_logging.Handler]) -> bool:
    """Return ``True`` when the shared stream handler has already been added."""
    for handler in handlers:
        if getattr(handler, "name", "") == _HANDLER_NAME:
            return True
    return False


def configure_logging(level: int = _DEFAULT_LOG_LEVEL) -> _logging.Logger:
    """Configure and return the package logger.

    Args:
        level (int): Logging level applied to the package logger. Defaults to
            :data:`logging.INFO`.

    Returns:
        logging.Logger: The shared package logger instance.
    """
    logger = _logging.getLogger(PACKAGE_LOGGER_NAME)
    logger.setLevel(level)
    if not _handler_exists(logger.handlers):
        handler = _logging.StreamHandler()
        handler.set_name(_HANDLER_NAME)
        handler.setFormatter(_logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
    logger.propagate = False
    return logger


configure_logging()

__all__ = ["configure_logging", "PACKAGE_LOGGER_NAME"]
