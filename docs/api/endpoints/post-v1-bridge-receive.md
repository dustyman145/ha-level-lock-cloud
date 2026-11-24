# `POST /v1/bridge/receive`

**Purpose:** Poll for the result of a command sent with `/v1/bridge/send`.
**Evidence:** ✅ Verified
**Source:** `_.ix1`, `_.et1`, `BridgeReceiveInput`, `BridgeReceiveOutput`
**Used by integration:** yes

## Request

| Part | Value |
|---|---|
| URL | `https://api.level.co/v1/bridge/receive` |
| Auth | `AccessToken` header |

### Body (`BridgeReceiveInput`)

```json
{ "message_id": "<message_id from send>" }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message_id` | string | yes | From the `send` response |

## Response (`BridgeReceiveOutput`)

```json
{
  "state": "success",
  "payload": "<hex response bytes>"
}
```

| Field | Type | Optional | Description |
|---|---|---|---|
| `state` | string | yes | `in_progress`, `success`, `timeout`, `error`, `unknown` |
| `payload` | hex string | yes | Binary lock response; present on `success` |

### States

| `state` | Action |
|---|---|
| `in_progress` | Wait ~1 s and poll again with the same `message_id` |
| `success` | Hex-decode `payload` and parse it ([command-protocol.md](../command-protocol.md)) |
| `timeout` / `error` / `unknown` / other | Outcome unknown. Do not resend a lock/unlock |

`state: "success"` means the lock answered, not that the operation succeeded. Check the parsed bolt state and result code.

## Polling

| Setting | Value |
|---|---|
| Interval | ~1 s 🔍 |
| Window | `max_waiting_time_in_seconds` from send, default 30 s 🔍 |
| PoC hard cap | 120 s ⚙️ |
