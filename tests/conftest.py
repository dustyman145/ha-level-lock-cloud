"""Fixtures: a synthetic Level account and a mocked api.level.co."""

from __future__ import annotations

import os
import struct
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
import pytest

from custom_components.level_lock_cloud.crypto import (
    BLOB_SALT,
    _chacha20,
    _iterated_sha256,
)

API = "https://api.level.co"
PASSWORD = "correct horse"
EMAIL = "owner@example.invalid"
ACCOUNT_UUID = "00000000-0000-0000-0000-000000000001"
FRONT_UUID = "00000000-0000-0000-0000-0000000000f1"
GARAGE_UUID = "00000000-0000-0000-0000-0000000000f2"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    return


def _bson_int_array(name: str, values: list[int]) -> bytes:
    items = b"".join(
        b"\x10" + str(i).encode() + b"\x00" + struct.pack("<i", v) for i, v in enumerate(values)
    )
    array = struct.pack("<i", len(items) + 5) + items + b"\x00"
    elements = b"\x04" + name.encode() + b"\x00" + array
    return struct.pack("<i", len(elements) + 5) + elements + b"\x00"


def make_account(password: str = PASSWORD) -> tuple[dict[str, Any], ec.EllipticCurvePrivateKey]:
    """Build a synthetic account response with a real encrypted key blob."""
    key = ec.generate_private_key(ec.SECP256K1())
    scalar = key.private_numbers().private_value.to_bytes(32, "big")
    blob_key, n1, n2 = os.urandom(32), os.urandom(12), os.urandom(12)
    wrapped = _chacha20(_iterated_sha256(password, BLOB_SALT), n1, blob_key)
    signed_bytes = [b - 256 if b > 127 else b for b in scalar]  # Java signed bytes
    encrypted = _chacha20(blob_key, n2, _bson_int_array("privateKey", signed_bytes))
    r, s = utils.decode_dss_signature(key.sign(encrypted, ec.ECDSA(hashes.SHA512())))
    account = {
        "uuid": ACCOUNT_UUID,
        "encryptedBlobKeys": [{"name": "password", "nonce": n1.hex(), "value": wrapped.hex()}],
        "blob": {
            "nonce": n2.hex(),
            "value": encrypted.hex(),
            "sign": (r.to_bytes(32, "big") + s.to_bytes(32, "big")).hex(),
        },
        "Location": [
            {
                "LocationUUID": "00000000-0000-0000-0000-000000000004",
                "LocationName": "Home",
                "devices": [
                    {
                        "DeviceUUID": FRONT_UUID,
                        "name": "Front Door",
                        "BoltState": "1",
                        "SerialNumber": "SN1",
                        "door_sense_on": True,
                        "door_sense_state": "2",
                        "CurrentFirmwareInfo": {"version": "1.2.3.4"},
                        "AdvertisingDataV2": {"battery_level": "3"},
                        "LastBoltOperationV2": {
                            "timestamp": "2026-11-23T17:46:57Z",
                            "bolt_operation_source": "14",
                            "bolt_state": "1",
                        },
                        "bridge": {"bridge_uuid": "x", "active": True, "reachable": True},
                    },
                    {
                        "DeviceUUID": GARAGE_UUID,
                        "name": "Garage",
                        "BoltState": 0,
                        "door_sense_state": 0,
                        "AdvertisingDataV2": {"battery_level": 1},
                        "bridge": {"bridge_uuid": "y", "active": True, "reachable": False},
                    },
                ],
            }
        ],
    }
    return account, key


def operation_payload(state: int, result: int = 0) -> str:
    """A 27-byte V3 operation response as hex."""
    return (bytes([state, result]) + bytes(20) + struct.pack("<I", 1_800_000_000) + b"\x00").hex()


@pytest.fixture
def account() -> dict[str, Any]:
    """Synthetic account."""
    return make_account()[0]


@pytest.fixture
def level_api(aioclient_mock, account):
    """Mock the Level cloud for a non-2FA account."""
    aioclient_mock.post(
        f"{API}/v2/login", json={"status": []}, headers={"AccessToken": "tok-1"}
    )
    aioclient_mock.get(f"{API}/v2/account/get", json={"account": account})
    return aioclient_mock

