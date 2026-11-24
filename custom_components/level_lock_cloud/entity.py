"""Base entity for Level Lock Cloud."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import LevelCoordinator
from .models import LevelLock


class LevelEntity(CoordinatorEntity[LevelCoordinator]):
    """Common device info and availability."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LevelCoordinator, lock_id: str, key: str) -> None:
        super().__init__(coordinator)
        self._lock_id = lock_id
        lock = coordinator.data[lock_id]
        self._attr_unique_id = f"{lock_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, lock_id)},
            name=lock.name,
            manufacturer=MANUFACTURER,
            model=lock.model,
            sw_version=lock.firmware,
            serial_number=lock.serial,
            suggested_area=lock.location,
        )

    @property
    def lock(self) -> LevelLock:
        """Current data for this lock."""
        return self.coordinator.data[self._lock_id]

    @property
    def available(self) -> bool:
        return super().available and self._lock_id in self.coordinator.data
