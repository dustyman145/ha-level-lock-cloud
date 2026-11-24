"""Cryptography and binary protocol helpers for the Level cloud API.

See docs/api/account-key.md and docs/api/command-protocol.md.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import struct
import time
from typing import Any
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms

LOGIN_SALT = b"CFF33588-AC1D-4F77-943B-728CF61FCC1B"
BLOB_SALT = b"C0771591-BE41-4E22-8C89-D4521D9538B4"
HASH_ROUNDS = 102
LEVEL_EPOCH = 1466640000
PROTOCOL_VERSION = 0x01

OPCODE_HISTORY_LATEST = 20
OPCODE_BOLT_OPERATE_V3 = 54
SOURCE_REMOTE = 11


class LevelCryptoError(Exception):
    """Raised when the account key cannot be decrypted or verified."""


class LevelProtocolError(Exception):
    """Raised when a lock response cannot be parsed."""


def _iterated_sha256(password: str, salt: bytes) -> bytes:
    value = password.encode("utf-8") + salt
    for _ in range(HASH_ROUNDS):
        value = hashlib.sha256(value).digest()
    return value


def login_value(password: str) -> str:
    """Return the derived value sent as `password` to /v2/login."""
    return base64.b64encode(_iterated_sha256(password, LOGIN_SALT)).decode("ascii")


def otp_hash(code: str) -> str:
    """Return the value sent as `hash` to /v1/2fa/confirm."""
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()[:12]


def _chacha20(key: bytes, nonce: bytes, data: bytes) -> bytes:
    if len(key) != 32 or len(nonce) != 12:
        raise LevelCryptoError("Unexpected key or nonce length")
    cipher = Cipher(algorithms.ChaCha20(key, (0).to_bytes(4, "little") + nonce), mode=None)
    return cipher.decryptor().update(data)


def _decode_wrapped(text: str, hex_len: int) -> bytes:
    if len(text) == hex_len:
        return bytes.fromhex(text)
    return base64.b64decode(text)


# --- Minimal BSON reader (only what the account blob needs) -----------------


def _bson_document(data: bytes, pos: int = 0) -> tuple[dict[str, Any], int]:
    size = int.from_bytes(data[pos : pos + 4], "little")
    end = pos + size
    pos += 4
    out: dict[str, Any] = {}
    while pos < end - 1:
        kind = data[pos]
        pos += 1
        key_end = data.index(0, pos)
        key = data[pos:key_end].decode("utf-8")
        pos = key_end + 1
        value: Any
        if kind == 0x10:  # int32
            value = int.from_bytes(data[pos : pos + 4], "little", signed=True)
            pos += 4
        elif kind in (0x09, 0x11, 0x12):  # datetime, timestamp, int64
            value = int.from_bytes(data[pos : pos + 8], "little", signed=True)
            pos += 8
        elif kind == 0x01:  # double
            value = struct.unpack("<d", data[pos : pos + 8])[0]
            pos += 8
        elif kind in (0x02, 0x0D, 0x0E):  # string, js code, symbol
            length = int.from_bytes(data[pos : pos + 4], "little")
            value = data[pos + 4 : pos + 4 + length - 1].decode("utf-8")
            pos += 4 + length
        elif kind in (0x03, 0x04):  # document, array
            sub, sub_size = _bson_document(data, pos)
            value = list(sub.values()) if kind == 0x04 else sub
            pos += sub_size
        elif kind == 0x05:  # binary
            length = int.from_bytes(data[pos : pos + 4], "little")
            value = data[pos + 5 : pos + 5 + length]
            pos += 5 + length
        elif kind == 0x08:  # bool
            value = data[pos] != 0
            pos += 1
        elif kind == 0x07:  # ObjectId
            value = data[pos : pos + 12]
            pos += 12
        elif kind == 0x13:  # decimal128
            value = data[pos : pos + 16]
            pos += 16
        elif kind in (0x06, 0x0A, 0x7F, 0xFF):  # undefined, null, max/min key
            value = None
        else:
            raise LevelCryptoError(f"Unsupported BSON type 0x{kind:02x}")
        out[key] = value
    return out, size


# --- Account key -------------------------------------------------------------


def account_private_key(account: dict[str, Any], password: str) -> ec.EllipticCurvePrivateKey:
    """Decrypt and verify the account's secp256k1 signing key."""
    try:
        entry = next(
            e for e in account.get("encryptedBlobKeys") or [] if e.get("name") == "password"
        )
        blob_key = _chacha20(
            _iterated_sha256(password, BLOB_SALT),
            _decode_wrapped(entry["nonce"], 24),
            _decode_wrapped(entry["value"], 64),
        )
        blob = account["blob"]
        encrypted = bytes.fromhex(blob["value"])
        document, _ = _bson_document(_chacha20(blob_key, bytes.fromhex(blob["nonce"]), encrypted))
        raw = document["privateKey"]
        key_bytes = bytes(raw) if isinstance(raw, bytes) else bytes(b & 0xFF for b in raw)
        if len(key_bytes) != 32:
            raise LevelCryptoError("Unexpected private key length")
        key = ec.derive_private_key(int.from_bytes(key_bytes, "big"), ec.SECP256K1())

        signature = bytes.fromhex(blob["sign"])
        half = len(signature) // 2
        if half == 0 or len(signature) % 2:
            raise LevelCryptoError("Malformed blob signature")
        der = utils.encode_dss_signature(
            int.from_bytes(signature[:half], "big"), int.from_bytes(signature[half:], "big")
        )
        key.public_key().verify(der, encrypted, ec.ECDSA(hashes.SHA512()))
    except LevelCryptoError:
        raise
    except InvalidSignature as err:
        raise LevelCryptoError("Account key signature check failed (wrong password?)") from err
    except (StopIteration, KeyError, ValueError, TypeError, IndexError) as err:
        raise LevelCryptoError(f"Cannot decrypt account key: {err!r}") from err
    return key


# --- Commands ----------------------------------------------------------------


def build_command(
    key: ec.EllipticCurvePrivateKey,
    sender: uuid.UUID,
    target: uuid.UUID,
    opcode: int,
    payload: bytes,
    unix_seconds: float | None = None,
) -> bytes:
    """Build and sign a firmware command packet."""
    now = int(time.time() if unix_seconds is None else unix_seconds)
    body = (
        bytes([PROTOCOL_VERSION])
        + sender.bytes
        + struct.pack("<I", now - LEVEL_EPOCH)
        + target.bytes
        + bytes([opcode])
        + payload
    )
    r, s = utils.decode_dss_signature(key.sign(body, ec.ECDSA(hashes.SHA256())))
    return r.to_bytes(32, "big") + s.to_bytes(32, "big") + body


def operate_payload(lock: bool) -> bytes:
    """Payload for BoltControllerOperateV3."""
    return bytes([1 if lock else 0, SOURCE_REMOTE])


HISTORY_LATEST_PAYLOAD = bytes([0, 0, 1])


@dataclass(slots=True)
class OperationResponse:
    """Parsed BoltControllerOperateV3 response."""

    bolt_state: int
    result: int
    timestamp: int  # Unix seconds


def parse_operation_response(payload: bytes) -> OperationResponse:
    """Parse a 27-byte V3 operation response."""
    if len(payload) != 27:
        raise LevelProtocolError(f"Unexpected operation response length {len(payload)}")
    return OperationResponse(
        bolt_state=payload[0],
        result=payload[1],
        timestamp=int.from_bytes(payload[22:26], "little"),
    )


@dataclass(slots=True)
class HistoryEvent:
    """One operation history record."""

    source: int
    timestamp: int | None  # Unix seconds
    operation: int
    bolt_state: int
    result: int


def parse_history(payload: bytes) -> list[HistoryEvent]:
    """Parse an OperationHistoryGetLatest response (one or zero events)."""
    if len(payload) < 4:
        raise LevelProtocolError("History response too short")
    count = payload[3]
    if count == 0:
        return []
    if count != 1 or len(payload) not in (28, 32):
        raise LevelProtocolError(f"Unsupported history response ({count} events, {len(payload)} B)")
    event = payload[4:]
    raw_ts = int.from_bytes(event[1:5], "little")
    return [
        HistoryEvent(
            source=event[0],
            timestamp=None if raw_ts in (0, 0xFFFFFFFF) else raw_ts + LEVEL_EPOCH,
            operation=event[5],
            bolt_state=event[6],
            result=event[7],
        )
    ]
