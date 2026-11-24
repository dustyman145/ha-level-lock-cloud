"""Tests for the config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.level_lock_cloud.const import CONF_TOKEN, DOMAIN
from custom_components.level_lock_cloud.crypto import otp_hash

from .conftest import API, EMAIL, PASSWORD


async def _start(hass: HomeAssistant, password: str = PASSWORD):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: password}
    )


async def test_user_flow_without_2fa(hass: HomeAssistant, level_api) -> None:
    result = await _start(hass)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD, CONF_TOKEN: "tok-1"}
    login = next(c for c in level_api.mock_calls if c[1].path == "/v2/login")
    assert login[3]["X-Allow-TFA"] == "1"
    assert login[2]["userID"] == EMAIL


async def test_user_flow_wrong_password(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(f"{API}/v2/login", json={"status": ["loginFailed"]})
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(f"{API}/v2/login", status=500)
    result = await _start(hass)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_with_2fa(hass: HomeAssistant, aioclient_mock, account) -> None:
    aioclient_mock.post(
        f"{API}/v2/login", status=202, json={"status": []}, headers={"AccessToken": "pre"}
    )
    aioclient_mock.post(f"{API}/v1/2fa/contacts", json={"email": "o***@example.invalid"})
    aioclient_mock.post(f"{API}/v1/2fa/otp/send", json={})
    aioclient_mock.post(f"{API}/v1/2fa/confirm", json={}, headers={"AccessToken": "full"})
    aioclient_mock.get(f"{API}/v2/account/get", json={"account": account})

    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "tfa_method"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"method": "email"}
    )
    assert result["step_id"] == "tfa_code"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123456"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_TOKEN] == "full"

    calls = {c[1].path: c for c in aioclient_mock.mock_calls}
    assert calls["/v1/2fa/otp/send"][2] == {"method": "email"}
    assert calls["/v1/2fa/otp/send"][3]["AccessToken"] == "pre"
    assert calls["/v1/2fa/confirm"][2] == {"hash": otp_hash("123456")}
    assert calls["/v2/account/get"][3]["AccessToken"] == "full"


async def test_2fa_bad_code(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(
        f"{API}/v2/login", status=202, json={"status": []}, headers={"AccessToken": "pre"}
    )
    aioclient_mock.post(f"{API}/v1/2fa/contacts", json={})
    aioclient_mock.post(f"{API}/v1/2fa/otp/send", json={})
    aioclient_mock.post(f"{API}/v1/2fa/confirm", status=400, json={"message": "bad"})

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"method": "phone"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "1"})
    assert result["step_id"] == "tfa_code"
    assert result["errors"] == {"base": "invalid_code"}
