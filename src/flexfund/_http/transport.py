"""The transports every generated resource method calls into.

Responsibilities (a port of PHP ``Transport``):

* Add ``Authorization: Bearer <token>`` via the token provider.
* Unwrap the ``{success, message, data}`` envelope and return only ``data``. Hydration into
  models happens in the generated resources, so this stays agnostic of endpoint shapes.
* Route any non-2xx response through :func:`~flexfund._http.errors.map_response`.
* Retry 429s (any method) and, for GET/HEAD/OPTIONS only, 5xx responses and network
  failures, with full-jitter exponential backoff; ``Retry-After`` replaces the backoff.
  Writes are never retried after a 5xx or a network error because we cannot tell whether
  they already landed.
* On a single 401, ask the token provider to mint a new token (naming the token that was
  rejected, so concurrent requests rejected for the same token share one refresh) and replay
  the same request once, without consuming a retry attempt. A second 401 raises
  ``AuthenticationError``: ``client_credentials`` has no refresh token, so it means the
  credentials are bad.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from flexfund._http.errors import map_response, network_error, retry_after_seconds
from flexfund._http.policy import (
    MAX_RETRY_AFTER_SECONDS,
    assert_safe_path,
    backoff_delay,
    is_idempotent,
    is_retryable,
    unwrap_envelope,
)
from flexfund._http.query import encode_query
from flexfund._version import __version__
from flexfund.auth.provider import AsyncTokenProvider, TokenProvider
from flexfund.errors import FlexFundError

USER_AGENT = f"flexfund-sdk-python/{__version__}"


def _base_headers() -> dict[str, str]:
    return {"Accept": "application/json", "User-Agent": USER_AGENT}


def _wait_seconds(attempt: int, response: httpx.Response | None) -> float:
    if response is not None:
        retry_after = retry_after_seconds(response.headers.get("Retry-After"))
        if retry_after is not None:
            return min(float(retry_after), MAX_RETRY_AFTER_SECONDS)
    return backoff_delay(attempt)


def _checked_max_attempts(max_attempts: int) -> int:
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be at least 1 (got {max_attempts}).")
    return max_attempts


def _unusable_response(exc: httpx.HTTPError) -> FlexFundError:
    """A response arrived but could not be used (a body that fails to decode, too many
    redirects on a caller's client that follows them). Not retried: unlike a dropped
    connection, sending the same request again would most likely get the same answer."""
    return network_error(f"FlexFund's response could not be used: {exc}")


class SyncTransport:
    def __init__(
        self,
        http_client: httpx.Client,
        token_provider: TokenProvider | None = None,
        *,
        max_attempts: int = 3,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._http = http_client
        self._token_provider = token_provider
        self._max_attempts = _checked_max_attempts(max_attempts)
        self._sleeper = sleeper

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Send a request and return the envelope's ``data``.

        ``path`` is relative (``"v20260322/transaction/42"``) and joined to the client's
        base URL.
        """
        assert_safe_path(path)
        pairs = encode_query(query)
        params = httpx.QueryParams(pairs) if pairs else None
        attempt = 1
        retried_auth = False
        while True:
            headers = _base_headers()
            sent_token = None
            if self._token_provider is not None:
                sent_token = self._token_provider.token()
                headers["Authorization"] = f"Bearer {sent_token.token}"

            try:
                response = self._http.request(
                    method, path, params=params, json=json, headers=headers
                )
            except httpx.TransportError as exc:
                if is_idempotent(method) and attempt < self._max_attempts:
                    self._sleeper(_wait_seconds(attempt, None))
                    attempt += 1
                    continue
                raise network_error(f"Failed to reach FlexFund: {exc}") from exc
            except httpx.HTTPError as exc:
                raise _unusable_response(exc) from exc

            status = response.status_code
            if 200 <= status < 300:
                return unwrap_envelope(status, response.headers, response.text)

            if status == 401 and self._token_provider is not None and not retried_auth:
                self._token_provider.refresh(rejected=sent_token)
                retried_auth = True
                continue

            if is_retryable(status, method) and attempt < self._max_attempts:
                self._sleeper(_wait_seconds(attempt, response))
                attempt += 1
                continue

            raise map_response(status, response.headers, response.text)


class AsyncTransport:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        token_provider: AsyncTokenProvider | None = None,
        *,
        max_attempts: int = 3,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._http = http_client
        self._token_provider = token_provider
        self._max_attempts = _checked_max_attempts(max_attempts)
        self._sleeper = sleeper

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Send a request and return the envelope's ``data``. See :meth:`SyncTransport.request`."""
        assert_safe_path(path)
        pairs = encode_query(query)
        params = httpx.QueryParams(pairs) if pairs else None
        attempt = 1
        retried_auth = False
        while True:
            headers = _base_headers()
            sent_token = None
            if self._token_provider is not None:
                sent_token = await self._token_provider.token()
                headers["Authorization"] = f"Bearer {sent_token.token}"

            try:
                response = await self._http.request(
                    method, path, params=params, json=json, headers=headers
                )
            except httpx.TransportError as exc:
                if is_idempotent(method) and attempt < self._max_attempts:
                    await self._sleeper(_wait_seconds(attempt, None))
                    attempt += 1
                    continue
                raise network_error(f"Failed to reach FlexFund: {exc}") from exc
            except httpx.HTTPError as exc:
                raise _unusable_response(exc) from exc

            status = response.status_code
            if 200 <= status < 300:
                return unwrap_envelope(status, response.headers, response.text)

            if status == 401 and self._token_provider is not None and not retried_auth:
                await self._token_provider.refresh(rejected=sent_token)
                retried_auth = True
                continue

            if is_retryable(status, method) and attempt < self._max_attempts:
                await self._sleeper(_wait_seconds(attempt, response))
                attempt += 1
                continue

            raise map_response(status, response.headers, response.text)
