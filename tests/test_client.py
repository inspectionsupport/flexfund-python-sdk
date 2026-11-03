from __future__ import annotations

import httpx
import pytest
import respx

from flexfund import AsyncFlexFundClient, FlexFundClient
from flexfund.errors import AuthenticationError

BASE = "https://flexfund.test"
TOKEN = {"token_type": "Bearer", "expires_in": 3600, "access_token": "tok", "scope": "a:read"}


def test_base_url_is_required() -> None:
    with pytest.raises(TypeError, match="base_url"):
        FlexFundClient(client_id="i", client_secret="s")  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="FlexFund support"):
        FlexFundClient(client_id="i", client_secret="s", base_url="  ")


def test_the_sdk_ships_no_endpoint_urls() -> None:
    import flexfund

    assert not hasattr(flexfund, "Environment")


def test_sync_client_authenticates_and_calls(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE}/oauth/token").mock(return_value=httpx.Response(200, json=TOKEN))
    route = respx_mock.get(f"{BASE}/v20260322/x").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": [1]})
    )
    with FlexFundClient(
        client_id="test-client-id", client_secret="test-client-secret", base_url=BASE
    ) as c:
        assert c._transport.request("GET", "v20260322/x") == [1]
    assert route.calls.last.request.headers["authorization"] == "Bearer tok"


async def test_async_client_authenticates_and_calls(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE}/oauth/token").mock(return_value=httpx.Response(200, json=TOKEN))
    respx_mock.get(f"{BASE}/v20260322/x").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": {"a": 1}})
    )
    async with AsyncFlexFundClient(
        client_id="test-client-id", client_secret="test-client-secret", base_url=BASE
    ) as c:
        assert await c._transport.request("GET", "v20260322/x") == {"a": 1}


def test_missing_credentials_raise_without_a_request(respx_mock: respx.MockRouter) -> None:
    token = respx_mock.post(f"{BASE}/oauth/token")
    with (
        FlexFundClient(client_id="", client_secret="", base_url=BASE) as c,
        pytest.raises(AuthenticationError),
    ):
        c._transport.request("GET", "v20260322/x")
    assert token.call_count == 0


def test_only_owned_http_clients_are_closed() -> None:
    mine = httpx.Client(base_url=BASE)
    with FlexFundClient(client_id="i", client_secret="s", base_url=BASE, http_client=mine):
        pass
    assert not mine.is_closed
    mine.close()


async def test_async_only_owned_http_clients_are_closed() -> None:
    mine = httpx.AsyncClient(base_url=BASE)
    async with AsyncFlexFundClient(
        client_id="i", client_secret="s", base_url=BASE, http_client=mine
    ):
        pass
    assert not mine.is_closed
    await mine.aclose()


@pytest.mark.parametrize("url", ["http://api.example.com", "ftp://x.test", "api.example.com"])
def test_plain_http_base_url_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="https"):
        FlexFundClient(client_id="a", client_secret="b", base_url=url)


@pytest.mark.parametrize("url", ["http://localhost:8000", "http://api.test", "https://x.example"])
def test_local_http_and_https_base_urls_allowed(url: str) -> None:
    FlexFundClient(client_id="a", client_secret="b", base_url=url).close()


@pytest.mark.parametrize(
    "theirs",
    ["http://flexfund.example", "https://elsewhere.example", "https://flexfund.example:8443", ""],
)
def test_a_caller_http_client_must_point_at_the_token_origin_over_https(theirs: str) -> None:
    with httpx.Client(base_url=theirs) as mine, pytest.raises(ValueError, match="base_url"):
        FlexFundClient(
            client_id="i", client_secret="s", base_url="https://flexfund.example", http_client=mine
        )


async def test_async_caller_http_client_is_checked_too() -> None:
    async with httpx.AsyncClient(base_url="http://api.flexfund.example") as mine:
        with pytest.raises(ValueError, match="https"):
            AsyncFlexFundClient(
                client_id="i",
                client_secret="s",
                base_url="https://api.flexfund.example",
                http_client=mine,
            )


def test_a_caller_http_client_with_a_path_on_the_same_origin_is_accepted() -> None:
    with httpx.Client(base_url="https://flexfund.example/") as mine:
        FlexFundClient(
            client_id="i", client_secret="s", base_url="https://flexfund.example", http_client=mine
        ).close()


def test_turning_off_tls_verification_warns_except_for_local_hosts() -> None:
    with pytest.warns(UserWarning, match="verification is off"):
        FlexFundClient(
            client_id="i",
            client_secret="s",
            base_url=BASE.replace(".test", ".example"),
            verify=False,
        ).close()
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        FlexFundClient(client_id="i", client_secret="s", base_url=BASE, verify=False).close()
