# `POST /v1/bridge/send`

**Purpose:** Submit a signed binary command to a lock through its Level Connect bridge.
**Evidence:** ✅ Verified (history read, lock and unlock on one lock)
**Source:** `_.ix1`, `_.et1.b`, `BridgeSendInput`, `BridgeSendOutput`
**Used by integration:** yes

## Request

| Part | Value |
|---|---|
| URL | `https://api.level.co/v1/bridge/send` |
| Auth | `AccessToken` header |

### Headers

| Header | Value |
|---|---|
| `AccessToken` | `<ACCESS_TOKEN>` |
| `Accept` | `application/json` |
| `Content-Type` | `application/json` |

### Body (`BridgeSendInput`)

```json
{
  "device_uuid": "00000000-0000-0000-0000-000000000002",
  "command": "<hex of the complete signed packet>",
  "is_admin_queue_item": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `device_uuid` | UUID string | yes | Lock `DeviceUUID`. **Not** the `bridge_uuid` |
| `command` | hex string | yes | Full signed packet incl. 64-byte signature. See [command-protocol.md](../command-protocol.md) |
| `is_admin_queue_item` | boolean | no | `false` for immediate commands |

The target UUID inside the signed packet must equal `device_uuid`.

### Example commands

| Action | Opcode | Payload | Packet length |
|---|---:|---|---|
| Lock | 54 | `01 0B` | 104 B / 208 hex |
| Unlock | 54 | `00 0B` | 104 B / 208 hex |
| Last history event | 20 | `00 00 01` | 105 B / 210 hex |

## Response (`BridgeSendOutput`)

```json
{
  "message_id": "<opaque id>",
  "max_waiting_time_in_seconds": 30
}
```

| Field | Type | Optional | Description |
|---|---|---|---|
| `message_id` | string | yes | ID to poll with `/v1/bridge/receive` ✅ |
| `max_waiting_time_in_seconds` | integer | yes | How long to poll. App defaults to 30 when missing 🔍 |

A `message_id` is a receipt, **not** proof the bolt moved.

## Notes

- The app's normal lock/unlock path does **not** call `/v1/bridge/command/authorize` first. 🔍
- If this call times out, the command may still have been delivered. Never resend lock/unlock automatically; see [errors.md](../errors.md#never-auto-retry-a-physical-command).
- Next step: [post-v1-bridge-receive.md](post-v1-bridge-receive.md).
