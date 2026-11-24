"""Binary sensors for Level Lock Cloud: door, low battery, bridge connectivity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOOR_CLOSED, DOOR_OPEN
from .coordinator import LevelConfigEntry, LevelCoordinator
from .entity import LevelEntity
from .models import LevelLock

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class LevelBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a Level binary sensor."""

    value_fn: Callable[[LevelLock], bool | None]
    exists_fn: Callable[[LevelLock], bool]


def _door(lock: LevelLock) -> bool | None:
    if lock.door_state == DOOR_OPEN:
        return True
    if lock.door_state == DOOR_CLOSED:
        return False
    return None


DESCRIPTIONS: tuple[LevelBinarySensorDescription, ...] = (
    LevelBinarySensorDescription(
        key="door",
        translation_key="door",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=_door,
        exists_fn=lambda lock: lock.supports_door_sense,
    ),
    LevelBinarySensorDescription(
        key="battery_low",
        device_class=BinarySensorDeviceClass.BATTERY,
        value_fn=lambda lock: None if lock.battery_level is None else lock.battery_level == 1,
        exists_fn=lambda lock: lock.battery_level not in (None, 0),
    ),
    LevelBinarySensorDescription(
        key="bridge",
        translation_key="bridge",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: lock.bridge_reachable,
        exists_fn=lambda lock: lock.has_bridge,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LevelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors; unsupported ones are not created."""
    coordinator = entry.runtime_data
    async_add_entities(
        LevelBinarySensor(coordinator, lock_id, description)
        for lock_id, lock in coordinator.data.items()
        for description in DESCRIPTIONS
        if description.exists_fn(lock)
    )


class LevelBinarySensor(LevelEntity, BinarySensorEntity):
    """A Level binary sensor."""

    entity_description: LevelBinarySensorDescription

    def __init__(
        self,
        coordinator: LevelCoordinator,
        lock_id: str,
        description: LevelBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, lock_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.lock)
