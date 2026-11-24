"""Data update coordinator for Level Lock Cloud."""

from __future__ import annotations

import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    LevelApiClient,
    LevelApiError,
    LevelAuthError,
    LevelCommandError,
    LevelCryptoError,
    LevelTwoFactorRequired,
)
from .const import (
    BOLT_LOCKED,
    BOLT_UNLOCKED,
    COMMAND_OVERRIDE_SECONDS,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_LOCK_STATE_CHANGED,
    OPERATION_RESULTS,
    OPERATION_SOURCES,
    RESULT_ALREADY_THERE,
    RESULT_SUCCESS,
)
from .models import LevelLock, parse_locks

_LOGGER = logging.getLogger(__name__)

type LevelConfigEntry = ConfigEntry[LevelCoordinator]


class LevelCoordinator(DataUpdateCoordinator[dict[str, LevelLock]]):
    """Polls the Level account and runs lock commands."""

    config_entry: LevelConfigEntry

    def __init__(self, hass: HomeAssistant, entry: LevelConfigEntry, client: LevelApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        # lock uuid -> (bolt state, monotonic time) from a confirmed command
        self._overrides: dict[str, tuple[int, float]] = {}

    async def _async_update_data(self) -> dict[str, LevelLock]:
        try:
            account = await self.client.get_account()
        except (LevelAuthError, LevelTwoFactorRequired, LevelCryptoError) as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LevelApiError as err:
            raise UpdateFailed(str(err)) from err

        self._save_token()
        locks = parse_locks(account)
        now = time.monotonic()
        for lock_id, lock in locks.items():
            override = self._overrides.get(lock_id)
            if override is None:
                continue
            state, at = override
            if now - at > COMMAND_OVERRIDE_SECONDS or lock.bolt_state == state:
                del self._overrides[lock_id]
            else:
                lock.bolt_state = state
        self._fire_changes(locks)
        return locks

    def _save_token(self) -> None:
        token = self.client.token
        if token and token != self.config_entry.data.get(CONF_TOKEN):
            self.hass.config_entries.async_update_entry(
                self.config_entry, data={**self.config_entry.data, CONF_TOKEN: token}
            )

    def _fire_changes(self, locks: dict[str, LevelLock]) -> None:
        if not self.data:
            return
        for lock_id, lock in locks.items():
            old = self.data.get(lock_id)
            if old is None or old.bolt_state == lock.bolt_state:
                continue
            self.hass.bus.async_fire(
                EVENT_LOCK_STATE_CHANGED,
                {
                    "lock_id": lock_id,
                    "name": lock.name,
                    "locked": lock.bolt_state == BOLT_LOCKED,
                    "bolt_state": lock.bolt_state,
                    "source": OPERATION_SOURCES.get(lock.last_source),
                },
            )

    async def async_operate(self, lock_id: str, lock: bool) -> None:
        """Lock or unlock and apply the confirmed state."""
        target = BOLT_LOCKED if lock else BOLT_UNLOCKED
        try:
            response = await self.client.operate(lock_id, lock)
        except LevelCommandError as err:
            await self.async_request_refresh()
            raise HomeAssistantError(
                f"Level lock did not confirm the command ({err}). "
                "Check the door before trying again."
            ) from err
        except (LevelAuthError, LevelTwoFactorRequired) as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError("Level session expired; please re-authenticate") from err
        except LevelApiError as err:
            await self.async_request_refresh()
            raise HomeAssistantError(f"Level command failed: {err}") from err

        _LOGGER.debug(
            "Operation on %s: state=%s result=%s", lock_id, response.bolt_state, response.result
        )
        if response.bolt_state in (0, 1, 2, 3):
            self._overrides[lock_id] = (response.bolt_state, time.monotonic())
            if self.data and lock_id in self.data:
                old_state = self.data[lock_id].bolt_state
                self.data[lock_id].bolt_state = response.bolt_state
                if old_state != response.bolt_state:
                    self.hass.bus.async_fire(
                        EVENT_LOCK_STATE_CHANGED,
                        {
                            "lock_id": lock_id,
                            "name": self.data[lock_id].name,
                            "locked": response.bolt_state == BOLT_LOCKED,
                            "bolt_state": response.bolt_state,
                            "source": "remote",
                        },
                    )
                self.async_update_listeners()

        if response.result not in (RESULT_SUCCESS, RESULT_ALREADY_THERE) or response.bolt_state != target:
            reason = OPERATION_RESULTS.get(response.result, f"code {response.result}")
            raise HomeAssistantError(f"Level lock reported: {reason}")
