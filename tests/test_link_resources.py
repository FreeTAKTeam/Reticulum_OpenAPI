from types import SimpleNamespace

import pytest

from reticulum_openapi import link_client
from reticulum_openapi import link_service


class DummyResource:
    def __init__(self, *args, **kwargs):
        pass


def test_send_resource_callbacks(monkeypatch, tmp_path):
    """Ensure callbacks fire when sending a resource."""
    file_path = tmp_path / "data.txt"
    file_path.write_text("payload")

    calls = {"progress": False, "completion": False, "hook": False}
    fake_link = object()

    class FakeResource:
        def __init__(
            self, data, link, metadata=None, callback=None, progress_callback=None, **_
        ):
            assert data == str(file_path)
            assert link is fake_link
            assert metadata["filename"] == "data.txt"
            if progress_callback:
                progress_callback(self)
            if callback:
                callback(self)

    monkeypatch.setattr(link_client.RNS, "Resource", FakeResource)

    def progress(res):
        calls["progress"] = True

    def completion(res):
        calls["completion"] = True

    def hook(res):
        calls["hook"] = True

    cli = link_client.LinkFileClient(fake_link, on_upload_complete=hook)

    cli.send_resource(
        str(file_path), progress_callback=progress, completion_callback=completion
    )

    assert calls["progress"]
    assert calls["completion"]
    assert calls["hook"]


def test_send_resource_raises(monkeypatch, tmp_path):
    """Verify errors during resource send are propagated."""
    file_path = tmp_path / "data.txt"
    file_path.write_text("payload")

    def raise_resource(*a, **k):
        raise ValueError("boom")

    monkeypatch.setattr(link_client.RNS, "Resource", raise_resource)

    cli = link_client.LinkFileClient(object())

    with pytest.raises(ValueError):
        cli.send_resource(str(file_path))


def test_resource_received_callback(tmp_path):
    """Incoming resources with metadata should be stored using filename."""
    storage = tmp_path / "store"

    service = link_service.LinkResourceService(str(storage))

    src_path = tmp_path / "incoming"
    src_path.write_bytes(b"content")
    res = SimpleNamespace(
        metadata={"filename": "file.txt"}, storagepath=str(src_path), hash=b"\x01\x02"
    )

    service.resource_received_callback(res)

    saved = storage / "file.txt"
    assert saved.read_bytes() == b"content"


def test_resource_received_callback_no_metadata(tmp_path):
    """Resources lacking metadata should default to hash-based filenames."""
    storage = tmp_path / "store"
    called = {}

    def hook(path):
        called["path"] = path

    service = link_service.LinkResourceService(str(storage), on_download_complete=hook)

    src_path = tmp_path / "incoming"
    src_path.write_bytes(b"data")
    res = SimpleNamespace(metadata=None, storagepath=str(src_path), hash=b"\x0a\x0b")

    service.resource_received_callback(res)

    expected = storage / res.hash.hex()
    assert expected.read_bytes() == b"data"
    assert called["path"] == str(expected)
