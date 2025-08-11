
# tests/test_codec_msgpack.py
import os
import sys
import importlib
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import pytest

codec = importlib.import_module("runtime.codec_msgpack")

def test_basic_integers():
    # 127 => 0x7f
    b = codec.to_canonical_bytes(127)
    assert b == b'\x7f'
    # 128 => uint8 0xcc 0x80
    b = codec.to_canonical_bytes(128)
    assert b == b'\xcc\x80'
    # -1 => 0xff
    b = codec.to_canonical_bytes(-1)
    assert b == b'\xff'

def test_basic_strings_and_bins():
    b = codec.to_canonical_bytes("a")
    assert b == b'\xa1a'
    data = codec.to_canonical_bytes(b'\x01\x02')
    assert data == b'\xc4\x02\x01\x02'

def test_arrays_and_maps_ordering():
    b = codec.to_canonical_bytes(["x", 1, True])
    assert b.startswith(b'\x93')  # fixarray of size 3
    # Map ordering: keys sorted by UTF-8 bytes
    obj = {"b": 1, "a": 2}
    enc = codec.to_canonical_bytes(obj)
    expected = b'\x82' + b'\xa1a' + b'\x02' + b'\xa1b' + b'\x01'
    assert enc == expected

def test_disallow_float():
    import math
    with pytest.raises(codec.CodecError):
        codec.to_canonical_bytes(1.23)
    with pytest.raises(codec.CodecError):
        codec.to_canonical_bytes(float('nan'))

@pytest.mark.skipif(importlib.util.find_spec("msgpack") is None, reason="msgpack not installed")
def test_roundtrip_with_msgpack():
    obj = {"a": 1, "b": ["x", 2], "c": None}
    b = codec.to_canonical_bytes(obj)
    back = codec.from_bytes(b)
    assert back == obj

@pytest.mark.skipif(importlib.util.find_spec("blake3") is None, reason="blake3 not installed")
def test_digest_stability_blake3():
    obj = {"a": 1, "b": "x"}
    d1 = codec.digest(obj)
    d2 = codec.digest(obj)
    assert d1 == d2 and len(d1) == 32

@pytest.mark.skipif(importlib.util.find_spec("nacl") is None, reason="PyNaCl not installed")
def test_sign_verify_ed25519():
    from nacl.signing import SigningKey
    sk = SigningKey.generate()
    pk = sk.verify_key
    msg = codec.to_canonical_bytes({"rid": "r", "ts": 1, "op": "o"})
    sig = codec.sign(msg, sk)
    assert codec.verify(msg, pk, sig) is True
    # tamper
    tampered = msg + b'\x00'
    assert codec.verify(tampered, pk, sig) is False
