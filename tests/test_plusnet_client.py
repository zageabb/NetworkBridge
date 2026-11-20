import asyncio
import hashlib

import httpx
import pytest

from networkbridge.plusnet_client import (
    PlusnetHubTwoClient,
    RouterLoginError,
    router_password_digest,
)


def test_password_digest_matches_ascii_md5():
    assert router_password_digest("test123") == hashlib.md5(b"test123").hexdigest()


def test_password_digest_rejects_unverified_unicode():
    with pytest.raises(ValueError):
        router_password_digest("pássword")


def test_http_router_rejected():
    with pytest.raises(ValueError):
        PlusnetHubTwoClient("http://192.168.1.254")


def test_authentication_and_inventory():
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.url.path == "/cgi/cgi_basicMyDevice.js" and not any(
            path == "/login.cgi" for _, path in calls
        ):
            return httpx.Response(403, text="Forbidden")
        if request.url.path == "/login.cgi":
            assert b"usr=admin" in request.content
            assert b"pws=" in request.content
            return httpx.Response(200, text="ok")
        if request.url.path == "/cgi/cgi_basicMyDevice.js":
            return httpx.Response(
                200,
                text='var known_device_list = [{mac:"AA:BB:CC:DD:EE:FF",'
                     'ip:"192.168.1.4",activity:"1",dhcp_option:"NA"}];',
            )
        return httpx.Response(200, text="home")

    async def run():
        client = PlusnetHubTwoClient("https://192.168.1.254", "test123")
        await client._client.aclose()
        client._client = httpx.AsyncClient(
            base_url="https://192.168.1.254",
            transport=httpx.MockTransport(handler),
        )
        try:
            devices = await client.inventory()
            assert len(devices) == 1
            assert devices[0]["router_active"] is True
            assert calls == [
                ("GET", "/cgi/cgi_basicMyDevice.js"),
                ("GET", "/"),
                ("POST", "/login.cgi"),
                ("GET", "/cgi/cgi_basicMyDevice.js"),
            ]
        finally:
            await client.close()

    asyncio.run(run())


def test_login_error_prevents_repeat():
    async def run():
        client = PlusnetHubTwoClient("https://192.168.1.254", "test123")
        await client._client.aclose()

        def handler(request):
            if request.url.path == "/login.cgi":
                return httpx.Response(200, text="login_lock")
            return httpx.Response(200, text="home")

        client._client = httpx.AsyncClient(
            base_url="https://192.168.1.254",
            transport=httpx.MockTransport(handler),
        )
        try:
            with pytest.raises(RouterLoginError):
                await client.login()
            with pytest.raises(RouterLoginError):
                await client.login()
        finally:
            await client.close()

    asyncio.run(run())


def test_embedded_login_error_does_not_retry():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/login.cgi":
            return httpx.Response(200, text="<html><script>login_lock</script></html>")
        return httpx.Response(200, text="home")

    async def run():
        client = PlusnetHubTwoClient("https://192.168.1.254", "test123")
        await client._client.aclose()
        client._client = httpx.AsyncClient(
            base_url="https://192.168.1.254",
            transport=httpx.MockTransport(handler),
        )
        try:
            with pytest.raises(RouterLoginError):
                await client.login()
            with pytest.raises(RouterLoginError):
                await client.login()
            assert calls.count("/login.cgi") == 1
        finally:
            await client.close()

    asyncio.run(run())
