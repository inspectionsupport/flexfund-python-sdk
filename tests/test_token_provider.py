from __future__ import annotations

import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from flexfund.auth.cache import InMemoryTokenCache
from flexfund.auth.credentials import ClientCredentials
from flexfund.auth.provider import AsyncTokenProvider, TokenProvider, cache_key
from flexfund.auth.token import AccessToken
from flexfund.errors import AuthenticationError, RateLimitError, ServerError

BASE = "https://flexfund.test"
CREDS = ClientCredentials("test-client-id", "test-client-secret", ("b:read", "a:read"))


def token_body(access_token: str = "tok-1", expires_in: int = 3600) -> dict[str, Any]:
    return {
        "token_type": "Bearer",
        "expires_in": expires_in,
        "access_token": access_token,
        "scope": "a:read b:read",
    }


@pytest.fixture
def route(respx_mock: respx.MockRouter) -> respx.Route:
    return respx_mock.post(f"{BASE}/oauth/token").mock(
        return_value=httpx.Response(200, json=token_body())
    )


@pytest.fixture
def provider(route: respx.Route) -> TokenProvider:
    return TokenProvider(httpx.Client(), BASE + "/", CREDS, InMemoryTokenCache())


def test_request_shape(route: respx.Route, provider: TokenProvider) -> None:
    token = provider.token()
    request = route.calls.last.request
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    form = parse_qs(request.content.decode())
    assert form == {
        "grant_type": ["client_credentials"],
        "client_id": ["test-client-id"],
        "client_secret": ["test-client-secret"],
        "scope": ["b:read a:read"],
    }
    assert token.token == "tok-1"
    assert token.scopes == ("a:read", "b:read")
    assert "authorization" not in request.headers


def test_in_memory_reuse(route: respx.Route, provider: TokenProvider) -> None:
    assert provider.token() is provider.token()
    assert route.call_count == 1


def test_token_inside_60s_buffer_is_renewed(route: respx.Route) -> None:
    route.mock(return_value=httpx.Response(200, json=token_body(expires_in=30)))
    provider = TokenProvider(httpx.Client(), BASE, CREDS)
    provider.token()
    provider.token()
    assert route.call_count == 2


def test_token_just_outside_buffer_is_reused(route: respx.Route) -> None:
    route.mock(return_value=httpx.Response(200, json=token_body(expires_in=120)))
    provider = TokenProvider(httpx.Client(), BASE, CREDS)
    provider.token()
    provider.token()
    assert route.call_count == 1


def test_shared_cache_hit_avoids_request(route: respx.Route) -> None:
    cache = InMemoryTokenCache()
    TokenProvider(httpx.Client(), BASE, CREDS, cache).token()
    second = TokenProvider(httpx.Client(), BASE, CREDS, cache)
    assert second.token().token == "tok-1"
    assert route.call_count == 1


def test_cache_entry_near_expiry_is_ignored(route: respx.Route) -> None:
    cache = InMemoryTokenCache()
    stale = AccessToken("old", datetime.now(UTC) + timedelta(seconds=10))
    cache.set(cache_key(BASE, CREDS), stale.to_dict(), 10)
    assert TokenProvider(httpx.Client(), BASE, CREDS, cache).token().token == "tok-1"
    assert route.call_count == 1


@pytest.mark.parametrize(
    "garbage",
    [
        {},
        {"token": 5},
        {"token": "x", "expiresAt": "not a date"},
        {"expiresAt": "2030-01-01T00:00:00+00:00"},
    ],
)
def test_malformed_cache_entry_is_a_miss(route: respx.Route, garbage: dict[str, Any]) -> None:
    cache = InMemoryTokenCache()
    cache.set(cache_key(BASE, CREDS), garbage, 60)
    assert TokenProvider(httpx.Client(), BASE, CREDS, cache).token().token == "tok-1"
    assert route.call_count == 1


def test_refresh_clears_both_tiers_and_refetches(route: respx.Route) -> None:
    route.side_effect = [
        httpx.Response(200, json=token_body("tok-1")),
        httpx.Response(200, json=token_body("tok-2")),
    ]
    cache = InMemoryTokenCache()
    provider = TokenProvider(httpx.Client(), BASE, CREDS, cache)
    assert provider.token().token == "tok-1"
    assert provider.refresh().token == "tok-2"
    assert provider.token().token == "tok-2"
    cached = cache.get(cache_key(BASE, CREDS))
    assert cached is not None and cached["token"] == "tok-2"
    assert route.call_count == 2


def test_cache_ttl_is_time_to_expiry() -> None:
    seen: dict[str, Any] = {}

    class Spy(InMemoryTokenCache):
        def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
            seen["ttl"] = ttl_seconds
            super().set(key, value, ttl_seconds)

    with respx.mock() as router:
        router.post(f"{BASE}/oauth/token").mock(
            return_value=httpx.Response(200, json=token_body(expires_in=1000))
        )
        TokenProvider(httpx.Client(), BASE, CREDS, Spy()).token()
    assert 995 <= seen["ttl"] <= 1000


@pytest.mark.parametrize(
    ("creds", "fragment"),
    [
        (ClientCredentials("", "s"), "client id"),
        (ClientCredentials("   ", "s"), "client id"),
        (ClientCredentials("i", ""), "client secret"),
        (ClientCredentials("", " "), "client id or client secret"),
    ],
)
def test_missing_credentials_make_no_request(
    route: respx.Route, creds: ClientCredentials, fragment: str
) -> None:
    with pytest.raises(AuthenticationError) as exc:
        TokenProvider(httpx.Client(), BASE, creds).token()
    assert fragment in exc.value.message
    assert "so no token was requested" in exc.value.message
    assert route.call_count == 0


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            httpx.Response(
                400,
                json={
                    "error": "invalid_request",
                    "error_description": "Bad.",
                    "hint": "Check `client_id`",
                },
            ),
            "(status 400): invalid_request — Bad. — Check `client_id`",
        ),
        (httpx.Response(401, json={"error": "invalid_client"}), "(status 401): invalid_client"),
        (
            httpx.Response(404, json={"success": False, "message": "Not found"}),
            "Not found (status 404)",
        ),
        (httpx.Response(422, json={"message": ["a", "b"]}), "a; b (status 422)"),
        (httpx.Response(200, json={"token_type": "Bearer"}), "(status 200)"),
    ],
)
def test_failure_messages(route: respx.Route, response: httpx.Response, expected: str) -> None:
    route.mock(return_value=response)
    with pytest.raises(AuthenticationError) as exc:
        TokenProvider(httpx.Client(), BASE, CREDS).token()
    assert expected in exc.value.message
    assert exc.value.status_code == response.status_code


def test_network_failure_is_a_server_error_not_bad_credentials(route: respx.Route) -> None:
    route.mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(ServerError, match="Failed to reach FlexFund's /oauth/token") as exc:
        TokenProvider(httpx.Client(), BASE, CREDS).token()
    assert not isinstance(exc.value, AuthenticationError)


@pytest.mark.parametrize(
    "response", [httpx.Response(500, json={"foo": "bar"}), httpx.Response(502, text="<html>")]
)
def test_token_endpoint_outage_is_a_server_error(
    route: respx.Route, response: httpx.Response
) -> None:
    route.mock(return_value=response)
    with pytest.raises(ServerError, match="try again later") as exc:
        TokenProvider(httpx.Client(), BASE, CREDS).token()
    assert exc.value.status_code == response.status_code


def test_token_endpoint_rate_limit_is_a_rate_limit_error(route: respx.Route) -> None:
    route.mock(return_value=httpx.Response(429, headers={"Retry-After": "5"}, json={}))
    with pytest.raises(RateLimitError) as exc:
        TokenProvider(httpx.Client(), BASE, CREDS).token()
    assert exc.value.retry_after == 5


def test_a_malformed_token_response_does_not_carry_the_token(route: respx.Route) -> None:
    route.mock(return_value=httpx.Response(200, json=token_body("live-token", expires_in=-5)))
    with pytest.raises(AuthenticationError, match="malformed token response") as exc:
        TokenProvider(httpx.Client(), BASE, CREDS).token()
    assert exc.value.raw_body is None
    assert exc.value.body is not None
    assert exc.value.body["access_token"] == "[redacted]"
    assert "live-token" not in repr(vars(exc.value))


class BrokenCache:
    def get(self, key: str) -> dict[str, Any] | None:
        raise ConnectionError("redis://user:pw@cache:6379 unreachable")

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        raise ConnectionError("unreachable")

    def delete(self, key: str) -> None:
        raise ConnectionError("unreachable")


def test_a_failing_cache_backend_falls_back_to_the_network(
    route: respx.Route, caplog: pytest.LogCaptureFixture
) -> None:
    route.mock(return_value=httpx.Response(200, json=token_body()))
    provider = TokenProvider(httpx.Client(), BASE, CREDS, BrokenCache())

    assert provider.token().token == "tok-1"
    assert provider.refresh().token == "tok-1"
    assert route.call_count == 2
    assert "ConnectionError" in caplog.text
    assert "user:pw" not in caplog.text


def test_cache_key_excludes_secret_and_is_scope_order_independent() -> None:
    key = cache_key(BASE + "/", CREDS)
    assert key.startswith("flexfund_token_")
    assert "test-client-secret" not in key
    assert key == cache_key(
        BASE, ClientCredentials("test-client-id", "other-secret", ("a:read", "b:read"))
    )
    assert key != cache_key(BASE, ClientCredentials("someone-else", "x", ("a:read", "b:read")))
    assert key != cache_key("https://other.test", CREDS)


def test_secret_never_reaches_the_cache() -> None:
    cache = InMemoryTokenCache()
    with respx.mock() as router:
        router.post(f"{BASE}/oauth/token").mock(return_value=httpx.Response(200, json=token_body()))
        TokenProvider(httpx.Client(), BASE, CREDS, cache).token()
    stored = cache.get(cache_key(BASE, CREDS))
    assert "test-client-secret" not in json.dumps(stored)


def test_concurrent_threads_trigger_one_request(respx_mock: respx.MockRouter) -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        time.sleep(0.1)
        return httpx.Response(200, json=token_body())

    route = respx_mock.post(f"{BASE}/oauth/token").mock(side_effect=slow)
    provider = TokenProvider(httpx.Client(), BASE, CREDS, InMemoryTokenCache())
    barrier = threading.Barrier(10)

    def work() -> str:
        barrier.wait()
        return provider.token().token

    with ThreadPoolExecutor(10) as pool:
        results = list(pool.map(lambda _: work(), range(10)))
    assert results == ["tok-1"] * 10
    assert route.call_count == 1


# -- async ----------------------------------------------------------------------------------


class AsyncDictCache:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    async def get(self, key: str) -> dict[str, Any] | None:
        return self.items.get(key)

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self.items[key] = value

    async def delete(self, key: str) -> None:
        self.items.pop(key, None)


async def test_async_reuse_cache_and_refresh(route: respx.Route) -> None:
    cache = AsyncDictCache()
    async with httpx.AsyncClient() as http:
        provider = AsyncTokenProvider(http, BASE, CREDS, cache)
        first = await provider.token()
        assert await provider.token() is first
        assert route.call_count == 1
        assert cache_key(BASE, CREDS) in cache.items

        other = AsyncTokenProvider(http, BASE, CREDS, cache)
        assert (await other.token()).token == "tok-1"
        assert route.call_count == 1

        route.mock(return_value=httpx.Response(200, json=token_body("tok-2")))
        assert (await provider.refresh()).token == "tok-2"
        assert cache.items[cache_key(BASE, CREDS)]["token"] == "tok-2"


async def test_async_malformed_cache_entry_is_a_miss(route: respx.Route) -> None:
    cache = AsyncDictCache()
    cache.items[cache_key(BASE, CREDS)] = {"nonsense": True}
    async with httpx.AsyncClient() as http:
        assert (await AsyncTokenProvider(http, BASE, CREDS, cache).token()).token == "tok-1"


async def test_async_missing_credentials_make_no_request(route: respx.Route) -> None:
    async with httpx.AsyncClient() as http:
        with pytest.raises(AuthenticationError, match="client id"):
            await AsyncTokenProvider(http, BASE, ClientCredentials("", "s")).token()
    assert route.call_count == 0


async def test_async_failure_message(route: respx.Route) -> None:
    route.mock(
        return_value=httpx.Response(401, json={"error": "invalid_client", "hint": "bad secret"})
    )
    async with httpx.AsyncClient() as http:
        with pytest.raises(
            AuthenticationError, match=r"\(status 401\): invalid_client — bad secret"
        ):
            await AsyncTokenProvider(http, BASE, CREDS).token()


async def test_async_network_failure(route: respx.Route) -> None:
    route.mock(side_effect=httpx.ConnectError("down"))
    async with httpx.AsyncClient() as http:
        with pytest.raises(ServerError, match="Failed to reach"):
            await AsyncTokenProvider(http, BASE, CREDS).token()


class AsyncBrokenCache:
    async def get(self, key: str) -> dict[str, Any] | None:
        raise ConnectionError("unreachable")

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        raise ConnectionError("unreachable")

    async def delete(self, key: str) -> None:
        raise ConnectionError("unreachable")


async def test_async_failing_cache_backend_falls_back_to_the_network(route: respx.Route) -> None:
    route.mock(return_value=httpx.Response(200, json=token_body()))
    async with httpx.AsyncClient() as http:
        provider = AsyncTokenProvider(http, BASE, CREDS, AsyncBrokenCache())
        assert (await provider.token()).token == "tok-1"
        assert (await provider.refresh()).token == "tok-1"
    assert route.call_count == 2


async def test_concurrent_tasks_trigger_one_request(respx_mock: respx.MockRouter) -> None:
    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.1)
        return httpx.Response(200, json=token_body())

    route = respx_mock.post(f"{BASE}/oauth/token").mock(side_effect=slow)
    async with httpx.AsyncClient() as http:
        provider = AsyncTokenProvider(http, BASE, CREDS, AsyncDictCache())
        results = await asyncio.gather(*(provider.token() for _ in range(10)))
    assert {t.token for t in results} == {"tok-1"}
    assert route.call_count == 1


# -- refresh coalescing -------------------------------------------------------------------


class CountingFetcher:
    """Answers /oauth/token with tok-1, tok-2, ... and counts the calls (thread-safe)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            self.calls += 1
            n = self.calls
        time.sleep(0.02)  # long enough for the other callers to queue up on the lock
        return httpx.Response(200, json=token_body(f"tok-{n}"))


def test_concurrent_refreshes_for_the_same_rejected_token_make_one_request(
    respx_mock: respx.MockRouter,
) -> None:
    fetcher = CountingFetcher()
    respx_mock.post(f"{BASE}/oauth/token").mock(side_effect=fetcher)
    provider = TokenProvider(httpx.Client(), BASE, CREDS)
    old = provider.token()
    assert fetcher.calls == 1

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: provider.refresh(rejected=old), range(8)))

    assert fetcher.calls == 2  # the initial token plus ONE refresh, not eight
    assert {t.token for t in results} == {"tok-2"}


def test_refresh_without_a_rejected_token_is_still_unconditional(
    respx_mock: respx.MockRouter,
) -> None:
    fetcher = CountingFetcher()
    respx_mock.post(f"{BASE}/oauth/token").mock(side_effect=fetcher)
    provider = TokenProvider(httpx.Client(), BASE, CREDS)
    provider.token()
    provider.refresh()
    provider.refresh()
    assert fetcher.calls == 3


def test_a_stale_rejected_token_does_not_stop_a_needed_refresh(
    respx_mock: respx.MockRouter,
) -> None:
    """If the rejected token IS the current one, nobody replaced it, so a new one is minted."""
    fetcher = CountingFetcher()
    respx_mock.post(f"{BASE}/oauth/token").mock(side_effect=fetcher)
    provider = TokenProvider(httpx.Client(), BASE, CREDS)
    current = provider.token()
    assert provider.refresh(rejected=current).token == "tok-2"
    assert fetcher.calls == 2


def test_refresh_reuses_a_newer_token_another_process_put_in_the_shared_cache(
    respx_mock: respx.MockRouter,
) -> None:
    fetcher = CountingFetcher()
    respx_mock.post(f"{BASE}/oauth/token").mock(side_effect=fetcher)
    cache = InMemoryTokenCache()
    provider = TokenProvider(httpx.Client(), BASE, CREDS, cache)
    old = provider.token()
    other_process = AccessToken("tok-from-elsewhere", datetime.now(UTC) + timedelta(hours=1))
    cache.set(cache_key(BASE, CREDS), other_process.to_dict(), 3600)
    provider._token = None  # this process has no token in memory, the shared cache has a newer one

    assert provider.refresh(rejected=old).token == "tok-from-elsewhere"
    assert fetcher.calls == 1


async def test_concurrent_async_refreshes_for_the_same_rejected_token_make_one_request(
    respx_mock: respx.MockRouter,
) -> None:
    calls = 0

    async def fetch(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return httpx.Response(200, json=token_body(f"tok-{calls}"))

    respx_mock.post(f"{BASE}/oauth/token").mock(side_effect=fetch)
    async with httpx.AsyncClient() as http:
        provider = AsyncTokenProvider(http, BASE, CREDS)
        old = await provider.token()
        results = await asyncio.gather(*(provider.refresh(rejected=old) for _ in range(8)))

    assert calls == 2
    assert {t.token for t in results} == {"tok-2"}


async def test_eight_requests_rejected_for_one_token_cause_one_refresh_end_to_end(
    respx_mock: respx.MockRouter,
) -> None:
    """The real path: transport -> 401 -> provider.refresh(rejected=...), all concurrent."""
    from flexfund._http.transport import AsyncTransport

    token_calls = 0

    async def mint(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls
        token_calls += 1
        await asyncio.sleep(0.01)
        return httpx.Response(200, json=token_body(f"tok-{token_calls}"))

    def api(request: httpx.Request) -> httpx.Response:
        if request.headers["authorization"] == "Bearer tok-1":
            return httpx.Response(401, json={"message": "revoked"})
        return httpx.Response(200, json={"success": True, "message": "ok", "data": {"id": 1}})

    respx_mock.post(f"{BASE}/oauth/token").mock(side_effect=mint)
    respx_mock.get(f"{BASE}/v20260322/thing").mock(side_effect=api)
    async with httpx.AsyncClient() as auth_http, httpx.AsyncClient(base_url=BASE) as http:
        provider = AsyncTokenProvider(auth_http, BASE, CREDS)
        await provider.token()  # tok-1, which the API will reject
        transport = AsyncTransport(http, provider, max_attempts=1)
        results = await asyncio.gather(
            *(transport.request("GET", "v20260322/thing") for _ in range(8))
        )

    assert results == [{"id": 1}] * 8
    assert token_calls == 2  # tok-1, then exactly one refresh to tok-2
