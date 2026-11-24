# Lock command protocol

Lock commands are **binary firmware packets**, signed with the account key, hex-encoded and placed in the `command` field of [`POST /v1/bridge/send`](endpoints/post-v1-bridge-send.md). Responses come back as a hex `payload` from [`POST /v1/bridge/receive`](endpoints/post-v1-bridge-receive.md). There is no JSON action like `{"lock": true}`.

## Packet layout ✅

| Offset | Size | Field | Encoding |
|---:|---:|---|---|
| 0 | 64 | Signature | secp256k1 ECDSA / **SHA-256**; `r` (32 B big-endian) then `s` (32 B big-endian) |
| 64 | 1 | Protocol version | `0x01` (`V2_0`) |
| 65 | 16 | Sender UUID | Account `uuid`, standard big-endian UUID bytes |
| 81 | 4 | Timestamp | Unsigned **little-endian** seconds since the **Level epoch** |
| 85 | 16 | Target UUID | Lock `DeviceUUID`, standard UUID bytes |
| 101 | 1 | Opcode | Wire value (see table below) |
| 102 | n | Payload | Opcode-specific |

- The signature covers **bytes 64 to the end** (everything except the signature slot).
- Total length = `102 + n`. Lock/unlock = 104 bytes (208 hex chars); history = 105 bytes (210 hex chars).

### Level epoch ✅

```python
LEVEL_EPOCH = 1466640000   # 2016-06-23T00:00:00Z
level_seconds = int(time.time()) - LEVEL_EPOCH
```

Used for command timestamps and history-event timestamps. The V3 operation **response** timestamp is plain Unix seconds instead. 🔍

### Building a packet (Python)

```python
import struct, time, uuid
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils

LEVEL_EPOCH = 1466640000

def build_command(key, sender: uuid.UUID, target: uuid.UUID, opcode: int, payload: bytes) -> bytes:
    body = (
        bytes([0x01])
        + sender.bytes
        + struct.pack("<I", int(time.time()) - LEVEL_EPOCH)
        + target.bytes
        + bytes([opcode])
        + payload
    )
    r, s = utils.decode_dss_signature(key.sign(body, ec.ECDSA(hashes.SHA256())))
    return r.to_bytes(32, "big") + s.to_bytes(32, "big") + body
```

## Opcodes

| Opcode (dec) | Hex | Name | Status |
|---:|---:|---|---|
| 14 | `0x0E` | `Admin` | 🔍 envelope-related; no standalone recipe |
| 20 | `0x14` | `OperationHistoryGetLatest` | ✅ read-only history |
| 22 | `0x16` | `BoltControllerOperateV2` | 🔍 older path, unused |
| 53 | `0x35` | `SystemStatusGet` | 🔍 construction found; response not traced |
| 54 | `0x36` | `BoltControllerOperateV3` | ✅ lock / unlock |
| 59 | `0x3B` | `OperationHistoryGetLatestV2` | 🔍 |
| 70 | `0x46` | `GetNonce` | 🔍 |
| 71 | `0x47` | `GetLockRange` | 🔍 |
| 75 | `0x4B` | `GetMatterStatus` | 🔍 |
| 88 | `0x58` | `BoltControllerOperateV4` | 🔍 used for door-sense override |
| 89 | `0x59` | `StateHistoryGetLatest` | 🔍 |
| 90 | `0x5A` | `StateBroadcastGet` | 🔍 possible live-state read; not traced |

## Lock / unlock: opcode 54 ✅

Owner confirmed both directions physically on one lock.

| Operation | Payload |
|---|---|
| Unlock | `00 0B` (operation 0, source 11 = REMOTE) |
| Lock | `01 0B` (operation 1, source 11 = REMOTE) |

The app picks opcode 88 (V4) instead only when the user asks to override door sense (`overrideDoorSense=true`), adding a flags payload. Not implemented. Never auto-escalate a refused V3 command to V4.

### V3 response (27 bytes) 🔍

| Offset | Size | Field | Notes |
|---:|---:|---|---|
| 0 | 1 | Bolt state | See [bolt states](models.md#bolt-state) |
| 1 | 1 | Operation result | See [operation results](models.md#operation-result) |
| 2 | 4 | Max current | int32 LE, unit ❓ |
| 6 | 4 | Average current | int32 LE, unit ❓ |
| 10 | 4 | Current variance | int32 LE |
| 14 | 2 | Duration | uint16 LE, unit ❓ |
| 16 | 4 | Min voltage | int32 LE, unit ❓ |
| 20 | 2 | Operation sequence ID | uint16 LE |
| 22 | 4 | Operation timestamp | uint32, **Unix** seconds (not Level epoch) per app parser |
| 26 | 1 | Nonce byte | Meaning ❓ |

Traced from the app (`_.jt1.d`) and tested with synthetic data. No real live response bytes have been captured yet.

PoC completion rule ⚙️: report success only if the payload parses, the timestamp is within ±30 s of submission/now, the reported state equals the requested state, and the result is `SUCCESS` or `ALREADY_THERE`.

## Read last operation: opcode 20 ✅

Read-only; does not move the bolt.

| Payload offset | Size | Value |
|---:|---:|---|
| 0 | 2 | `lastAnchor` = 0 (uint16 LE) |
| 2 | 1 | `requestEventCount` = 1 |

Payload hex: `00 00 01`. The app's default request count is 20; multi-event parsing is not yet documented.

### History response

Header:

| Offset | Size | Field |
|---:|---:|---|
| 0 | 1 | Current nonce byte |
| 1 | 2 | New anchor (uint16 LE) |
| 3 | 1 | Event count |
| 4 | … | Events |

Each event:

| Offset | Size | Field |
|---:|---:|---|
| 0 | 1 | Operation source |
| 1 | 4 | Timestamp, uint32 LE, **Level epoch** |
| 5 | 1 | Operation: 0 unlock, 1 lock |
| 6 | 1 | Resulting bolt state |
| 7 | 1 | Operation result |
| 8 | 16 | Operator ID (who did it) |
| 24 | 4 | Optional `dsn` (meaning ❓) |

One-event response = 28 bytes, or 32 with `dsn`. Zero events = 4 bytes. Timestamps 0 and `0xFFFFFFFF` mean "no valid time". ✅ (one live event parsed)

A history record is the **last stored operation**, which may be old. It is not a fresh reading of the bolt position.

## Reading lock state: the options

| Source | How | Freshness |
|---|---|---|
| `DeviceItem.BoltState` | `GET /v2/account/get` | Cloud cache; age ❓ |
| `DeviceItem.LastBoltOperationV2` | `GET /v2/account/get` | Cloud cache with its own timestamp |
| `DeviceItem.AdvertisingDataV2` | `GET /v2/account/get` | Last Bluetooth advertisement upload; includes bolt state, battery, door sense, timestamp |
| History (opcode 20) | Bridge round-trip | Last stored operation on the lock |
| V3 response | After lock/unlock | State right after the command |
| `SystemStatusGet` (53) / `StateBroadcastGet` (90) | Bridge round-trip | ❓ possibly live; not traced |

For Home Assistant polling, `BoltState` from the account call is the cheapest option. Whether it updates promptly after manual/keypad use is ❓.

## APK sources

| Subject | Class |
|---|---|
| Packet layout + signing | `_.bz6.G`, `_.p2a.a`, `_.mn3.f` |
| UUID bytes | `_.vuf.a` |
| Epoch conversion | `_.ui7.F0` / `_.ui7.G0` |
| Opcode selection V3 / V4 | `_.kfc.a` |
| Operation request/response | `_.b1a`, `_.jt1.a` / `_.jt1.d`, `BoltOperation*` |
| History | `_.an6`, `_.ei0.T`, `_.x1a`, `GetLatestOperationHistory*`, `OperationEvent`, `OperatorID` |
| Bridge command helper | `_.et1`, `_.bt1`, `_.vs1` |
