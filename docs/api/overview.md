# Overview

## Source

| Item | Value |
|---|---|
| App | Level Home |
| Package | `co.level.app` |
| Version analysed | 2.5.0.56 |
| APKS SHA-256 | `905cff1d6971700f3f35bc28432948b2a6d79387cc31ba9b18f349df9a915853` |
| Decompiler used | JADX 1.5.6 (owner, 414 errors; critical branches checked against raw bytecode) and JADX 1.5.3 (2FA / battery tracing, 94 errors) |
| Analysis date | 2026-11-23 |

Obfuscated class names (e.g. `_.et1`) are specific to this build. They change between app versions.

## Host

| Purpose | Base URL | Evidence |
|---|---|---|
| Account + bridge API | `https://api.level.co` | ✅ |

## Common headers

| Header | Value | When | Evidence |
|---|---|---|---|
| `Accept` | `application/json` | All requests | ✅ |
| `Content-Type` | `application/json` | All requests | ✅ |
| `AccessToken` | `<ACCESS_TOKEN>` | Every request after login | ✅ |
| `X-Allow-TFA` | `1` | `POST /v2/login` | ✅ sent; enables the HTTP 202 2FA challenge 🔍 |
| `Client-App-ID` | `<id>` | Optional on `POST /v2/logout` | 🔍 |

The session token is sent in a header literally named `AccessToken`. It is **not** `Authorization: Bearer`, and no cookies are used. ✅

## The three layers

Keep these separate when implementing or debugging:

| Layer | What it is | Pages |
|---|---|---|
| 1. HTTPS / account | JSON over HTTPS with `AccessToken` | [authentication.md](authentication.md), [endpoints/](endpoints/) |
| 2. Bridge transport | `send` returns a `message_id`; `receive` is polled until a terminal `state` | [post-v1-bridge-send.md](endpoints/post-v1-bridge-send.md), [post-v1-bridge-receive.md](endpoints/post-v1-bridge-receive.md) |
| 3. Lock firmware | Binary signed commands and binary responses, hex-encoded inside the JSON | [command-protocol.md](command-protocol.md) |

A `2xx` from layer 1 or `state: "success"` from layer 2 does **not** mean the bolt moved. Only a parsed layer-3 response says that.

## Three different "versions"

| Thing | Example | Meaning |
|---|---|---|
| HTTP route version | `/v2/login`, `/v1/bridge/send` | Server API route version |
| Firmware envelope protocol | byte `0x01` in the command packet | Command framing version (`V2_0` enum) |
| Command variant | `BoltControllerOperateV3` | Opcode variant name |

Do not substitute one for another.

## Transport notes

| Topic | Status |
|---|---|
| TLS certificate pinning | ❓ not investigated |
| Realtime / push channel (WebSocket, MQTT, FCM) | ❓ not investigated |
| Rate limits | ❓ |
| HTTP timeout used by PoC client | 25 s per request ⚙️ |

## Supported hardware path

Both tested locks are reached **through a Level Connect (Wi-Fi) bridge**. The cloud forwards the signed command to the bridge, which talks to the lock over Bluetooth. Locks without a bridge cannot be controlled through this API. ✅ (for the owner's Front Door)
