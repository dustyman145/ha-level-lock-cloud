"""Constants for the Level Lock Cloud integration."""

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "level_lock_cloud"
MANUFACTURER: Final = "Level Home"

CONF_TOKEN: Final = "token"

DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=60)

# How long a confirmed lock/unlock result overrides the (possibly stale) cloud cache.
COMMAND_OVERRIDE_SECONDS: Final = 120

# Event fired on the HA bus when a lock's state changes (handy as a Node-RED trigger).
EVENT_LOCK_STATE_CHANGED: Final = f"{DOMAIN}_state_changed"

PLATFORMS: Final = [Platform.BINARY_SENSOR, Platform.LOCK, Platform.SENSOR]

# Enum codes, see docs/api/models.md
BOLT_UNLOCKED: Final = 0
BOLT_LOCKED: Final = 1
BOLT_PARTIAL: Final = 2
BOLT_UNKNOWN: Final = 3

BATTERY_LEVELS: Final = {1: "low", 2: "medium", 3: "high"}

DOOR_OPEN: Final = 1
DOOR_CLOSED: Final = 2
DOOR_NOT_CALIBRATED: Final = 3

OPERATION_SOURCES: Final = {
    0: "unknown",
    1: "manual",
    2: "bluetooth",
    3: "homekit",
    4: "console",
    5: "auto_lock",
    6: "matter",
    7: "approach_to_unlock",
    8: "nfc",
    9: "zigbee",
    10: "touch",
    11: "remote",
    12: "ring",
    13: "alexa",
    14: "keypad",
    15: "google",
}

OPERATION_RESULTS: Final = {
    0: "success",
    1: "timeout",
    2: "stall",
    3: "internal_error",
    4: "already_there",
    5: "battery_voltage_drooped",
    6: "invalid_install",
    7: "battery_critically_low",
    8: "door_open",
    9: "unknown",
}
RESULT_SUCCESS: Final = 0
RESULT_ALREADY_THERE: Final = 4
