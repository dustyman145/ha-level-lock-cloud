# Data models

Field names are **case-sensitive** and inconsistent (`Location`, `LocationUUID`, `devices`, `DeviceUUID`, `bridge_uuid`). Copy them exactly.

Source: the app's serializers in `co.level.network.openapi.models.*` 🔍. "Optional" means the serializer allows the field to be missing. Missing and `null` are different cases.

Type notes:

- `HexData` serialises as a hex string.
- Enums serialise as scalars (numbers for the bolt/role codes below).
- `SemanticVersion` serialises as `"major.minor.patch.build"`.
- `Instant` is a timestamp; exact string format ❓.

## Example account (trimmed) ✅ shape

Synthetic values. Not a complete response.

```json
{
  "account": {
    "uuid": "00000000-0000-0000-0000-000000000001",
    "encryptedBlobKeys": [
      { "name": "password", "nonce": "<hex|base64>", "value": "<hex|base64>" }
    ],
    "blob": { "nonce": "<hex>", "value": "<hex>", "sign": "<hex>" },
    "Location": [
      {
        "LocationUUID": "00000000-0000-0000-0000-000000000004",
        "LocationName": "Example home",
        "Time_zone": "America/Toronto",
        "devices": [
          {
            "DeviceUUID": "00000000-0000-0000-0000-000000000002",
            "name": "Front Door",
            "BoltState": 1,
            "AccessMap": [
              {
                "AccessMap_account_uuid": "00000000-0000-0000-0000-000000000001",
                "AccessMap_role": 0,
                "AccessMap_index": 0,
                "AccessMap_key": []
              }
            ],
            "UserList": [
              {
                "share_account_uuid": "00000000-0000-0000-0000-000000000001",
                "access_level": 1,
                "access_from": null,
                "access_until": null,
                "rrule": null
              }
            ],
            "bridge": {
              "bridge_uuid": "00000000-0000-0000-0000-000000000003",
              "active": true,
              "reachable": true
            }
          }
        ]
      }
    ]
  }
}
```

Whether the server wraps the account in `"account"` is not certain; the PoC accepts both (`response.get("account", response)`). ⚙️

---

## `Account`

| Field | Type | Optional | Notes |
|---|---|---|---|
| `uuid` | UUID | no | Sender UUID in signed commands ✅ |
| `status` | `Status` | no | |
| `userID` | string | no | Sign-in identifier |
| `name` | `PersonName` | no | |
| `type` | `Type` | no | |
| `blob` | `Blob` | no | Encrypted signing key ✅ |
| `emails` | `Email[]` | no | |
| `phoneNumbers` | `PhoneNumber[]` | no | |
| `encryptedBlobKeys` | `EncryptedBlobKey[]` | no | ✅ |
| `locationsDisplayOrder` | `LocationOrderItem[]` | no | |
| `Location` | `LocationItem[]` | no | Capital **L** ✅ |
| `messages` | `MessageItem[]` | no | |
| `signatures` | `SignatureItem[]` | no | |
| `adminSessions` | `AdminSessionItem[]` | no | |
| `created` | Instant | no | |
| `updated` | Instant | no | |
| `canonicalID` | string | yes | |
| `linked_platforms` | `PartnerType[]` | yes | |
| `passes` | `Pass[]` | yes | Absent on the owner's account ✅ |
| `nfc_tags` | `NfcTagsListItem[]` | yes | |
| `photo_url` | string | yes | |
| `device_settings` | `AccountDeviceSettings[]` | yes | |
| `account_groups` | string[] | yes | |
| `service_type` | `ServiceType` | yes | |
| `terms_current` | Instant | yes | |
| `terms_accepted` | Instant | yes | |
| `has_mdu_link` | boolean | yes | |

## `LocationItem`

| Field | Type | Optional | Notes |
|---|---|---|---|
| `LocationUUID` | UUID | no | |
| `LocationName` | string | no | |
| `Time_zone` | string | no | IANA zone |
| `CanonicalID` | string | no | |
| `devices` | `DeviceItem[]` | no | Locks ✅ |
| `devicesDisplayOrder` | `DeviceOrderItem[]` | no | |
| `Address` | `Address` | yes | |
| `bridges` | `BridgeItem[]` | yes | |
| `keypads` | `KeypadItem[]` | yes | |
| `photo_url` | string | yes | |

## `DeviceItem` (a lock)

| Field | Type | Optional | Notes |
|---|---|---|---|
| `DeviceUUID` | UUID | no | Lock ID; used as `device_uuid` and target UUID ✅ |
| `name` | string | no | Display name ✅ |
| `DeviceName` | string | no | Fallback name |
| `BoltState` | `BoltState` | no | Cached state, see [codes](#bolt-state) |
| `SerialNumber` | string | no | |
| `Product` | `Product` | no | Model ❓ values |
| `CurrentFirmwareInfo` | `CurrentFirmwareInfo` | no | Firmware version |
| `AccessMap` | `AccessMapItem[]` | no | |
| `DeviceInvites` | `DeviceInviteItem[]` | no | |
| `AutoLockTimeout` | integer | no | |
| `AutoUnlock` | boolean | no | |
| `KnockToLock` | boolean | no | |
| `EnableNotifications` | boolean | no | |
| `SoundVolume` | `SoundVolume` | no | |
| `EnableVacationMode` | boolean | no | |
| `CalibrationCount` | integer | no | |
| `BeaconMajorVersion` | integer | no | |
| `BeaconMinorVersion` | integer | no | |
| `device_publicKey` | bytes | no | Lock's own key; not used for commands |
| `device_ctpublickeyid` | integer | no | |
| `CanonicalID` | string | yes | |
| `TouchToLock` | boolean | yes | |
| `TouchToLockTimeout` | `TouchToLockTimeout` | yes | |
| `TouchToUnlock` | boolean | yes | |
| `homekit_state` | boolean | yes | |
| `door_sense_state` | `DoorSenseState` | yes | Door open/closed, see [codes](#door-sense-state) |
| `door_sense_on` | boolean | yes | |
| `EnableSound` | boolean | yes | |
| `BeaconTxPower` | `TxPower` | yes | |
| `BLETxPower` | `TxPower` | yes | |
| `subbrand` | `Subbrand` | yes | |
| `Created` | Instant | yes | |
| `Updated` | Instant | yes | Not the time `BoltState` was measured |
| `OwningCount` | integer | yes | |
| `adminQueue` | `AdminQueueItem[]` | yes | |
| `OperationEvent` | `OperationEvent` | yes | |
| `OperationEventV2` | `OperationEventV2` | yes | |
| `OperationHistory` | `OperationHistoryEvent[]` | yes | |
| `TargetFirmwareInfo` | `TargetFirmwareInfo` | yes | |
| `UserList` | `UserListItem[]` | yes | Who has access ✅ |
| `metadata` | `DeviceMetadata` | yes | |
| `sidewalk` | `DeviceSidewalkInfo` | yes | |
| `AdvertisingDataV2` | `AdvertisingDataV2` | yes | |
| `LastBoltOperationV2` | `DeviceItemLastBoltOperationV2` | yes | Last operation, with timestamp |
| `bridge` | `DeviceItemBridge` | yes | Present when the lock has a Level Connect ✅ |

Battery level is in `AdvertisingDataV2.battery_level`; see below.

## `AdvertisingDataV2` 🔍

Status the lock advertised over Bluetooth, uploaded to the cloud by the app or bridge. Another cached state source, with its own timestamp. How often it is refreshed with a bridge ❓.

| Field | Type | Optional | Notes |
|---|---|---|---|
| `product_id` | integer | no | |
| `bolt_state` | `BoltState` | no | [codes](#bolt-state) |
| `battery_level` | `BatteryLevel` | no | [codes](#battery-level): coarse, not a percentage |
| `is_time_stale` | boolean | no | Lock clock not synced |
| `dsn` | integer | no | |
| `timestamp` | Instant | no | |
| `bolt_operation_source` | `BoltOperationSource` | no | |
| `bolt_operation_result` | `BoltOperationResult` | no | |
| `firmware_version` | string | no | |
| `nonce_byte` | integer | no | |
| `is_homekit_paired` | boolean | yes | |
| `is_sidewalk_provisioned` | boolean | yes | |
| `is_sidewalk_registered` | boolean | yes | |
| `door_sense_state` | `DoorSenseState` | yes | [codes](#door-sense-state) |
| `is_matter_paired` | boolean | yes | |

## `DeviceItemBridge`

| Field | Type | Optional | Notes |
|---|---|---|---|
| `bridge_uuid` | UUID | yes | Bridge ID. **Not** used as the target of `bridge/send` |
| `active` | boolean | yes | |
| `reachable` | boolean | yes | Cached; may be stale |

## `DeviceItemLastBoltOperationV2`

| Field | Type | Optional |
|---|---|---|
| `timestamp` | Instant | no |
| `bolt_operation_source` | `BoltOperationSource` | no |
| `bolt_state` | `BoltState` | no |
| `bolt_operation_result` | `BoltOperationResult` | yes |
| `operator` | `OperationEventOperator` | yes |
| `dsn` | integer | yes |

## `UserListItem`

| Field | Type | Optional | Notes |
|---|---|---|---|
| `share_account_uuid` | UUID | no | Match to `account.uuid` |
| `access_level` | `AccessLevel` | no | See [codes](#access-level-userlist) |
| `email` | string | yes | |
| `phonenumber` | string | yes | |
| `name` | `PersonName` | yes | |
| `access_from` | Instant | yes | Schedule start |
| `access_until` | Instant | yes | Schedule end |
| `photo_url` | string | yes | |
| `rrule` | `RRule` | yes | Recurring schedule |

## `AccessMapItem`

| Field | Type | Optional | Notes |
|---|---|---|---|
| `AccessMap_account_uuid` | UUID | no | |
| `AccessMap_role` | `AccessMapRole` | no | See [codes](#accessmap-role) |
| `AccessMap_index` | integer | no | Meaning ❓ |
| `AccessMap_key` | integer[] | no | 33 values live; format ❓; not a usable public key check |

## `CurrentFirmwareInfo`

| Field | Type |
|---|---|
| `phase` | `BuildPhase` |
| `version` | `SemanticVersion` (string) |
| `build_config` | `DeviceFirmwareBuildConfig` |
| `build_type` | `DeviceFirmwareBuildType` |
| `updated` | Instant |

## `Blob`

| Field | Type | Notes |
|---|---|---|
| `nonce` | hex | 12 bytes |
| `value` | hex | Encrypted BSON |
| `sign` | hex | Raw `r‖s` ECDSA-SHA512 over `value` |

## `EncryptedBlobKey`

| Field | Type | Notes |
|---|---|---|
| `name` | `Name` | `password` or recovery-key entry |
| `nonce` | string | 24-char hex or Base64 |
| `value` | string | 64-char hex or Base64 |

## Login, bridge and pass models

Documented on their endpoint pages:

- `LoginInputSchema`, `LoginRespSchema`: [post-v2-login.md](endpoints/post-v2-login.md)
- `BridgeSendInput`, `BridgeSendOutput`: [post-v1-bridge-send.md](endpoints/post-v1-bridge-send.md)
- `BridgeReceiveInput`, `BridgeReceiveOutput`: [post-v1-bridge-receive.md](endpoints/post-v1-bridge-receive.md)
- Other bridge and pass models: [other-routes.md](endpoints/other-routes.md)

---

## Enum codes 🔍

### Bolt state

| Code | Firmware name | Meaning |
|---:|---|---|
| 0 | `RETRACTED` | Unlocked |
| 1 | `EXTENDED` | Locked |
| 2 | `PARTIAL` | Partially locked (jammed); not secure |
| 3 | `UNKNOWN` | Unknown; not secure |

### Battery level

| Code | Name |
|---:|---|
| 0 | `UNKNOWN` |
| 1 | `RED` (low) |
| 2 | `YELLOW` |
| 3 | `GREEN` (good) |

### Door sense state

| Code | Name |
|---:|---|
| -1 | `UNKNOWN` |
| 0 | `NOT_SUPPORTED` |
| 1 | `DOOR_OPEN` |
| 2 | `DOOR_CLOSED` |
| 3 | `NOT_CALIBRATED` |

### Operation result

| Code | Name |
|---:|---|
| 0 | `SUCCESS` |
| 1 | `TIMEOUT` |
| 2 | `STALL` |
| 3 | `INTERNAL_ERROR` |
| 4 | `ALREADY_THERE` |
| 5 | `BATTERY_VOLTAGE_DROOPED` |
| 6 | `INVALID_INSTALL` |
| 7 | `BATTERY_CRITICALLY_LOW` |
| 8 | `DOOR_OPEN` |
| 9 | `UNKNOWN` |

### Operation source

| Code | Name | Code | Name |
|---:|---|---:|---|
| 0 | `UNKNOWN` | 8 | `NFC` |
| 1 | `MANUAL` | 9 | `ZIGBEE` |
| 2 | `BLE` | 10 | `TOUCH` |
| 3 | `HOME_KIT` | 11 | `REMOTE` (used by our commands) |
| 4 | `CONSOLE` | 12 | `RING` |
| 5 | `AUTO_LOCK` | 13 | `ALEXA` |
| 6 | `MATTER` | 14 | `KEYPAD` |
| 7 | `APPROACH_TO_UNLOCK` | 15 | `GOOGLE` |

### AccessMap role

| Code | Meaning |
|---:|---|
| -1 | Unknown |
| 0 | Owner |
| 1 | Admin |
| 2 | Guest |
| 3 | Any |

### Access level (UserList)

| Code | Meaning |
|---:|---|
| -1 | Unknown |
| 0 | Guest |
| 1 | Admin |

The two role enums use different numbers. `AccessMap_role: 0` is **owner**, but `access_level: 0` is **guest**.
