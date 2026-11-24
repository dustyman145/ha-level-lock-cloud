"""Parse the Level account response into simple lock objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _int(value: Any) -> int | None:
    """Enums arrive as numbers or numeric strings."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(seconds, UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return str(value.get("version") or value.get("name") or "") or None
    return str(value)


@dataclass(slots=True)
class LevelLock:
    """A Level lock as reported by the account inventory."""

    uuid: str
    name: str
    location: str | None
    bolt_state: int | None
    has_bridge: bool
    bridge_reachable: bool | None
    battery_level: int | None
    door_state: int | None
    door_sense_on: bool | None
    last_source: int | None
    last_result: int | None
    last_time: datetime | None
    firmware: str | None
    serial: str | None
    model: str | None

    @property
    def supports_door_sense(self) -> bool:
        """True when the lock reports a door open/closed state."""
        return bool(self.door_sense_on) or self.door_state in (1, 2, 3)


def parse_locks(account: dict[str, Any]) -> dict[str, LevelLock]:
    """Return all locks in the account keyed by DeviceUUID."""
    locks: dict[str, LevelLock] = {}
    for location in account.get("Location") or []:
        for device in location.get("devices") or []:
            device_uuid = device.get("DeviceUUID")
            if not device_uuid:
                continue
            bridge = device.get("bridge") or None
            adv = device.get("AdvertisingDataV2") or {}
            last = device.get("LastBoltOperationV2") or {}
            firmware = device.get("CurrentFirmwareInfo") or {}

            door_state = _int(device.get("door_sense_state"))
            if door_state is None:
                door_state = _int(adv.get("door_sense_state"))

            locks[str(device_uuid)] = LevelLock(
                uuid=str(device_uuid),
                name=device.get("name") or device.get("DeviceName") or "Level Lock",
                location=location.get("LocationName"),
                bolt_state=_int(device.get("BoltState")),
                has_bridge=isinstance(bridge, dict),
                bridge_reachable=_bool(bridge.get("reachable")) if isinstance(bridge, dict) else None,
                battery_level=_int(adv.get("battery_level")),
                door_state=door_state,
                door_sense_on=_bool(device.get("door_sense_on")),
                last_source=_int(last.get("bolt_operation_source")),
                last_result=_int(last.get("bolt_operation_result")),
                last_time=_datetime(last.get("timestamp")),
                firmware=_text(firmware.get("version")) or _text(adv.get("firmware_version")),
                serial=_text(device.get("SerialNumber")),
                model=_text(device.get("Product")),
            )
    return locks
