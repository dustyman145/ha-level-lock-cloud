"""The Level Lock Cloud integration."""

from __future__ import annotations

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LevelApiClient
from .const import CONF_TOKEN, PLATFORMS
from .coordinator import LevelConfigEntry, LevelCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: LevelConfigEntry) -> bool:
    """Set up Level Lock Cloud from a config entry."""
    client = LevelApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        token=entry.data.get(CONF_TOKEN),
    )
    coordinator = LevelCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LevelConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
