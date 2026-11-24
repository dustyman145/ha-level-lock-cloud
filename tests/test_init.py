"""Tests for setup, entities and lock commands."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockState
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, CONF_EMAIL, CONF_PASSWORD, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.level_lock_cloud.const import CONF_TOKEN, DOMAIN

from .conftest import API, EMAIL, FRONT_UUID, PASSWORD, operation_payload


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=EMAIL,
        data={CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD, CONF_TOKEN: "tok-1"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entities(hass: HomeAssistant, level_api) -> None:
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    assert hass.states.get("lock.front_door").state == LockState.LOCKED
    assert hass.states.get("lock.garage").state == LockState.UNLOCKED

    assert hass.states.get("sensor.front_door_battery_level").state == "high"
    assert hass.states.get("binary_sensor.front_door_battery").state == STATE_OFF
    assert hass.states.get("binary_sensor.garage_battery").state == STATE_ON

    # Door sensor only where door sense is supported
    assert hass.states.get("binary_sensor.front_door_door").state == STATE_OFF
    assert hass.states.get("binary_sensor.garage_door") is None

    assert hass.states.get("sensor.front_door_last_activity").state == "keypad"
    assert hass.states.get("sensor.front_door_last_activity_time").state.startswith("2026-11-23")
    assert hass.states.get("binary_sensor.garage_level_connect").state == STATE_OFF


async def _call(hass: HomeAssistant, service: str) -> None:
    await hass.services.async_call(
        "lock", service, {ATTR_ENTITY_ID: "lock.front_door"}, blocking=True
    )


def _mock_bridge(level_api, receive: list[dict[str, Any]]) -> None:
    level_api.post(f"{API}/v1/bridge/send", json={"message_id": "m1", "max_waiting_time_in_seconds": 5})
    level_api.post(f"{API}/v1/bridge/receive", json=receive[0])


async def test_unlock(hass: HomeAssistant, level_api) -> None:
    await _setup(hass)
    events = []
    hass.bus.async_listen("level_lock_cloud_state_changed", events.append)
    _mock_bridge(level_api, [{"state": "success", "payload": operation_payload(0)}])

    await _call(hass, "unlock")
    await hass.async_block_till_done()

    assert hass.states.get("lock.front_door").state == LockState.UNLOCKED
    send = next(c for c in level_api.mock_calls if c[1].path == "/v1/bridge/send")
    body = send[2]
    assert body["device_uuid"] == FRONT_UUID
    assert body["is_admin_queue_item"] is False
    packet = bytes.fromhex(body["command"])
    assert len(packet) == 104 and packet[101] == 54 and packet[102:] == bytes([0, 11])
    assert events and events[0].data["locked"] is False

    # Stale cloud cache (still "locked") does not flip the confirmed state back
    await hass.config_entries.async_get_entry(
        next(iter(hass.config_entries.async_entries(DOMAIN))).entry_id
    ).runtime_data.async_refresh()
    assert hass.states.get("lock.front_door").state == LockState.UNLOCKED


async def test_lock_reports_failure(hass: HomeAssistant, level_api) -> None:
    await _setup(hass)
    _mock_bridge(level_api, [{"state": "success", "payload": operation_payload(2, 2)}])
    with pytest.raises(HomeAssistantError, match="stall"):
        await _call(hass, "unlock")
    assert hass.states.get("lock.front_door").state == LockState.JAMMED


async def test_transport_timeout_is_not_retried(hass: HomeAssistant, level_api) -> None:
    await _setup(hass)
    _mock_bridge(level_api, [{"state": "timeout"}])
    with pytest.raises(HomeAssistantError, match="did not confirm"):
        await _call(hass, "lock")
    sends = [c for c in level_api.mock_calls if c[1].path == "/v1/bridge/send"]
    assert len(sends) == 1


async def test_expired_token_relogins(hass: HomeAssistant, aioclient_mock, account) -> None:
    aioclient_mock.post(f"{API}/v2/login", json={"status": []}, headers={"AccessToken": "tok-2"})

    calls = {"n": 0}

    async def account_get(method, url, data):
        from pytest_homeassistant_custom_component.test_util.aiohttp import (
            AiohttpClientMockResponse,
        )

        calls["n"] += 1
        if calls["n"] == 1:
            return AiohttpClientMockResponse(method, url, status=401)
        return AiohttpClientMockResponse(method, url, json={"account": account})

    aioclient_mock.get(f"{API}/v2/account/get", side_effect=account_get)
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.data[CONF_TOKEN] == "tok-2"


async def test_2fa_on_relogin_starts_reauth(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{API}/v2/account/get", status=401)
    aioclient_mock.post(
        f"{API}/v2/login", status=202, json={"status": []}, headers={"AccessToken": "pre"}
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=EMAIL,
        data={CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD, CONF_TOKEN: "old"},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert flows and flows[0]["context"]["source"] == "reauth"
