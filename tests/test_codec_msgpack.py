import importlib
import pytest

from reticulum_openapi import codec_msgpack as codec


def test_basic_integers():
    """Verify canonical encoding of basic integers."""
    b = codec.to_canonical_bytes(127)
    assert b == b"\x7f"
    b = codec.to_canonical_bytes(128)
    assert b == b"\xcc\x80"
    b = codec.to_canonical_bytes(-1)
    assert b == b"\xff"


def test_int64_bounds_and_overflow():
    """Check 64-bit integer boundaries and overflow handling."""
    min_signed = -(2**63)
    max_unsigned = 2**64 - 1
    b = codec.to_canonical_bytes(min_signed)
    assert b == b"\xd3" + (min_signed & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "big")
    b = codec.to_canonical_bytes(max_unsigned)
    assert b == b"\xcf" + max_unsigned.to_bytes(8, "big")
    with pytest.raises(codec.CodecError):
        codec.to_canonical_bytes(min_signed - 1)
    with pytest.raises(codec.CodecError):
        codec.to_canonical_bytes(max_unsigned + 1)


def test_basic_strings_and_bins():
    """Ensure strings and binary data are encoded correctly."""
    b = codec.to_canonical_bytes("a")
    assert b == b"\xa1a"
    data = codec.to_canonical_bytes(b"\x01\x02")
    assert data == b"\xc4\x02\x01\x02"


def test_arrays_and_maps_ordering():
    """Arrays and maps should preserve ordering for canonical form."""
    b = codec.to_canonical_bytes(["x", 1, True])
    assert b.startswith(b"\x93")
    obj = {"b": 1, "a": 2}
    enc = codec.to_canonical_bytes(obj)
    expected = b"\x82" + b"\xa1a" + b"\x02" + b"\xa1b" + b"\x01"
    assert enc == expected


def test_disallow_float():
    """Floats should not be allowed for canonical bytes."""
    with pytest.raises(codec.CodecError):
        codec.to_canonical_bytes(1.23)
    with pytest.raises(codec.CodecError):
        codec.to_canonical_bytes(float("nan"))


@pytest.mark.skipif(
    importlib.util.find_spec("msgpack") is None, reason="msgpack not installed"
)
def test_roundtrip_with_msgpack():
    """Round-trip encode/decode using msgpack when available."""
    obj = {"a": 1, "b": ["x", 2], "c": None}
    b = codec.to_canonical_bytes(obj)
    back = codec.from_bytes(b)
    assert back == obj


@pytest.mark.skipif(
    importlib.util.find_spec("blake3") is None, reason="blake3 not installed"
)
def test_digest_stability_blake3():
    """Digest results should be stable when using blake3."""
    obj = {"a": 1, "b": "x"}
    d1 = codec.digest(obj)
    d2 = codec.digest(obj)
    assert d1 == d2 and len(d1) == 32


@pytest.mark.skipif(
    importlib.util.find_spec("nacl") is None, reason="PyNaCl not installed"
)
def test_sign_verify_ed25519():
    """Ed25519 signatures should verify correctly."""
    from nacl.signing import SigningKey

    sk = SigningKey.generate()
    pk = sk.verify_key
    msg = codec.to_canonical_bytes({"rid": "r", "ts": 1, "op": "o"})
    sig = codec.sign(msg, sk)
    assert codec.verify(msg, pk, sig) is True
    tampered = msg + b"\x00"
    assert codec.verify(tampered, pk, sig) is False
