"""Tests for the crypto and binary protocol helpers."""

from __future__ import annotations

import base64
import hashlib
import struct
import uuid

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
import pytest

from custom_components.level_lock_cloud.crypto import (
    LEVEL_EPOCH,
    LevelCryptoError,
    LevelProtocolError,
    _chacha20,
    account_private_key,
    build_command,
    login_value,
    operate_payload,
    otp_hash,
    parse_history,
    parse_operation_response,
)

from .conftest import PASSWORD, make_account


def test_login_value_matches_documented_derivation() -> None:
    value = b"pw" + b"CFF33588-AC1D-4F77-943B-728CF61FCC1B"
    for _ in range(102):
        value = hashlib.sha256(value).digest()
    assert login_value("pw") == base64.b64encode(value).decode()


def test_otp_hash() -> None:
    assert otp_hash(" 123456 ") == hashlib.sha256(b"123456").hexdigest()[:12]
    assert len(otp_hash("1")) == 12


def test_chacha20_rfc8439_vector() -> None:
    """RFC 8439 2.4.2 uses counter 1; skip the first 64-byte block of a counter-0 stream."""
    key = bytes(range(32))
    nonce = bytes.fromhex("000000000000004a00000000")
    plaintext = (
        b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip "
        b"for the future, sunscreen would be it."
    )
    out = _chacha20(key, nonce, bytes(64) + plaintext)[64:]
    assert out.hex().startswith("6e2e359a2568f98041ba0728dd0d6981")


def test_account_key_roundtrip() -> None:
    account, key = make_account()
    loaded = account_private_key(account, PASSWORD)
    assert loaded.private_numbers().private_value == key.private_numbers().private_value


def test_account_key_wrong_password() -> None:
    account, _ = make_account()
    with pytest.raises(LevelCryptoError):
        account_private_key(account, "wrong")


def test_account_key_base64_wrapped_entry() -> None:
    account, _ = make_account()
    entry = account["encryptedBlobKeys"][0]
    entry["nonce"] = base64.b64encode(bytes.fromhex(entry["nonce"])).decode()
    entry["value"] = base64.b64encode(bytes.fromhex(entry["value"])).decode()
    account_private_key(account, PASSWORD)


def test_build_command_layout_and_signature() -> None:
    key = ec.generate_private_key(ec.SECP256K1())
    sender, target = uuid.uuid4(), uuid.uuid4()
    packet = build_command(key, sender, target, 54, operate_payload(True), LEVEL_EPOCH + 1000)
    assert len(packet) == 104
    assert packet[64] == 1
    assert packet[65:81] == sender.bytes
    assert struct.unpack("<I", packet[81:85])[0] == 1000
    assert packet[85:101] == target.bytes
    assert packet[101] == 54
    assert packet[102:] == bytes([1, 11])
    der = utils.encode_dss_signature(
        int.from_bytes(packet[:32], "big"), int.from_bytes(packet[32:64], "big")
    )
    key.public_key().verify(der, packet[64:], ec.ECDSA(hashes.SHA256()))


def test_parse_operation_response() -> None:
    payload = bytes([1, 0]) + bytes(20) + struct.pack("<I", 1234) + b"\x07"
    parsed = parse_operation_response(payload)
    assert (parsed.bolt_state, parsed.result, parsed.timestamp) == (1, 0, 1234)
    with pytest.raises(LevelProtocolError):
        parse_operation_response(payload[:-1])


def test_parse_history() -> None:
    header = bytes([0]) + struct.pack("<H", 5) + bytes([1])
    event = bytes([14]) + struct.pack("<I", 100) + bytes([1, 1, 0]) + bytes(16)
    (parsed,) = parse_history(header + event)
    assert parsed.source == 14
    assert parsed.timestamp == LEVEL_EPOCH + 100
    assert parse_history(bytes([0, 0, 0, 0])) == []
