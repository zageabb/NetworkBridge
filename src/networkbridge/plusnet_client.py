"""Plusnet Hub Two read-only inventory HTTP client.

Authentication protocol derived from Hub Two login_function.js: POST
GO, usr and pws to /login.cgi, using the router's MD5-compatible digest.
No router configuration endpoints are accessed.
"""
from __future__ import annotations

import hashlib
import ssl
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from networkbridge.plusnet_inventory import MAX_PAYLOAD, parse_inventory

INVENTORY_PATH = "/cgi/cgi_basicMyDevice.js"
LOGIN_PATH = "/login.cgi"
HOME_PATH = "/basic_-_my_devices.htm"


class RouterLoginError(Exception):
    """Authentication failed; caller must not immediately retry."""


def router_password_digest(password: str) -> str:
    # The Hub's JavaScript calcMD5 maps printable ASCII to its byte value.
    # Reject other characters until verified against the router's implementation.
    if not password or any(ord(ch) < 32 or ord(ch) > 126 for ch in password):
        raise ValueError("Hub Two password must use printable ASCII for this client")
    return hashlib.md5(password.encode("ascii")).hexdigest()


class PlusnetHubTwoClient:
    def __init__(
        self, url: str, password: str | None = None,
        tls_certificate: Path | None = None,
    ) -> None:
        parts = urlsplit(url)
        if (parts.scheme != "https" or not parts.hostname or parts.username
                or parts.password or parts.query or parts.fragment or
                parts.path not in ("", "/")):
            raise ValueError("Router URL must be an HTTPS origin without credentials")
        verify: bool | ssl.SSLContext = True
        if tls_certificate is not None:
            if not tls_certificate.is_file():
                raise ValueError("Router TLS certificate file not found")
            verify = ssl.create_default_context(cafile=str(tls_certificate))
            verify.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/"), timeout=5.0, follow_redirects=False,
            verify=verify, trust_env=False,
        )
        self._password = password
        self._logged_in = False
        self._login_attempted = False

    async def close(self) -> None:
        await self._client.aclose()

    async def _get_inventory(self) -> str:
        response = await self._client.get(
            INVENTORY_PATH, params={"t": str(int(time.time() * 1000))},
            headers={"Referer": str(self._client.base_url) + HOME_PATH},
        )
        response.raise_for_status()
        if len(response.content) > MAX_PAYLOAD:
            raise ValueError("Router inventory exceeds maximum size")
        if "known_device_list" not in response.text:
            raise ValueError("Router did not return inventory")
        return response.text

    async def login(self) -> None:
        if self._login_attempted:
            raise RouterLoginError("Login already attempted; retry disabled")
        if self._password is None:
            raise RouterLoginError("Router password not configured")
        self._login_attempted = True
        # Establish initial cookies before the password-only login.
        initial = await self._client.get("/")
        initial.raise_for_status()
        response = await self._client.post(
            LOGIN_PATH,
            data={"GO": "basic_-_my_devices.htm", "usr": "admin",
                  "pws": router_password_digest(self._password)},
            headers={"Referer": str(self._client.base_url) + "/"},
        )
        response.raise_for_status()
        # Login errors may be embedded in a returned HTML page.
        if any(marker in response.text.lower() for marker in
               ("login_error", "login_lock", "attack_error")):
            raise RouterLoginError("Router rejected login or is locked")
        self._logged_in = True

    async def inventory(self) -> list[dict[str, object]]:
        try:
            raw = await self._get_inventory()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (401, 403) or self._logged_in:
                raise
            await self.login()
            raw = await self._get_inventory()
        return parse_inventory(raw)
