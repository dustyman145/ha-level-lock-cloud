# `GET /v2/account/get`

**Purpose:** Get the account, its locations, all locks (with cached state, access lists and bridge info) and the encrypted signing-key blob.
**Evidence:** ✅ Verified
**Source:** `_.pe`, `Account` serializer
**Used by integration:** yes, for discovery and polling

## Request

| Part | Value |
|---|---|
| URL | `https://api.level.co/v2/account/get` |
| Auth | `AccessToken` header |
| Body | none |

### Headers

| Header | Value |
|---|---|
| `AccessToken` | `<ACCESS_TOKEN>` |
| `Accept` | `application/json` |
| `Content-Type` | `application/json` |

## Response (200)

An `Account` object, possibly wrapped as `{"account": {...}}` ❓. Full model: [models.md → Account](../models.md#account).

Fields the integration needs:

| Path | Use |
|---|---|
| `uuid` | Sender UUID for commands; match against access lists |
| `encryptedBlobKeys`, `blob` | Decrypt the signing key ([account-key.md](../account-key.md)) |
| `Location[]` | Homes |
| `Location[].devices[]` | Locks |
| `…devices[].DeviceUUID` | Lock ID for `bridge/send` and command target |
| `…devices[].name` | Display name |
| `…devices[].BoltState` | Cached state: 0 unlocked, 1 locked, 2 partial, 3 unknown |
| `…devices[].LastBoltOperationV2` | Last operation with timestamp |
| `…devices[].bridge` | Present when a Level Connect is paired; `reachable`, `active` |
| `…devices[].AccessMap`, `UserList` | Whether this account may command the lock |
| `…devices[].CurrentFirmwareInfo.version` | Firmware version |
| `…devices[].SerialNumber`, `Product` | Device info |

Example: see [models.md](../models.md#example-account-trimmed--shape).

## Notes

- Traverse `account["Location"][i]["devices"][j]`. Capital `L` in `Location`, lowercase `devices`.
- Use `DeviceUUID`, never `bridge.bridge_uuid`, as the command target.
- `BoltState` is a cloud cache. How quickly it updates after keypad or manual use ❓.
- Response contains personal data (emails, phone numbers, names) and the encrypted key. Never log or commit it.
- A lock without `bridge` cannot be commanded through the cloud ❓ (not tested).
