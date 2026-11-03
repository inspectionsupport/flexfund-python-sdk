"""The public sync and async clients."""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from types import TracebackType
from typing import Any, Self
from urllib.parse import urlsplit

import httpx

from flexfund._generated_client import _AsyncResourceAccessors, _ResourceAccessors
from flexfund._http.transport import AsyncTransport, SyncTransport
from flexfund.auth.cache import AsyncTokenCache, InMemoryTokenCache, TokenCache
from flexfund.auth.credentials import ClientCredentials
from flexfund.auth.provider import AsyncTokenProvider, TokenProvider


class _AsyncInMemoryTokenCache:
    """Adapts the in-memory cache to the async protocol (its operations never block)."""

    def __init__(self) -> None:
        self._inner = InMemoryTokenCache()

    async def get(self, key: str) -> dict[str, Any] | None:
        return self._inner.get(key)

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self._inner.set(key, value, ttl_seconds)

    async def delete(self, key: str) -> None:
        self._inner.delete(key)


def _is_local(base_url: str) -> bool:
    host = urlsplit(base_url).hostname or ""
    return host in {"localhost", "127.0.0.1", "::1"} or host.endswith((".localhost", ".test"))


def _require_https(base_url: str) -> None:
    """Refuse plain HTTP (it would send the client secret and bearer tokens in cleartext),
    except for local development hosts."""
    scheme = urlsplit(base_url).scheme
    if scheme == "https" or (scheme == "http" and _is_local(base_url)):
        return
    raise ValueError(
        f"base_url must use https (got {base_url!r}); plain http is allowed only for "
        "localhost, 127.0.0.1, [::1], *.localhost and *.test."
    )


def _resolve_base_url(base_url: str) -> str:
    """The API's base URL, as FlexFund support gave it to you. The SDK ships no defaults, so
    there is no built-in endpoint to fall back to."""
    if not base_url.strip():
        raise ValueError("base_url is required: ask FlexFund support for your API endpoint URL.")
    _require_https(base_url)
    return base_url


def _check_http_client(http_client: httpx.Client | httpx.AsyncClient, resolved: str) -> None:
    """A caller's ``http_client`` receives the bearer token on every request, so it must point
    at the same origin the token was minted for, over the same HTTPS rule as ``base_url``."""
    theirs = str(http_client.base_url)
    if not theirs:
        raise ValueError(f"http_client must have base_url set (to {resolved!r}).")
    _require_https(theirs)
    ours = httpx.URL(resolved)
    actual = http_client.base_url
    if (actual.scheme, actual.host, actual.port) != (ours.scheme, ours.host, ours.port):
        raise ValueError(
            f"http_client's base_url {theirs!r} is not on {resolved!r}, the host the access "
            "token is issued for."
        )


def _warn_if_unverified(verify: bool, resolved: str) -> None:
    if not verify and not _is_local(resolved):
        warnings.warn(
            f"TLS certificate verification is off for {resolved}; the client secret and "
            "access tokens can be intercepted. Use verify=False only for local development.",
            stacklevel=3,
        )


def _timeout(timeout: float, connect_timeout: float) -> httpx.Timeout:
    return httpx.Timeout(timeout, connect=connect_timeout)


class FlexFundClient(_ResourceAccessors):
    """Synchronous FlexFund client. Resources are attributes, e.g. ``client.transaction``.

    Use it as a context manager (or call :meth:`close`) to release connections. Only the
    ``httpx`` clients the SDK created itself are closed; an ``http_client`` you pass in is
    yours to close.
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str,
        scopes: Sequence[str] = (),
        timeout: float = 30.0,
        connect_timeout: float = 5.0,
        max_attempts: int = 3,
        token_cache: TokenCache | None = None,
        verify: bool = True,
        http_client: httpx.Client | None = None,
    ) -> None:
        resolved = _resolve_base_url(base_url)
        if http_client is not None:
            _check_http_client(http_client, resolved)
        _warn_if_unverified(verify, resolved)
        credentials = ClientCredentials(client_id, client_secret, tuple(scopes))
        limits = _timeout(timeout, connect_timeout)

        self._owned: list[httpx.Client] = []
        # The token client is separate from the resource client: no bearer, no retry.
        token_http = httpx.Client(timeout=limits, verify=verify)
        self._owned.append(token_http)
        if http_client is None:
            http_client = httpx.Client(base_url=resolved, timeout=limits, verify=verify)
            self._owned.append(http_client)

        cache = token_cache if token_cache is not None else InMemoryTokenCache()
        provider = TokenProvider(token_http, resolved, credentials, cache)
        self._transport = SyncTransport(http_client, provider, max_attempts=max_attempts)

    def close(self) -> None:
        for client in self._owned:
            client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class AsyncFlexFundClient(_AsyncResourceAccessors):
    """Asynchronous FlexFund client. Use ``async with`` (or ``await client.aclose()``)."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str,
        scopes: Sequence[str] = (),
        timeout: float = 30.0,
        connect_timeout: float = 5.0,
        max_attempts: int = 3,
        token_cache: AsyncTokenCache | None = None,
        verify: bool = True,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        resolved = _resolve_base_url(base_url)
        if http_client is not None:
            _check_http_client(http_client, resolved)
        _warn_if_unverified(verify, resolved)
        credentials = ClientCredentials(client_id, client_secret, tuple(scopes))
        limits = _timeout(timeout, connect_timeout)

        self._owned: list[httpx.AsyncClient] = []
        token_http = httpx.AsyncClient(timeout=limits, verify=verify)
        self._owned.append(token_http)
        if http_client is None:
            http_client = httpx.AsyncClient(base_url=resolved, timeout=limits, verify=verify)
            self._owned.append(http_client)

        cache: AsyncTokenCache = (
            token_cache if token_cache is not None else _AsyncInMemoryTokenCache()
        )
        provider = AsyncTokenProvider(token_http, resolved, credentials, cache)
        self._transport = AsyncTransport(http_client, provider, max_attempts=max_attempts)

    async def aclose(self) -> None:
        for client in self._owned:
            await client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()
