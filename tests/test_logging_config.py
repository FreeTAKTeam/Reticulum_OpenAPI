"""Tests for shared logging configuration."""

from __future__ import annotations

import importlib
import logging
import sys
from typing import List

import reticulum_openapi.logging_config as logging_config


def _reset_package_logger() -> None:
    """Remove all handlers from the package logger to create a clean slate."""
    package_logger = logging.getLogger(logging_config.PACKAGE_LOGGER_NAME)
    for handler in list(package_logger.handlers):
        package_logger.removeHandler(handler)
        handler.close()
    package_logger.propagate = True


def _handler_ids(logger: logging.Logger) -> List[int]:
    """Return stable identifiers for handlers attached to ``logger``."""
    return [id(handler) for handler in logger.handlers]


def test_configure_logging_is_idempotent() -> None:
    """Importing or configuring logging repeatedly must not add handlers."""
    _reset_package_logger()
    reloaded_logging = importlib.reload(logging_config)
    package_logger = logging.getLogger(reloaded_logging.PACKAGE_LOGGER_NAME)
    assert len(package_logger.handlers) == 1
    existing_handlers = _handler_ids(package_logger)

    reloaded_logging.configure_logging()
    reloaded_logging.configure_logging()

    assert _handler_ids(package_logger) == existing_handlers


def test_controller_import_does_not_duplicate_handlers() -> None:
    """Reloading controller reuses the shared logger configuration."""
    _reset_package_logger()
    reloaded_logging = importlib.reload(logging_config)
    package_logger = logging.getLogger(reloaded_logging.PACKAGE_LOGGER_NAME)
    assert len(package_logger.handlers) == 1
    initial_handlers = _handler_ids(package_logger)

    import reticulum_openapi.controller as controller_module

    controller = importlib.reload(controller_module)
    assert _handler_ids(package_logger) == initial_handlers

    controller = importlib.reload(controller)
    assert _handler_ids(package_logger) == initial_handlers
    assert controller.logger is logging.getLogger(controller.__name__)


def test_logging_alias_remains_available() -> None:
    """Importing ``reticulum_openapi.logging`` returns the configuration module."""
    module = importlib.import_module("reticulum_openapi.logging")
    assert module is logging_config
    assert sys.modules.get("reticulum_openapi.logging") is module
