from __future__ import annotations

import httpx
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flexfund import AsyncFlexFundClient
from flexfund.fastapi import FlexFundDep, flexfund_client_context, flexfund_lifespan

BASE = "https://flexfund.test"


def make_client() -> AsyncFlexFundClient:
    return AsyncFlexFundClient(
        client_id="test-client-id", client_secret="test-client-secret", base_url=BASE
    )


def test_lifespan_builds_injects_and_closes(respx_mock: respx.MockRouter) -> None:
    token = respx_mock.post(f"{BASE}/oauth/token").mock(
        return_value=httpx.Response(
            200,
            json={"token_type": "Bearer", "expires_in": 3600, "access_token": "tok", "scope": ""},
        )
    )
    built: list[AsyncFlexFundClient] = []

    def factory() -> AsyncFlexFundClient:
        client = make_client()
        built.append(client)
        return client

    app = FastAPI(lifespan=flexfund_lifespan(factory))

    @app.get("/probe")
    async def probe(flexfund: FlexFundDep) -> dict[str, bool]:
        # The route received the very client the lifespan built, and it can authenticate.
        provider = flexfund._transport._token_provider
        assert provider is not None
        await provider.token()
        return {"same": flexfund is built[0]}

    with TestClient(app) as tc:
        assert len(built) == 1
        assert tc.get("/probe").json() == {"same": True}
        assert app.state.flexfund is built[0]
        assert not built[0]._owned[0].is_closed
    assert token.call_count == 1
    assert all(c.is_closed for c in built[0]._owned)


def test_missing_lifespan_gives_a_clear_error() -> None:
    app = FastAPI()

    @app.get("/probe")
    async def probe(flexfund: FlexFundDep) -> dict[str, bool]:  # pragma: no cover
        return {}

    with TestClient(app, raise_server_exceptions=False) as tc:
        assert tc.get("/probe").status_code == 500


async def test_client_context_composes_and_closes() -> None:
    app = FastAPI()
    async with flexfund_client_context(make_client, app) as client:
        assert app.state.flexfund is client
        assert not client._owned[0].is_closed
    assert all(c.is_closed for c in client._owned)


async def test_client_context_closes_on_error() -> None:
    holder: list[AsyncFlexFundClient] = []
    try:
        async with flexfund_client_context(make_client) as client:
            holder.append(client)
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert all(c.is_closed for c in holder[0]._owned)
