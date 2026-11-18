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


@pytest.mark.asyncio
async def test_placeholder():
    pass
