# Findings, open questions and log

Newest entries first. Once a finding is confirmed, move it to the relevant page and link to it from here.

## Open questions

Priority for the Home Assistant integration in **bold**.

- [x] ~~2FA request/response bodies~~ → traced from APK, see [2fa.md](endpoints/2fa.md). Live test still needed.
- [ ] **2FA live test: is a code sent automatically on the 202? Wrong-code errors?**
- [ ] **Token lifetime, expiry status code, refresh or re-login behaviour**
- [ ] **How fresh `DeviceItem.BoltState` / `AdvertisingDataV2` are after manual / keypad / auto-lock operations**
- [x] ~~Battery level~~ → `AdvertisingDataV2.battery_level` (0 unknown, 1 red, 2 yellow, 3 green)
- [x] ~~Door-sense values~~ → see [models.md](models.md#door-sense-state)
- [ ] Capture one real V3 lock/unlock response to confirm the 27-byte layout and timestamp base
- [ ] Error bodies: wrong password, expired token, unreachable bridge, no access
- [ ] `SystemStatusGet` (53) and `StateBroadcastGet` (90): live bolt/door state?
- [ ] Push / realtime channel (FCM, WebSocket) for state changes
- [ ] Multi-event history parsing and anchor pagination
- [ ] `AccessMap_key` format (33 integers)
- [ ] Guest / pass credentials (non-owner accounts)
- [ ] Rate limits, replay window, clock tolerance for command timestamps
- [ ] Garage lock: commands untested; which lock is Bluetooth vs Matter Bolt
- [ ] Locks without a Level Connect bridge: any cloud path?

## Corrections

Mistakes made during the investigation. Keep them so they are not repeated.

1. **Blob signature hash.** The account blob is verified with **SHA-512**, not SHA-256. Commands use SHA-256. The app registers two signers; the firmware one is qualified `ec_fw_sha256`.
2. **`AccessMap_key` is not a public key check.** Comparing it to the account public key gave a false negative and blocked commands. The app's resolver does not use it.
3. **`passes` absent ≠ no access.** The owner account has no `passes` field and works with the account key.
4. **Cached / history state ≠ current state.** `BoltState` and history records are last-reported values.

## Log

### 2026-11-24: 2FA flow, battery and door sense traced from APK
Source: APK 2.5.0.56 decompiled with JADX 1.5.3 (94 errors).
- Login returns **HTTP 202** when 2FA is required; app adds `tfaEnabled` itself (`_.kif.g`, `u87.Z` = 202). The 202 still carries an `AccessToken` header.
- `/v1/2fa/otp/send` body `{"method": "email"|"phone"}`; `/v1/2fa/confirm` body `{"hash": sha256(code).hex()[:12]}` (`_.ybf.r`); confirm returns the new token in the `AccessToken` header (`_.kif.a`).
- `/v1/2fa/contacts` body `{hashed_password, hashed_recovery_key}` (Base64, login derivation) → `{email, phone}`.
- `userID` phone numbers are normalised to international form without separators (`_.ygb`).
- Error body model `StandardError` = `{code, message, data: {seconds}}`.
- Battery: `DeviceItem.AdvertisingDataV2.battery_level` enum 0–3. Door sense enum -1..3.

### 2026-11-24: Wiki created from owner's investigation
Source: owner's notes (`LEVEL_CONNECT_API.md`, investigation log, PoC Python client), APK 2.5.0.56.
- Imported verified login, account, key decryption, command format, bridge send/receive, history and lock/unlock.
- Imported APK-only route inventory and models.
- Full APK decompilation in this repo's tooling is pending; 2FA bodies not yet traced.

### 2026-11-23: Front Door unlock confirmed
Source: live, owner. Opcode 54, payload `00 0B`. Bolt retracted. Response JSON not captured.

### 2026-11-23: Front Door lock confirmed
Source: live, owner. Opcode 54, payload `01 0B`. Bolt extended. Response JSON not captured.

### 2026-11-23: Read-only history succeeded
Source: live, owner. Opcode 20, payload `00 00 01`. Transport `success`, one event parsed: last operation lock / success. Confirms login, key decryption, command signing (SHA-256), packet framing, Level-epoch timestamp, bridge send/receive.

### 2026-11-23: Account key decrypted and verified
Source: live, owner. Worked after switching blob verification to SHA-512.

### 2026-11-23: Login and inventory
Source: live, owner. Two locks with bridge metadata; `passes` field absent.

## Proof-of-concept client

The owner wrote a standalone Python client during the investigation (not in this repo). Its structure, useful as a reference for `api.py`:

| File | Role |
|---|---|
| `level_cloud_account.py` | HTTPS helper, login derivation, `get_account_session()` |
| `level_owner_probe.py` | Blob decryption and signature check, `account_private_key()` |
| `level_bridge_client.py` | Lock selection, command building, send/poll, history and V3 parsing, `lock()` / `unlock()` / `status()` |

Tested with Python 3.14, `cryptography` 46.0.4, `pymongo` 4.20.1 (for `bson`). 32 offline tests with synthetic data.
