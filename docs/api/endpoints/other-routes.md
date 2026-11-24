# Other routes found in the APK

**Evidence:** 🔍 From APK only. None called. A route string proves the app knows the route, not that it works or what headers it needs.
**Used by integration:** no (listed for completeness)

Split a route into its own page using [`_template.md`](_template.md) once it is investigated further.

## Bridge routes (`_.ix1`, all POST)

| Route | Request fields | Response fields | Notes |
|---|---|---|---|
| `/v1/bridge/send` | | | See [post-v1-bridge-send.md](post-v1-bridge-send.md) ✅ |
| `/v1/bridge/receive` | | | See [post-v1-bridge-receive.md](post-v1-bridge-receive.md) ✅ |
| `/v1/bridge/command/authorize` | `bridge_uuid`, `authorization_nonce` (string), `command` (string) | `command` (hex) | Not required for normal lock/unlock |
| `/v1/bridge/owning/authorize` | `bridge_uuid`, `lock_uuid`, `current_firmware_info`, `bridge_nonce` (bytes), `service_public_key_id` (int) | `own_bridge_command` (hex) | Bridge pairing |
| `/v1/bridge/own` | `bridge_uuid`, `lock_uuid`, `current_firmware_info`, `own_bridge_response` (bytes), `service_public_key_id` (int), `add_service_user_command` (bytes) | ❓ | Bridge pairing |
| `/v1/bridge/unown` | `bridge_uuid` | ❓ | Unpair bridge. Do not call |
| `/v1/bridge/state/update` | `bridge_uuid`, optional `wifi_ssid` | ❓ | Updates bridge info; not a bolt-state read |
| `/v1/bridge/ble-peripheral-mode/set` | `bridge_uuid`, `duration_in_seconds` (int) | ❓ | App uses 60 s |

## Pass routes (`_.yab`, `_.pe`, all POST)

Passes are shareable credentials (guest access). Not needed for owner accounts.

| Route | Purpose |
|---|---|
| `/v2/pass/create` | Create a pass (`PassCreateInput`) |
| `/v2/pass/{pass_url_id}/accept` | Accept a pass link |
| `/v2/pass/{pass_uuid}/delete` | Delete a pass |
| `/v2/pass/{pass_uuid}/update` | Update a pass |
| `/v2/account/pass/create` | Create an account from a pass (`AccountPassCreateInput`) |

### Pass models

| Model | Fields |
|---|---|
| `Pass` | `version`, `uuid`, `name`, `url`, `url_id`, `private_key` (hex), `public_key` (hex), `location` (`PassLocation`, single object), `admin` |
| `PassLocation` | `uuid`, `schedule`, `devices` |
| `PassDevice` | `uuid` |
| `PassSchedule` | `type`, optional `fixed` |
| `PassScheduleFixed` | `start_time`, `end_time` |
| `PassCreateInput` | `uuid`, `name`, `private_key`, `public_key`, `location`, `admin_commands` |
| `PassAdminCommand` | `device_uuid`, `command` |
| `AccountPassCreateInput` | `user_id`, `password`, `public_key`, `blob`, `blob_keys`, `pass_url_id`, optional `secp256r1_public_key` |

## Account routes (`_.pe`)

| Method | Route |
|---|---|
| POST | `/v2/account/create` |
| POST | `/v2/account/action` |
| POST | `/v1/account/edit` |
| POST | `/v1/account/delete` |
| POST | `/v1/account/verify` |
| POST | `/v1/account/verification-code/resend` |
| POST | `/v1/account/password/change` |
| POST | `/v1/account/photo/set` |
| GET | `/v1/account/photo/get/{account_uuid}/{photo_file}` |
| POST | `/v1/recover` |
| POST | `/v1/recovery-key` |
| POST | `/v1/reserve` |

2FA routes: see [2fa.md](2fa.md). Logout: [post-v2-logout.md](post-v2-logout.md).

## OAuth device-code integration routes (`_.moa`)

Used by the app to approve third-party integrations (a Level Connect integration feature exists behind a feature flag). The owner's app does not show a Home Assistant linking option. No token exchange or client registration was found, so this is **not** a usable official path for Home Assistant yet.

| Method | Route |
|---|---|
| POST | `/v1/oauth2/device-code/verify` |
| POST | `/v1/oauth2/device-code/integrations/list` |
| GET | `/v1/oauth2/device-code/integrations/{link_uuid}/devices` |
| POST | `/v1/oauth2/device-code/integrations/{link_uuid}/devices/update` |
| POST | `/v1/oauth2/device-code/integrations/{link_uuid}/revoke` |
