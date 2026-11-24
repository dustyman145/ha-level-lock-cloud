"""Async client for the (undocumented) Level cloud API.

Reverse engineered from the Level Home Android app. See docs/api/.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
import re
import time
from typing import Any
import uuid

import aiohttp
from cryptography.hazmat.primitives.asymmetric import ec

from .crypto import (
    HISTORY_LATEST_PAYLOAD,
    OPCODE_BOLT_OPERATE_V3,
    OPCODE_HISTORY_LATEST,
    HistoryEvent,
    LevelCryptoError,
    LevelProtocolError,
    OperationResponse,
    account_private_key,
    build_command,
    login_value,
    operate_payload,
    otp_hash,
    parse_history,
    parse_operation_response,
)

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://api.level.co"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=25)
DEFAULT_WAIT_SECONDS = 30
MAX_WAIT_SECONDS = 120
POLL_INTERVAL = 1.0


class LevelApiError(Exception):
    """Generic API error."""


class LevelAuthError(LevelApiError):
    """Credentials rejected or session invalid."""


class LevelTwoFactorRequired(LevelApiError):
    """Login needs a 2FA code. The client holds a pre-2FA token."""


class LevelCommandError(LevelApiError):
    """A lock command failed or its outcome is unknown."""


def normalize_user_id(user_id: str) -> str:
    """Emails as typed; phone numbers without separators (like the app)."""
    user_id = user_id.strip()
    if re.fullmatch(r"\+?[\d\s\-().]+", user_id):
        return re.sub(r"[\s\-().]", "", user_id)
    return user_id


class LevelApiClient:
    """Client for api.level.co."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        user_id: str,
        password: str,
        token: str | None = None,
    ) -> None:
        self._session = session
        self._user_id = normalize_user_id(user_id)
        self._password = password
        self._token = token
        self._account_uuid: uuid.UUID | None = None
        self._key: ec.EllipticCurvePrivateKey | None = None
        self._command_lock = asyncio.Lock()

    @property
    def token(self) -> str | None:
        """Current session token."""
        return self._token

    # --- HTTP ------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        auth: bool = True,
    ) -> tuple[int, Mapping[str, str], Any]:
        req_headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)
        if auth:
            if not self._token:
                raise LevelAuthError("Not logged in")
            req_headers["AccessToken"] = self._token
        try:
            async with self._session.request(
                method,
                f"{API_BASE_URL}{path}",
                json=json,
                headers=req_headers,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                try:
                    body = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError):
                    body = None
                if resp.status in (401, 403):
                    raise LevelAuthError(f"{path}: HTTP {resp.status}")
                if resp.status >= 400:
                    message = body.get("message") if isinstance(body, dict) else None
                    raise LevelApiError(f"{path}: HTTP {resp.status} {message or ''}".strip())
                return resp.status, resp.headers, body
        except (aiohttp.ClientError, TimeoutError) as err:
            raise LevelApiError(f"{path}: {err!r}") from err

    async def _authed(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> Any:
        """Request with one re-login on auth failure (the request was rejected, so retry is safe)."""
        try:
            _, _, body = await self._request(method, path, json=json)
        except LevelAuthError:
            _LOGGER.debug("Session rejected on %s, logging in again", path)
            await self.login()
            _, _, body = await self._request(method, path, json=json)
        return body

    # --- Authentication --------------------------------------------------

    async def login(self) -> None:
        """Log in. Raises LevelTwoFactorRequired when a code is needed."""
        status, headers, body = await self._request(
            "POST",
            "/v2/login",
            json={"userID": self._user_id, "password": login_value(self._password)},
            headers={"X-Allow-TFA": "1"},
            auth=False,
        )
        flags = (body.get("status") or []) if isinstance(body, dict) else []
        if "loginFailed" in flags:
            raise LevelAuthError("Invalid credentials")
        token = headers.get("AccessToken")
        if not token:
            raise LevelAuthError("No access token returned")
        self._token = token
        if status == 202 or "tfaEnabled" in flags:
            raise LevelTwoFactorRequired

    async def get_2fa_contacts(self) -> dict[str, str | None]:
        """Where 2FA codes can be sent: {'email': ..., 'phone': ...}."""
        _, _, body = await self._request(
            "POST", "/v1/2fa/contacts", json={"hashed_password": login_value(self._password)}
        )
        body = body if isinstance(body, dict) else {}
        return {"email": body.get("email"), "phone": body.get("phone")}

    async def send_otp(self, method: str) -> None:
        """Ask the server to send a 2FA code by 'email' or 'phone'."""
        await self._request("POST", "/v1/2fa/otp/send", json={"method": method})

    async def confirm_otp(self, code: str) -> None:
        """Submit the 2FA code; stores the new session token."""
        _, headers, _ = await self._request(
            "POST", "/v1/2fa/confirm", json={"hash": otp_hash(code)}
        )
        if new_token := headers.get("AccessToken"):
            self._token = new_token

    # --- Account ---------------------------------------------------------

    async def get_account(self) -> dict[str, Any]:
        """Return the account object (locations, locks, key blob)."""
        if not self._token:
            await self.login()
        body = await self._authed("GET", "/v2/account/get")
        if not isinstance(body, dict):
            raise LevelApiError("Unexpected account response")
        account = body.get("account", body)
        if self._key is None:
            self._key = account_private_key(account, self._password)
            self._account_uuid = uuid.UUID(account["uuid"])
        return account

    # --- Bridge commands -------------------------------------------------

    async def _exchange(self, device_uuid: str, opcode: int, payload: bytes) -> bytes:
        if self._key is None or self._account_uuid is None:
            raise LevelCommandError("Account key not loaded")
        target = uuid.UUID(device_uuid)
        packet = build_command(self._key, self._account_uuid, target, opcode, payload)
        sent = await self._authed(
            "POST",
            "/v1/bridge/send",
            {"device_uuid": str(target), "command": packet.hex(), "is_admin_queue_item": False},
        )
        message_id = sent.get("message_id") if isinstance(sent, dict) else None
        if not message_id:
            raise LevelCommandError("No message_id returned; outcome unknown")
        wait = sent.get("max_waiting_time_in_seconds")
        wait = wait if isinstance(wait, (int, float)) and wait > 0 else DEFAULT_WAIT_SECONDS
        deadline = time.monotonic() + min(wait, MAX_WAIT_SECONDS)

        while True:
            received = await self._authed(
                "POST", "/v1/bridge/receive", {"message_id": message_id}
            )
            state = received.get("state") if isinstance(received, dict) else None
            if state == "success":
                try:
                    return bytes.fromhex(received.get("payload") or "")
                except ValueError as err:
                    raise LevelCommandError("Malformed payload") from err
            if state != "in_progress":
                raise LevelCommandError(f"Bridge transport state: {state}")
            if time.monotonic() >= deadline:
                raise LevelCommandError("Timed out waiting for the lock")
            await asyncio.sleep(POLL_INTERVAL)

    async def operate(self, device_uuid: str, lock: bool) -> OperationResponse:
        """Lock or unlock. Never retried automatically."""
        async with self._command_lock:
            payload = await self._exchange(
                device_uuid, OPCODE_BOLT_OPERATE_V3, operate_payload(lock)
            )
        try:
            return parse_operation_response(payload)
        except LevelProtocolError as err:
            raise LevelCommandError(str(err)) from err

    async def latest_history(self, device_uuid: str) -> HistoryEvent | None:
        """Read the last operation stored on the lock (read-only)."""
        async with self._command_lock:
            payload = await self._exchange(
                device_uuid, OPCODE_HISTORY_LATEST, HISTORY_LATEST_PAYLOAD
            )
        try:
            events = parse_history(payload)
        except LevelProtocolError as err:
            raise LevelCommandError(str(err)) from err
        return events[0] if events else None


__all__ = [
    "LevelApiClient",
    "LevelApiError",
    "LevelAuthError",
    "LevelCommandError",
    "LevelCryptoError",
    "LevelTwoFactorRequired",
]
