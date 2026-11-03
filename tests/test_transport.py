from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from typing import Any

import httpx
import pytest
import respx

from conftest import BASE_URL, envelope
from flexfund import __version__
from flexfund._http.transport import AsyncTransport, SyncTransport
from flexfund.auth.token import AccessToken
from flexfund.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

URL = f"{BASE_URL}/v20260322/thing"
PATH = "v20260322/thing"

Send = Callable[..., Awaitable[Any]]


class FakeProvider:
    """Stands in for TokenProvider/AsyncTokenProvider: hands out tok-1, then tok-2, ..."""

    def __init__(self) -> None:
        self.refreshes = 0
        self.rejected: list[AccessToken | None] = []
        self._n = 1

    def _token(self) -> AccessToken:
        return AccessToken(f"tok-{self._n}", datetime.now(UTC) + timedelta(hours=1))

    def token(self) -> AccessToken:
        return self._token()

    def refresh(self, rejected: AccessToken | None = None) -> AccessToken:
        self.rejected.append(rejected)
        self.refreshes += 1
        self._n += 1
        return self._token()


class AsyncFakeProvider(FakeProvider):
    async def token(self) -> AccessToken:  # type: ignore[override]
        return self._token()

    async def refresh(self, rejected: AccessToken | None = None) -> AccessToken:  # type: ignore[override]
        self.rejected.append(rejected)
        self.refreshes += 1
        self._n += 1
        return self._token()


class Harness:
    def __init__(self, send: Send, sleeps: list[float], provider: FakeProvider | None) -> None:
        self.send = send
        self.sleeps = sleeps
        self.provider = provider


@pytest.fixture(params=["sync", "async"])
async def build(
    request: pytest.FixtureRequest, respx_mock: respx.MockRouter
) -> AsyncIterator[Callable[..., Harness]]:
    kind: str = request.param
    sync_clients: list[httpx.Client] = []
    async_clients: list[httpx.AsyncClient] = []

    def factory(*, max_attempts: int = 3, auth: bool = False) -> Harness:
        sleeps: list[float] = []
        if kind == "sync":
            provider = FakeProvider() if auth else None
            http = httpx.Client(base_url=BASE_URL)
            sync_clients.append(http)
            transport = SyncTransport(
                http,
                provider,
                max_attempts=max_attempts,
                sleeper=sleeps.append,  # type: ignore[arg-type]
            )

            async def send(*a: Any, **kw: Any) -> Any:
                return transport.request(*a, **kw)

        else:
            provider = AsyncFakeProvider() if auth else None
            ahttp = httpx.AsyncClient(base_url=BASE_URL)
            async_clients.append(ahttp)

            async def record(seconds: float) -> None:
                sleeps.append(seconds)

            atransport = AsyncTransport(
                ahttp,
                provider,
                max_attempts=max_attempts,
                sleeper=record,  # type: ignore[arg-type]
            )

            async def send(*a: Any, **kw: Any) -> Any:
                return await atransport.request(*a, **kw)

        return Harness(send, sleeps, provider)

    yield factory
    for c in sync_clients:
        c.close()
    for ac in async_clients:
        await ac.aclose()


OK = httpx.Response(200, json=envelope({"id": 1}))


async def test_success_unwraps_envelope_and_sends_headers(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(return_value=OK)
    h = build(auth=True)
    assert await h.send("GET", PATH) == {"id": 1}
    headers = route.calls.last.request.headers
    assert headers["authorization"] == "Bearer tok-1"
    assert headers["accept"] == "application/json"
    assert headers["user-agent"] == f"flexfund-sdk-python/{__version__}"


async def test_no_authorization_header_without_provider(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(return_value=OK)
    await build().send("GET", PATH)
    assert "authorization" not in route.calls.last.request.headers


async def test_query_is_php_encoded_and_json_body_sent(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post(URL).mock(return_value=httpx.Response(201, json=envelope(None)))
    h = build()
    result = await h.send(
        "POST",
        PATH,
        query={"flag": True, "ids": [3, 4], "skip": None, "f": {"k": "v"}},
        json={"a": 1},
    )
    assert result is None
    request = route.calls.last.request
    assert dict(request.url.params) == {"flag": "1", "ids[0]": "3", "ids[1]": "4", "f[k]": "v"}
    assert json.loads(request.content) == {"a": 1}


async def test_empty_json_body_is_still_sent(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post(URL).mock(return_value=OK)
    await build().send("POST", PATH, json={})
    assert route.calls.last.request.content == b"{}"


async def test_no_body_when_json_is_none(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(return_value=OK)
    await build().send("GET", PATH)
    assert route.calls.last.request.content == b""


async def test_envelope_without_data_returns_none(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(URL).mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok"})
    )
    assert await build().send("GET", PATH) is None


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="OK"),
        httpx.Response(200, text=""),
        httpx.Response(200, json=[1, 2]),
        httpx.Response(200, json={"data": {"id": 1}}),
        httpx.Response(200, json={"success": False, "message": "meh"}),
    ],
)
async def test_2xx_without_envelope_is_an_error(
    build: Callable[..., Harness], respx_mock: respx.MockRouter, response: httpx.Response
) -> None:
    respx_mock.get(URL).mock(return_value=response)
    with pytest.raises(ServerError) as exc:
        await build().send("GET", PATH)
    assert exc.value.status_code == 200


@pytest.mark.parametrize(
    ("method", "status", "calls"),
    [
        ("POST", 429, 3),
        ("PUT", 429, 3),
        ("GET", 429, 3),
        ("POST", 500, 1),
        ("POST", 503, 1),
        ("PUT", 502, 1),
        ("DELETE", 500, 1),
        ("PATCH", 500, 1),
        ("GET", 500, 3),
        ("GET", 503, 3),
        ("HEAD", 502, 3),
        ("OPTIONS", 500, 3),
        ("GET", 404, 1),
        ("GET", 400, 1),
        ("POST", 422, 1),
        ("POST", 409, 1),
    ],
)
async def test_retry_matrix(
    build: Callable[..., Harness],
    respx_mock: respx.MockRouter,
    method: str,
    status: int,
    calls: int,
) -> None:
    route = respx_mock.route(method=method, url=URL).mock(
        return_value=httpx.Response(status, json={"message": "x"})
    )
    h = build(max_attempts=3)
    with pytest.raises(Exception) as exc:
        await h.send(method, PATH)
    assert route.call_count == calls
    assert len(h.sleeps) == calls - 1
    assert exc.value.status_code == status  # type: ignore[attr-defined]
    expected = {
        429: RateLimitError,
        404: NotFoundError,
        409: ConflictError,
        422: ValidationError,
    }.get(status, ServerError)
    assert type(exc.value) is expected


async def test_429_then_success_on_post(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post(URL).mock(side_effect=[httpx.Response(429, json={}), OK])
    h = build()
    assert await h.send("POST", PATH, json={}) == {"id": 1}
    assert route.call_count == 2


async def test_max_attempts_one_never_retries(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(return_value=httpx.Response(500, json={}))
    h = build(max_attempts=1)
    with pytest.raises(ServerError):
        await h.send("GET", PATH)
    assert route.call_count == 1
    assert h.sleeps == []


async def test_backoff_delays_are_within_full_jitter_bounds(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(URL).mock(return_value=httpx.Response(500, json={}))
    h = build(max_attempts=4)
    with pytest.raises(ServerError):
        await h.send("GET", PATH)
    assert len(h.sleeps) == 3
    for attempt, delay in enumerate(h.sleeps, start=1):
        assert 0 <= delay <= 0.5 * 2 ** (attempt - 1)


async def test_retry_after_seconds_replaces_backoff(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(URL).mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "7"}, json={}), OK]
    )
    h = build()
    await h.send("GET", PATH)
    assert h.sleeps == [7.0]


async def test_retry_after_http_date(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    when = format_datetime(datetime.now(UTC) + timedelta(seconds=30), usegmt=True)
    respx_mock.get(URL).mock(
        side_effect=[httpx.Response(503, headers={"Retry-After": when}, json={}), OK]
    )
    h = build()
    await h.send("GET", PATH)
    assert len(h.sleeps) == 1
    assert 20 <= h.sleeps[0] <= 30


async def test_rate_limit_error_exposes_retry_after(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(URL).mock(
        return_value=httpx.Response(429, headers={"Retry-After": "3"}, json={"message": "slow"})
    )
    h = build(max_attempts=2)
    with pytest.raises(RateLimitError) as exc:
        await h.send("GET", PATH)
    assert exc.value.retry_after == 3
    assert h.sleeps == [3.0]


async def test_network_error_on_get_is_retried(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(
        side_effect=[httpx.ConnectError("x"), httpx.ReadTimeout("y"), OK]
    )
    h = build()
    assert await h.send("GET", PATH) == {"id": 1}
    assert route.call_count == 3
    assert len(h.sleeps) == 2


async def test_network_error_on_post_is_not_retried(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post(URL).mock(side_effect=httpx.ConnectError("boom"))
    h = build()
    with pytest.raises(ServerError, match="Failed to reach FlexFund: boom") as exc:
        await h.send("POST", PATH, json={})
    assert exc.value.status_code is None
    assert route.call_count == 1
    assert isinstance(exc.value.__cause__, httpx.ConnectError)


async def test_network_error_exhausts_attempts_on_get(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(side_effect=httpx.ConnectError("boom"))
    h = build()
    with pytest.raises(ServerError) as exc:
        await h.send("GET", PATH)
    assert exc.value.status_code is None
    assert route.call_count == 3


async def test_401_refreshes_and_replays_with_new_token(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(
        side_effect=[httpx.Response(401, json={"message": "expired"}), OK]
    )
    h = build(auth=True)
    assert await h.send("GET", PATH) == {"id": 1}
    assert h.provider is not None and h.provider.refreshes == 1
    # the refresh is told WHICH token was rejected, so concurrent 401s can share one refresh
    assert [t.token for t in h.provider.rejected if t is not None] == ["tok-1"]
    assert [c.request.headers["authorization"] for c in route.calls] == [
        "Bearer tok-1",
        "Bearer tok-2",
    ]
    assert h.sleeps == []


async def test_401_replay_does_not_consume_a_retry_attempt(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(URL).mock(side_effect=[httpx.Response(401, json={}), OK])
    assert await build(max_attempts=1, auth=True).send("GET", PATH) == {"id": 1}


async def test_second_401_raises_authentication_error(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(
        return_value=httpx.Response(401, json={"message": "bad creds"})
    )
    h = build(auth=True)
    with pytest.raises(AuthenticationError, match="bad creds"):
        await h.send("GET", PATH)
    assert route.call_count == 2
    assert h.provider is not None and h.provider.refreshes == 1


async def test_401_without_provider_is_not_replayed(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(return_value=httpx.Response(401, json={}))
    with pytest.raises(AuthenticationError):
        await build().send("GET", PATH)
    assert route.call_count == 1


async def test_401_replay_then_429_still_retries(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(
        side_effect=[httpx.Response(401, json={}), httpx.Response(429, json={}), OK]
    )
    h = build(auth=True)
    assert await h.send("GET", PATH) == {"id": 1}
    assert route.call_count == 3


def test_dot_segment_paths_rejected() -> None:
    from flexfund._http.policy import assert_safe_path

    assert_safe_path("v20260322/account/42")
    with pytest.raises(ValueError):
        assert_safe_path("v20260322/account/..")


def test_retry_after_is_capped() -> None:
    from flexfund._http.transport import _wait_seconds

    assert _wait_seconds(1, httpx.Response(429, headers={"Retry-After": "86400"})) == 60.0


async def test_an_undecodable_body_is_a_server_error_not_a_raw_httpx_error(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(URL).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Encoding": "gzip"},
            stream=httpx.ByteStream(b"definitely not gzip"),
        )
    )
    h = build()
    with pytest.raises(ServerError, match="could not be used") as exc:
        await h.send("GET", PATH)
    assert isinstance(exc.value.__cause__, httpx.DecodingError)
    assert route.call_count == 1


@pytest.mark.parametrize("digits", [400, 5000])
def test_an_absurd_retry_after_is_clamped_not_a_crash(digits: int) -> None:
    from flexfund._http.errors import MAX_RETRY_AFTER_HEADER_SECONDS, retry_after_seconds
    from flexfund._http.transport import _wait_seconds

    header = "9" * digits
    assert retry_after_seconds(header) == MAX_RETRY_AFTER_HEADER_SECONDS
    assert _wait_seconds(1, httpx.Response(429, headers={"Retry-After": header})) == 60.0


async def test_an_absurd_retry_after_on_the_last_attempt_still_raises_rate_limit_error(
    build: Callable[..., Harness], respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(URL).mock(
        return_value=httpx.Response(429, headers={"Retry-After": "9" * 5000}, json={})
    )
    h = build(max_attempts=1)
    with pytest.raises(RateLimitError) as exc:
        await h.send("GET", PATH)
    assert exc.value.retry_after is not None


@pytest.mark.parametrize("attempts", [0, -1])
def test_max_attempts_below_one_is_refused(attempts: int) -> None:
    with httpx.Client() as http, pytest.raises(ValueError, match="at least 1"):
        SyncTransport(http, max_attempts=attempts)
