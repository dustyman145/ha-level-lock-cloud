"""Config flow for Level Lock Cloud, including 2FA and re-authentication."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import (
    LevelApiClient,
    LevelApiError,
    LevelAuthError,
    LevelCryptoError,
    LevelTwoFactorRequired,
)
from .const import CONF_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_METHOD = "method"
CONF_CODE = "code"


class LevelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Level Lock Cloud."""

    VERSION = 1

    def __init__(self) -> None:
        self._client: LevelApiClient | None = None
        self._email: str = ""
        self._password: str = ""
        self._contacts: dict[str, str | None] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Email and password."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL].strip()
            self._password = user_input[CONF_PASSWORD]
            if self.source != SOURCE_REAUTH:
                await self.async_set_unique_id(self._email.lower())
                self._abort_if_unique_id_configured()
            self._client = LevelApiClient(
                async_get_clientsession(self.hass), self._email, self._password
            )
            try:
                await self._client.login()
            except LevelTwoFactorRequired:
                return await self.async_step_tfa_method()
            except LevelAuthError:
                errors["base"] = "invalid_auth"
            except LevelApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "unknown"
            else:
                return await self._async_finish(errors)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=self._email): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_tfa_method(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose where the 2FA code is sent."""
        assert self._client is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self._client.send_otp(user_input[CONF_METHOD])
            except LevelApiError:
                errors["base"] = "otp_send_failed"
            else:
                return await self.async_step_tfa_code()
        elif not self._contacts:
            try:
                self._contacts = await self._client.get_2fa_contacts()
            except LevelApiError:
                _LOGGER.debug("Could not fetch 2FA contacts", exc_info=True)

        options = [
            method
            for method in ("email", "phone")
            if self._contacts.get(method) or not any(self._contacts.values())
        ]
        return self.async_show_form(
            step_id="tfa_method",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_METHOD, default=options[0]): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            translation_key="tfa_method",
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            description_placeholders={
                "email": self._contacts.get("email") or "-",
                "phone": self._contacts.get("phone") or "-",
            },
            errors=errors,
        )

    async def async_step_tfa_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Enter the 2FA code."""
        assert self._client is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self._client.confirm_otp(user_input[CONF_CODE])
            except LevelApiError:
                errors["base"] = "invalid_code"
            else:
                return await self._async_finish(errors, step_id="tfa_code")

        return self.async_show_form(
            step_id="tfa_code",
            data_schema=vol.Schema({vol.Required(CONF_CODE): str}),
            errors=errors,
        )

    async def _async_finish(
        self, errors: dict[str, str], step_id: str = "user"
    ) -> ConfigFlowResult:
        """Verify account access and the signing key, then create or update the entry."""
        assert self._client is not None
        try:
            await self._client.get_account()
        except LevelTwoFactorRequired:
            return await self.async_step_tfa_method()
        except (LevelAuthError, LevelCryptoError):
            errors["base"] = "invalid_auth"
        except LevelApiError:
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected error loading account")
            errors["base"] = "unknown"
        if errors:
            if step_id == "tfa_code":
                return self.async_show_form(
                    step_id="tfa_code",
                    data_schema=vol.Schema({vol.Required(CONF_CODE): str}),
                    errors=errors,
                )
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL, default=self._email): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                errors=errors,
            )

        data = {
            CONF_EMAIL: self._email,
            CONF_PASSWORD: self._password,
            CONF_TOKEN: self._client.token,
        }
        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(self._get_reauth_entry(), data=data)
        return self.async_create_entry(title=self._email, data=data)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication."""
        self._email = entry_data[CONF_EMAIL]
        return await self.async_step_user()
