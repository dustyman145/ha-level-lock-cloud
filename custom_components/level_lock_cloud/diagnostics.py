"""Diagnostics for Level Lock Cloud (no secrets or identifiers)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import LevelConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LevelConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics."""
    coordinator = entry.runtime_data
    locks = []
    for index, lock in enumerate((coordinator.data or {}).values()):
        data = asdict(lock)
        data["uuid"] = f"lock_{index}"
        data["serial"] = "**REDACTED**" if data["serial"] else None
        data["last_time"] = lock.last_time.isoformat() if lock.last_time else None
        locks.append(data)
    return {
        "last_update_success": coordinator.last_update_success,
        "locks": locks,
    }
