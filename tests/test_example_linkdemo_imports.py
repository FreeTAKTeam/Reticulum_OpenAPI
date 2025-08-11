"""Basic import tests for the LinkDemo example."""

import importlib


def test_server_module_imports() -> None:
    """Server module should be importable and expose LinkService."""
    module = importlib.import_module("examples.LinkDemo.server")
    assert hasattr(module, "LinkService")


def test_client_module_imports() -> None:
    """Client module should be importable and define main."""
    module = importlib.import_module("examples.LinkDemo.client")
    assert hasattr(module, "main")
