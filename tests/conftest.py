"""Shared fixtures. The generated smoke tests in tests/generated rely on these names."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
import respx

from flexfund._http.transport import AsyncTransport, SyncTransport

BASE_URL = "https://flexfund.test"


def envelope(data: Any) -> dict[str, Any]:
    """A FlexFund success envelope around ``data``."""
    return {"success": True, "message": "ok", "data": data}


@pytest.fixture
def sync_transport(respx_mock: respx.MockRouter) -> Iterator[SyncTransport]:
    client = httpx.Client(base_url=BASE_URL)
    try:
        yield SyncTransport(client, None, max_attempts=1)
    finally:
        client.close()


@pytest.fixture
async def async_transport(respx_mock: respx.MockRouter) -> AsyncIterator[AsyncTransport]:
    client = httpx.AsyncClient(base_url=BASE_URL)
    try:
        yield AsyncTransport(client, None, max_attempts=1)
    finally:
        await client.aclose()
