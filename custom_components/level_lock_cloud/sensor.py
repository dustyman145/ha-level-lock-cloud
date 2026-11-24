"""Sensors for Level Lock Cloud: battery level, last activity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import BATTERY_LEVELS, OPERATION_SOURCES
from .coordinator import LevelConfigEntry, LevelCoordinator
from .entity import LevelEntity
from .models import LevelLock

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class LevelSensorDescription(SensorEntityDescription):
    """Describes a Level sensor."""

    value_fn: Callable[[LevelLock], str | datetime | None]
    exists_fn: Callable[[LevelLock], bool]


DESCRIPTIONS: tuple[LevelSensorDescription, ...] = (
    LevelSensorDescription(
        key="battery_level",
        translation_key="battery_level",
        device_class=SensorDeviceClass.ENUM,
        options=list(BATTERY_LEVELS.values()),
        value_fn=lambda lock: BATTERY_LEVELS.get(lock.battery_level),
        exists_fn=lambda lock: lock.battery_level not in (None, 0),
    ),
    LevelSensorDescription(
        key="last_activity",
        translation_key="last_activity",
        device_class=SensorDeviceClass.ENUM,
        options=list(OPERATION_SOURCES.values()),
        value_fn=lambda lock: OPERATION_SOURCES.get(lock.last_source),
        exists_fn=lambda lock: lock.last_source is not None,
    ),
    LevelSensorDescription(
        key="last_activity_time",
        translation_key="last_activity_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda lock: lock.last_time,
        exists_fn=lambda lock: lock.last_time is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LevelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors; unsupported ones are not created."""
    coordinator = entry.runtime_data
    async_add_entities(
        LevelSensor(coordinator, lock_id, description)
        for lock_id, lock in coordinator.data.items()
        for description in DESCRIPTIONS
        if description.exists_fn(lock)
    )


class LevelSensor(LevelEntity, SensorEntity):
    """A Level sensor."""

    entity_description: LevelSensorDescription

    def __init__(
        self,
        coordinator: LevelCoordinator,
        lock_id: str,
        description: LevelSensorDescription,
    ) -> None:
        super().__init__(coordinator, lock_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | datetime | None:
        return self.entity_description.value_fn(self.lock)
