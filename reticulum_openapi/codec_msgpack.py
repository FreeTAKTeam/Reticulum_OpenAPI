"""
codec_msgpack.py
Canonical MessagePack codec for RNS/LXMF OpenAPI runtime.

Key functions:
- to_canonical_bytes(obj) -> bytes
- from_bytes(b: bytes) -> obj
- digest(obj) -> 32B (BLAKE3)
- sign(canon_bytes, sk) -> sig
- verify(canon_bytes, pk, sig) -> bool

MessagePack Canonicalization Rules (Critical for Signatures)
1) Maps: only UTF-8 string keys; keys are sorted by their UTF-8 byte value (ascending).
2) Integers: encode using the smallest integer representation that fits (MessagePack default).
3) Floats: DISALLOWED in signed regions. If needed, convert to Decimal/string upstream.
4) Strings vs Binary: human text as str; opaque bytes as bin.
5) Timestamps: epoch milliseconds as int64 (no ext type).
6) No ext types in signed regions (ext allowed only inside payload if independently signed).
7) payloadDigest = BLAKE3(canonical_msgpack(payload)).
8) Signature input = UTF-8 bytes of rid|ts|op concatenated with payloadDigest bytes.
"""

from typing import Any, TYPE_CHECKING, Union

# Optional dependencies
try:
    import msgpack  # type: ignore
except Exception:  # pragma: no cover
    msgpack = None

try:
    import blake3  # type: ignore
except Exception:  # pragma: no cover
    blake3 = None

# Ed25519 via PyNaCl if available
try:
    from nacl.signing import SigningKey, VerifyKey  # type: ignore
    from nacl.exceptions import BadSignatureError  # type: ignore
except Exception:  # pragma: no cover
    SigningKey = None
    VerifyKey = None
    BadSignatureError = Exception


class CodecError(Exception):
    pass


class DependencyError(CodecError):
    pass


############################
# Low-level MessagePack enc
############################


def _pack_nil() -> bytes:
    return b"\xc0"


def _pack_bool(v: bool) -> bytes:
    return b"\xc3" if v else b"\xc2"


def _pack_int(n: int) -> bytes:
    # positive fixint
    if 0 <= n <= 0x7F:
        return bytes([n])
    # negative fixint
    if -32 <= n < 0:
        return (n & 0xFF).to_bytes(1, "big")
    # choose signed/unsigned minimal width
    if n < 0:
        # signed
        if -128 <= n <= 127:
            return b"\xd0" + (n & 0xFF).to_bytes(1, "big")
        if -32768 <= n <= 32767:
            return b"\xd1" + (n & 0xFFFF).to_bytes(2, "big")
        if -2147483648 <= n <= 2147483647:
            return b"\xd2" + (n & 0xFFFFFFFF).to_bytes(4, "big")
        if n < -(2**63) or n > 2**64 - 1:
            raise CodecError("Integer out of range for MessagePack")
        return b"\xd3" + (n & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "big")
    else:
        # unsigned
        if n <= 0xFF:
            return b"\xcc" + n.to_bytes(1, "big")
        if n <= 0xFFFF:
            return b"\xcd" + n.to_bytes(2, "big")
        if n <= 0xFFFFFFFF:
            return b"\xce" + n.to_bytes(4, "big")
        if n < -(2**63) or n > 2**64 - 1:
            raise CodecError("Integer out of range for MessagePack")
        return b"\xcf" + n.to_bytes(8, "big")


def _pack_bin(b: bytes) -> bytes:
    n = len(b)
    if n <= 0xFF:
        return b"\xc4" + bytes([n]) + b
    if n <= 0xFFFF:
        return b"\xc5" + n.to_bytes(2, "big") + b
    return b"\xc6" + n.to_bytes(4, "big") + b


def _pack_str(s: str) -> bytes:
    b = s.encode("utf-8")
    n = len(b)
    if n <= 31:
        return bytes([0xA0 | n]) + b
    if n <= 0xFF:
        return b"\xd9" + bytes([n]) + b
    if n <= 0xFFFF:
        return b"\xda" + n.to_bytes(2, "big") + b
    return b"\xdb" + n.to_bytes(4, "big") + b


def _pack_array(arr: list) -> bytes:
    n = len(arr)
    if n <= 15:
        prefix = bytes([0x90 | n])
    elif n <= 0xFFFF:
        prefix = b"\xdc" + n.to_bytes(2, "big")
    else:
        prefix = b"\xdd" + n.to_bytes(4, "big")
    return prefix + b"".join(_pack(x) for x in arr)


def _pack_map(d: dict) -> bytes:
    n = len(d)
    # Keys must be strings; order by UTF-8 bytes
    items = []
    for k, v in d.items():
        if not isinstance(k, str):
            raise CodecError("Canonical maps require string keys")
        items.append((k.encode("utf-8"), k, v))
    items.sort(key=lambda t: t[0])
    if n <= 15:
        prefix = bytes([0x80 | n])
    elif n <= 0xFFFF:
        prefix = b"\xde" + n.to_bytes(2, "big")
    else:
        prefix = b"\xdf" + n.to_bytes(4, "big")
    out = [prefix]
    for key_bytes, key_str, val in items:
        out.append(_pack_str(key_str))
        out.append(_pack(val))
    return b"".join(out)


def _pack(o: Any) -> bytes:
    if o is None:
        return _pack_nil()
    if isinstance(o, bool):
        return _pack_bool(o)
    if isinstance(o, int):
        return _pack_int(o)
    if isinstance(o, bytes):
        return _pack_bin(o)
    if isinstance(o, str):
        return _pack_str(o)
    if isinstance(o, list):
        return _pack_array(o)
    if isinstance(o, tuple):
        return _pack_array(list(o))
    if isinstance(o, dict):
        return _pack_map(o)
    # Float or others are not allowed for canonical/signed bytes
    raise CodecError(f"Type not allowed in canonical MessagePack: {type(o).__name__}")


############################
# Public API
############################


def to_canonical_bytes(obj: Any) -> bytes:
    """
    Encode obj to canonical MessagePack bytes with the rules above.
    """
    return _pack(obj)


def from_bytes(b: bytes) -> Any:
    """
    Decode MessagePack bytes to Python object using msgpack if available.

    Note: Decoding does not preserve map key order; canonicalization applies only to encoding.
    """
    if msgpack is None:
        raise DependencyError(
            "msgpack is required for from_bytes(). Install `msgpack`."
        )
    return msgpack.unpackb(b, raw=False)


def digest(obj: Any) -> bytes:
    """
    Compute 32-byte BLAKE3 digest of canonical MessagePack encoding of obj.
    """
    if blake3 is None:
        raise DependencyError("blake3 is required for digest(). Install `blake3`.")
    data = to_canonical_bytes(obj)
    return blake3.blake3(data).digest()


def sign(canon_bytes: bytes, sk: Union[bytes, "SigningKey"]) -> bytes:
    """
    Sign canonical bytes with Ed25519. `sk` can be a 32-byte seed or a nacl.signing.SigningKey.
    Returns signature bytes (64B).
    """
    if SigningKey is None:
        raise DependencyError("PyNaCl is required for sign(). Install `pynacl`.")
    if isinstance(sk, bytes):
        if len(sk) != 32:
            raise CodecError("Signing key seed must be 32 bytes")
        sk = SigningKey(sk)
    signed = sk.sign(canon_bytes)
    return bytes(signed.signature)


def verify(canon_bytes: bytes, pk: Union[bytes, VerifyKey], sig: bytes) -> bool:
    """
    Verify an Ed25519 signature over canonical bytes. `pk` can be 32-byte public key or VerifyKey.
    """
    if VerifyKey is None:
        raise DependencyError("PyNaCl is required for verify(). Install `pynacl`.")
    if isinstance(pk, bytes):
        if len(pk) != 32:
            raise CodecError("Verify key must be 32 bytes")
        pk = VerifyKey(pk)
    try:
        pk.verify(canon_bytes, sig)
        return True
    except BadSignatureError:
        return False
