"""Lock platform for Level Lock Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import BOLT_LOCKED, BOLT_PARTIAL, BOLT_UNLOCKED, OPERATION_SOURCES
from .coordinator import LevelConfigEntry, LevelCoordinator
from .entity import LevelEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LevelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Level locks (only those reachable through a Level Connect bridge)."""
    coordinator = entry.runtime_data
    async_add_entities(
        LevelLockEntity(coordinator, lock_id)
        for lock_id, lock in coordinator.data.items()
        if lock.has_bridge
    )


class LevelLockEntity(LevelEntity, LockEntity):
    """A Level lock controlled through the cloud."""

    _attr_name = None

    def __init__(self, coordinator: LevelCoordinator, lock_id: str) -> None:
        super().__init__(coordinator, lock_id, "lock")
        self._operating: bool | None = None  # True = locking, False = unlocking

    @property
    def is_locked(self) -> bool | None:
        state = self.lock.bolt_state
        if state == BOLT_LOCKED:
            return True
        if state == BOLT_UNLOCKED:
            return False
        return None

    @property
    def is_jammed(self) -> bool:
        return self.lock.bolt_state == BOLT_PARTIAL

    @property
    def is_locking(self) -> bool:
        return self._operating is True

    @property
    def is_unlocking(self) -> bool:
        return self._operating is False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        lock = self.lock
        return {
            "last_changed_by": OPERATION_SOURCES.get(lock.last_source),
            "bridge_reachable": lock.bridge_reachable,
        }

    async def async_lock(self, **kwargs: Any) -> None:
        await self._operate(True)

    async def async_unlock(self, **kwargs: Any) -> None:
        await self._operate(False)

    async def _operate(self, lock: bool) -> None:
        self._operating = lock
        self.async_write_ha_state()
        try:
            await self.coordinator.async_operate(self._lock_id, lock)
        finally:
            self._operating = None
            self.async_write_ha_state()
