# Errors, timeouts and retries

## Three error layers

| Layer | Examples | Handling |
|---|---|---|
| HTTPS / auth | Non-2xx, socket timeout, bad JSON | Report; do not assume the command was not delivered |
| Bridge transport | `state`: `in_progress`, `success`, `timeout`, `error`, `unknown` | Keep polling `in_progress`; parse payload on `success`; others mean the outcome is unknown |
| Lock firmware | Operation result `SUCCESS`, `STALL`, `DOOR_OPEN`, … | Combine with reported bolt state to decide success |

A transport `timeout` and an operation result `TIMEOUT` are different things.

## Error body 🔍

The app parses non-2xx bodies as `StandardError` (`co.level.network.openapi.auth.StandardError`):

```json
{
  "code": 123,
  "message": "<text>",
  "data": { "seconds": 30 }
}
```

| Field | Type | Optional | Notes |
|---|---|---|---|
| `code` | integer | yes | Server error code; values ❓ |
| `message` | string | yes | |
| `data.seconds` | integer | yes | Probably a wait time for rate limiting (the app has a `RateLimitException`) ❓ |

If the body does not parse, the app raises `UnrecognizedErrorException` with the HTTP status.

## HTTP errors ❓

Exact status codes and `code` values have **not** been captured live. Fill this table in as they are observed:

| Situation | HTTP status | Body | Evidence |
|---|---|---|---|
| Wrong password | ❓ | `status` contains `loginFailed` | 🔍 |
| 2FA required | **202** | `status` may contain `tfaEnabled` | 🔍 |
| Expired / invalid token | ❓ | ❓ | |
| Lock unreachable | ❓ | ❓ | |
| Rate limited | ❓ | ❓ | |

## Bridge transport states

| `state` | Meaning |
|---|---|
| `in_progress` | Keep polling the same `message_id` |
| `success` | Response available in `payload`; still need to parse it |
| `timeout` | Outcome unknown |
| `error` | Transport error; bolt may or may not have moved |
| `unknown` | Outcome unknown |
| anything else | Treat as unknown |

## Polling timing

| Value | Source |
|---|---|
| Default wait when `max_waiting_time_in_seconds` missing | 30 s 🔍 |
| Poll interval | ~1 s 🔍 |
| Max polling window | 120 s ⚙️ |

## Never auto-retry a physical command

A send can time out **after** the server accepted it. If a lock/unlock outcome is unknown (no `message_id`, polling failed, unparseable or stale payload):

1. Report the outcome as unknown.
2. Optionally do **one read-only** history check (opcode 20).
3. Do **not** resend lock/unlock automatically. A new token after re-login is not a reason to replay.

For Home Assistant this means: raise an error on the service call and refresh state, rather than retrying.

## Firmware operation results

See [models.md → operation result](models.md#operation-result).
