# `POST /v2/logout`

**Purpose:** End the current session.
**Evidence:** 🔍 From APK only. Never called.
**Source:** `_.pe.v`
**Used by integration:** maybe, on config entry removal

## Request

| Part | Value |
|---|---|
| URL | `https://api.level.co/v2/logout` |
| Auth | `AccessToken` header ❓ (assumed, like other calls) |

### Headers

| Header | Value | Notes |
|---|---|---|
| `AccessToken` | `<ACCESS_TOKEN>` | ❓ |
| `Client-App-ID` | `<id>` | Optional 🔍. Value and meaning ❓ |

### Body

Empty "no data" model 🔍. Likely `{}` ❓.

## Response

Empty "no data" model 🔍.

## Unknowns

- Whether it revokes only this token or all sessions.
- What `Client-App-ID` is and where its value comes from.
