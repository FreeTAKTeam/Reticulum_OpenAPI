import importlib
import pytest

from reticulum_openapi import codec_msgpack as codec


@pytest.fixture
def misordered_map_bytes() -> bytes:
    """Bytes for a map with unsorted keys."""
    return b"\x82\xa1b\x01\xa1a\x02"


@pytest.fixture
def int_boundary_vectors() -> dict[int, dict[str, bytes]]:
    """Canonical int encodings from Python, Go, and TS."""
    return {
        127: {"python": b"\x7f", "go": b"\x7f", "ts": b"\x7f"},
        128: {"python": b"\xcc\x80", "go": b"\xcc\x80", "ts": b"\xcc\x80"},
    }


@pytest.fixture
def digest_vectors() -> dict[str, object]:
    """Precomputed BLAKE3 digests from other implementations."""
    hex_digest = "158deb4967a3da4287e78229ad2290cf58a65402bf9460d376e68c5807f4aac4"
    return {
        "obj": {"a": 1, "b": "x"},
        "digests": {"python": hex_digest, "go": hex_digest, "ts": hex_digest},
    }


def test_basic_integers():
    """Verify canonical encoding of basic integers."""
    b = codec.to_canonical_bytes(127)
    assert b == b"\x7f"
    b = codec.to_canonical_bytes(128)
    assert b == b"\xcc\x80"
    b = codec.to_canonical_bytes(-1)
    assert b == b"\xff"


def test_cross_language_boundaries(int_boundary_vectors):
    """Ensure 127/128 encodings match across implementations."""
    for num, vectors in int_boundary_vectors.items():
        enc = codec.to_canonical_bytes(num)
        assert enc == vectors["python"] == vectors["go"] == vectors["ts"]


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


def test_nan_disallowed():
    """NaN should raise CodecError during canonicalization."""
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
    importlib.util.find_spec("blake3") is None, reason="blake3 not installed"
)
def test_cross_language_digest(digest_vectors):
    """Digests should match precomputed cross-language values."""
    expected = digest_vectors["digests"]
    computed = codec.digest(digest_vectors["obj"]).hex()
    assert computed == expected["python"] == expected["go"] == expected["ts"]


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


@pytest.mark.skipif(
    importlib.util.find_spec("nacl") is None, reason="PyNaCl not installed"
)
def test_verify_fails_on_misordered_map(misordered_map_bytes):
    """Verification should fail for misordered map bytes."""
    from nacl.signing import SigningKey

    sk = SigningKey.generate()
    pk = sk.verify_key
    obj = {"b": 1, "a": 2}
    canon = codec.to_canonical_bytes(obj)
    sig = codec.sign(canon, sk)
    assert codec.verify(canon, pk, sig) is True
    assert codec.verify(misordered_map_bytes, pk, sig) is False


@pytest.mark.skipif(
    importlib.util.find_spec("msgpack") is None
    or importlib.util.find_spec("nacl") is None,
    reason="msgpack or PyNaCl not installed",
)
def test_verify_fails_with_ext_type():
    """Verification should fail when bytes include ext types."""
    import msgpack
    from nacl.signing import SigningKey

    sk = SigningKey.generate()
    pk = sk.verify_key
    base = {"a": b"\x00"}
    canon = codec.to_canonical_bytes(base)
    sig = codec.sign(canon, sk)
    bad = msgpack.packb({"a": msgpack.ExtType(1, b"\x00")}, use_bin_type=True)
    assert codec.verify(bad, pk, sig) is False
