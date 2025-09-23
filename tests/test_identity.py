"""Tests for persistent identity loading utilities."""

from pathlib import Path

from reticulum_openapi import identity as identity_module


def test_load_identity_reuses_existing_file(monkeypatch, tmp_path):
    """Existing identity files should be loaded without creating new keys."""

    existing_identity = object()

    class DummyIdentity:
        created = 0
        load_calls = 0
        saved_paths: list[str] = []

        def __init__(self):
            DummyIdentity.created += 1

        @staticmethod
        def from_file(path: str):
            DummyIdentity.load_calls += 1
            return existing_identity

        def to_file(self, path: str) -> None:
            DummyIdentity.saved_paths.append(path)

    monkeypatch.setattr(identity_module.RNS, "Identity", DummyIdentity)
    monkeypatch.setattr(
        identity_module.RNS.Reticulum,
        "configdir",
        str(tmp_path),
    )
    identity_file = tmp_path / "identity"
    identity_file.write_text("stub")

    result = identity_module.load_or_create_identity()

    assert result is existing_identity
    assert DummyIdentity.created == 0
    assert DummyIdentity.load_calls == 1
    assert DummyIdentity.saved_paths == []


def test_load_identity_creates_when_missing(monkeypatch, tmp_path):
    """A new identity is created and persisted when no file exists."""

    class DummyIdentity:
        created = 0
        load_calls = 0
        saved_paths: list[str] = []
        persisted_instance = None

        def __init__(self):
            DummyIdentity.created += 1
            DummyIdentity.persisted_instance = self

        @staticmethod
        def from_file(path: str):
            DummyIdentity.load_calls += 1
            if Path(path).exists():
                return DummyIdentity.persisted_instance
            return None

        def to_file(self, path: str) -> None:
            DummyIdentity.saved_paths.append(path)
            Path(path).write_text("saved")

    monkeypatch.setattr(identity_module.RNS, "Identity", DummyIdentity)
    monkeypatch.setattr(
        identity_module.RNS.Reticulum,
        "configdir",
        str(tmp_path),
    )

    created = identity_module.load_or_create_identity()

    assert isinstance(created, DummyIdentity)
    assert DummyIdentity.created == 1
    assert DummyIdentity.saved_paths == [str(tmp_path / "identity")]

    loaded = identity_module.load_or_create_identity()

    assert loaded is created
    assert DummyIdentity.load_calls == 1
    assert DummyIdentity.created == 1
