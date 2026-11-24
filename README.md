# Level Lock Cloud for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/dustyman145/ha-level-lock-cloud/actions/workflows/validate.yml/badge.svg)](https://github.com/dustyman145/ha-level-lock-cloud/actions/workflows/validate.yml)

A Home Assistant custom integration to lock and unlock **Level** smart locks through the Level cloud, with battery, door and activity sensors. Locks are standard `lock` entities, so they work from dashboards, automations and **Node-RED**.

> ⚠️ **Unofficial.** The Level cloud API is undocumented. It was reverse engineered from the official Level Android app (see [`docs/api/`](docs/api/)) and may change or stop working at any time. This project is not affiliated with or endorsed by Level Home Inc.

> 🧪 **Alpha.** Lock/unlock has been confirmed on real hardware with the same protocol. The Home Assistant integration itself is new; please report issues with debug logs.

## Requirements

- A Level lock paired with a **Level Connect** (Wi-Fi bridge). Locks without a bridge get sensors only, no lock entity.
- Your Level account email (or phone number) and password. An owner or admin account is required to send commands.

## Features

| Entity | Shown when | Notes |
|---|---|---|
| Lock | Lock has a Level Connect | Locked / unlocked / jammed; locking and unlocking states while a command runs |
| Door (binary sensor) | Lock reports door sense | Open / closed. Not created for locks without door sense |
| Battery (binary sensor) | Battery level reported | On when the battery is low |
| Battery level (sensor) | Battery level reported | Low / medium / high (Level only reports a coarse level, not %) |
| Last activity (sensor) | Reported by the cloud | How the lock was last operated: keypad, manual, auto-lock, remote, … |
| Last activity time (sensor) | Reported by the cloud | When that happened |
| Level Connect (diagnostic) | Lock has a bridge | Whether the bridge is reachable |

Other behaviour:

- **Two-factor authentication** is supported during setup and re-authentication.
- State is polled from the Level cloud every 60 seconds and updated immediately from the lock's own reply after each lock/unlock.
- A command that fails or whose outcome is unknown raises an error and is **never retried automatically** (the lock may have moved).
- An event `level_lock_cloud_state_changed` is fired when a lock's state changes.
- Diagnostics download with identifiers and secrets removed.

## Installation

### HACS (recommended)

1. HACS → menu → **Custom repositories**.
2. Add `https://github.com/dustyman145/ha-level-lock-cloud`, category **Integration**.
3. Install **Level Lock Cloud** and restart Home Assistant.

### Manual

Copy `custom_components/level_lock_cloud` into your `config/custom_components/` folder and restart.

## Configuration

**Settings → Devices & Services → Add Integration → Level Lock Cloud**, then sign in. If your account has 2FA, choose email or text message and enter the code.

Your password is stored in Home Assistant's configuration (like other cloud integrations). It is required: lock commands are signed with a key that can only be decrypted with your password.

## Usage

### Actions

```yaml
action: lock.unlock
target:
  entity_id: lock.front_door
```

### Node-RED

Needs [node-red-contrib-home-assistant-websocket](https://github.com/zachowj/node-red-contrib-home-assistant-websocket) (included with the Node-RED add-on).

- **Control:** *Action* node with `lock.lock` / `lock.unlock` on the lock entity.
- **State:** *Events: state* / *Trigger: state* nodes on the lock, door or battery entities.
- **Events:** *Events: all* node with event type `level_lock_cloud_state_changed`. Payload: `{ lock_id, name, locked, bolt_state, source }`.

Example flows (Menu → Import, then set your server and entity IDs):

- [`examples/node-red-flow.json`](examples/node-red-flow.json): lock/unlock buttons and the state-change event.
- [`examples/alarm-manager-unlock-flow.json`](examples/alarm-manager-unlock-flow.json): unlock a Level lock when **UniFi Alarm Manager** calls a webhook (bearer token, skips if already unlocked). Setup: [`examples/README.md`](examples/README.md).

## Troubleshooting

Enable debug logging:

```yaml
logger:
  logs:
    custom_components.level_lock_cloud: debug
```

Tokens, passwords and keys are never logged.

## Development

```bash
pip install -r requirements_test.txt
pytest
```

Tests run against a mocked Level cloud with a synthetic encrypted account; no real account is used.

## API documentation

[`docs/api/`](docs/api/) documents every known endpoint, the binary lock protocol and the data models.

## License

MIT. See [LICENSE](LICENSE).
