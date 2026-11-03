"""Obtains and caches a FlexFund ``client_credentials`` access token.

POSTs ``grant_type=client_credentials`` + ``client_id`` + ``client_secret`` + ``scope``
(space-joined) form-encoded to ``{base_url}/oauth/token`` and expects
``{token_type, expires_in, access_token, scope}`` back.

Caching has two tiers: in-memory (this instance) always, then an optional pluggable
cache shared across processes. The cache key hashes base URL + client id + sorted scopes;
the client secret is never part of it, never cached, and never logged.

There is no refresh token in this grant, so :meth:`TokenProvider.refresh` always means
"mint a brand new token" - unless the caller names the token the server just rejected and
somebody else has already replaced it, in which case that newer token is reused. That is what
keeps N concurrent requests, all rejected for the same old token, down to ONE ``/oauth/token``
call instead of N.

Both providers use their own ``httpx`` client (no bearer, no retry), separate from the
resource client, and fetch under a lock with double-checked locking so concurrent callers
trigger exactly one ``/oauth/token`` request.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx

from flexfund._http.errors import network_error, retry_after_seconds
from flexfund.auth.cache import AsyncTokenCache, TokenCache
from flexfund.auth.credentials import ClientCredentials
from flexfund.auth.token import AccessToken
from flexfund.errors import AuthenticationError, FlexFundError, RateLimitError, ServerError

_log = logging.getLogger("flexfund")

# Seconds before real expiry at which a token counts as due for renewal, to absorb clock
# skew plus the latency of the request the token is about to be used for.
EXPIRY_BUFFER_SECONDS = 60


def cache_key(base_url: str, credentials: ClientCredentials) -> str:
    """Never includes the secret, so the key itself is safe to log."""
    parts = "|".join(
        [base_url.rstrip("/"), credentials.client_id, ",".join(credentials.sorted_scopes())]
    )
    return "flexfund_token_" + hashlib.sha256(parts.encode()).hexdigest()


def _assert_credentials_present(credentials: ClientCredentials) -> None:
    """Fail before the request when there is nothing to authenticate with.

    The server's answer is misleading: an empty client_id yields a 400 ``invalid_request``
    that reads like a malformed SDK request rather than "never configured". Making the
    request at all is also pure cost, and a retry loop for queue-backed callers.
    """
    missing = []
    if not credentials.client_id.strip():
        missing.append("client id")
    if not credentials.client_secret.strip():
        missing.append("client secret")
    if missing:
        raise AuthenticationError(
            f"No FlexFund {' or '.join(missing)} configured, so no token was requested. "
            "Check where your credentials are loaded from."
        )


def _describe_failure(status: int, decoded: dict[str, Any] | None) -> str:
    """Say what actually went wrong.

    ``/oauth/token`` is a league/oauth2-server endpoint, so it answers
    ``{error, error_description, hint}``, never the FlexFund envelope. ``hint`` is the most
    useful part: it names the offending parameter.
    """
    if decoded is None:
        return (
            f"FlexFund rejected the client_credentials request (status {status}) "
            "and returned no JSON body."
        )

    # FlexFund's own envelope, in case a non-OAuth error surfaces (a 404 from a wrong base URL).
    message = decoded.get("message")
    if message is not None:
        text = "; ".join(str(m) for m in message) if isinstance(message, list) else str(message)
        return f"{text} (status {status})"

    parts = [
        str(decoded[key])
        for key in ("error", "error_description", "hint")
        if decoded.get(key) not in (None, "")
    ]
    if not parts:
        return f"FlexFund rejected the client_credentials request (status {status})."
    return (
        f"FlexFund rejected the client_credentials request (status {status}): {' — '.join(parts)}"
    )


def _form(credentials: ClientCredentials) -> dict[str, str]:
    return {
        "grant_type": "client_credentials",
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scope": credentials.scope_string(),
    }


def _without_token(
    decoded: dict[str, Any] | None, raw_body: str
) -> tuple[dict[str, Any] | None, str | None]:
    """The body to attach to an error, minus any access token in it.

    Error trackers serialize exception attributes, so a live bearer token on ``.body`` or
    ``.raw_body`` would end up stored somewhere it can be read. The raw text can't be edited
    safely, so it is dropped whenever the decoded body carried a token.
    """
    if decoded is None or "access_token" not in decoded:
        return decoded, raw_body
    return {**decoded, "access_token": "[redacted]"}, None


def _parse_token_response(status: int, headers: Mapping[str, str], raw_body: str) -> AccessToken:
    try:
        parsed = json.loads(raw_body)
    except ValueError:
        parsed = None
    decoded = parsed if isinstance(parsed, dict) else None
    body, raw = _without_token(decoded, raw_body)

    # An outage or a rate limit is not a credentials problem: callers that treat
    # AuthenticationError as permanent must not drop work over a transient failure.
    if status == 429:
        raise RateLimitError(
            f"FlexFund rate-limited the token request (status {status}).",
            status,
            body,
            raw,
            retry_after=retry_after_seconds(headers.get("Retry-After")),
        )
    if status >= 500:
        raise ServerError(
            f"FlexFund's /oauth/token endpoint failed (status {status}); try again later.",
            status,
            body,
            raw,
        )
    if status != 200 or decoded is None or "access_token" not in decoded:
        raise AuthenticationError(_describe_failure(status, decoded), status, body, raw)
    try:
        return AccessToken.from_token_response(decoded)
    except (ValueError, TypeError, OverflowError) as exc:
        raise AuthenticationError(
            f"FlexFund returned a malformed token response: {exc}", status, body, raw
        ) from exc


def _unreachable(exc: httpx.HTTPError) -> FlexFundError:
    """No usable answer from /oauth/token: a ServerError, like any other network failure."""
    return network_error(f"Failed to reach FlexFund's /oauth/token endpoint: {exc}")


def _cache_failed(operation: str, exc: Exception) -> None:
    """A token cache that is down (Redis unreachable, say) costs a token request, not the call.

    Only the exception type is logged: a backend's message can carry its connection string.
    """
    _log.warning(
        "FlexFund token cache %s failed (%s); continuing without it", operation, type(exc).__name__
    )


def _from_cached(data: dict[str, Any] | None) -> AccessToken | None:
    if not isinstance(data, dict):
        return None
    try:
        return AccessToken.from_dict(data)
    except Exception:  # A malformed/stale entry must never break token acquisition: it is a miss.
        return None


def _ttl(token: AccessToken) -> int:
    return max(0, int((token.expires_at - datetime.now(UTC)).total_seconds()))


class TokenProvider:
    """Synchronous token provider (thread-safe)."""

    def __init__(
        self,
        http_client: httpx.Client,
        base_url: str,
        credentials: ClientCredentials,
        cache: TokenCache | None = None,
    ) -> None:
        self._http = http_client
        self._base_url = base_url
        self._credentials = credentials
        self._cache = cache
        self._token: AccessToken | None = None
        self._lock = threading.Lock()
        self._key = cache_key(base_url, credentials)

    def _fresh_local(self) -> AccessToken | None:
        token = self._token
        if token is not None and not token.is_expiring_within(EXPIRY_BUFFER_SECONDS):
            return token
        return None

    def token(self) -> AccessToken:
        """A valid token, minting one if needed. Never within 60s of expiry."""
        if (token := self._fresh_local()) is not None:
            return token
        with self._lock:
            if (token := self._fresh_local()) is not None:
                return token
            if self._cache is not None:
                cached = _from_cached(self._cache_get())
                if cached is not None and not cached.is_expiring_within(EXPIRY_BUFFER_SECONDS):
                    self._token = cached
                    return cached
            return self._fetch_and_cache()

    def refresh(self, rejected: AccessToken | None = None) -> AccessToken:
        """Discard the cached token (both tiers) and mint a new one.

        Pass the token the server rejected (a 401) to coalesce concurrent refreshes: once the
        lock is held, a current token that is not ``rejected`` means another caller (or another
        process, through the shared cache) already replaced it, so that one is returned instead
        of minting yet another. Without ``rejected`` the refresh is unconditional.
        """
        with self._lock:
            reusable = self._replacement_for(rejected) if rejected is not None else None
            if reusable is not None:
                return reusable
            self._token = None
            self._cache_delete()
            return self._fetch_and_cache()

    def _replacement_for(self, rejected: AccessToken) -> AccessToken | None:
        current = self._token
        if current is not None and current.token != rejected.token:
            return current
        if self._cache is not None:
            cached = _from_cached(self._cache_get())
            if (
                cached is not None
                and cached.token != rejected.token
                and not cached.is_expiring_within(EXPIRY_BUFFER_SECONDS)
            ):
                self._token = cached
                return cached
        return None

    def _fetch_and_cache(self) -> AccessToken:
        token = self._fetch()
        self._token = token
        self._cache_set(token)
        return token

    def _cache_get(self) -> dict[str, Any] | None:
        if self._cache is None:
            return None
        try:
            return self._cache.get(self._key)
        except Exception as exc:
            _cache_failed("get", exc)
            return None

    def _cache_set(self, token: AccessToken) -> None:
        if self._cache is None:
            return
        try:
            self._cache.set(self._key, token.to_dict(), _ttl(token))
        except Exception as exc:
            _cache_failed("set", exc)

    def _cache_delete(self) -> None:
        if self._cache is None:
            return
        try:
            self._cache.delete(self._key)
        except Exception as exc:
            _cache_failed("delete", exc)

    def _fetch(self) -> AccessToken:
        _assert_credentials_present(self._credentials)
        try:
            response = self._http.post(
                self._base_url.rstrip("/") + "/oauth/token", data=_form(self._credentials)
            )
        except httpx.HTTPError as exc:
            raise _unreachable(exc) from exc
        return _parse_token_response(response.status_code, response.headers, response.text)


class AsyncTokenProvider:
    """Asynchronous token provider (safe for concurrent tasks)."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        credentials: ClientCredentials,
        cache: AsyncTokenCache | None = None,
    ) -> None:
        self._http = http_client
        self._base_url = base_url
        self._credentials = credentials
        self._cache = cache
        self._token: AccessToken | None = None
        self._lock = asyncio.Lock()
        self._key = cache_key(base_url, credentials)

    def _fresh_local(self) -> AccessToken | None:
        token = self._token
        if token is not None and not token.is_expiring_within(EXPIRY_BUFFER_SECONDS):
            return token
        return None

    async def token(self) -> AccessToken:
        """A valid token, minting one if needed. Never within 60s of expiry."""
        if (token := self._fresh_local()) is not None:
            return token
        async with self._lock:
            if (token := self._fresh_local()) is not None:
                return token
            if self._cache is not None:
                cached = _from_cached(await self._cache_get())
                if cached is not None and not cached.is_expiring_within(EXPIRY_BUFFER_SECONDS):
                    self._token = cached
                    return cached
            return await self._fetch_and_cache()

    async def refresh(self, rejected: AccessToken | None = None) -> AccessToken:
        """Discard the cached token (both tiers) and mint a new one.

        Pass the token the server rejected to coalesce concurrent refreshes; see
        :meth:`TokenProvider.refresh`.
        """
        async with self._lock:
            reusable = await self._replacement_for(rejected) if rejected is not None else None
            if reusable is not None:
                return reusable
            self._token = None
            await self._cache_delete()
            return await self._fetch_and_cache()

    async def _replacement_for(self, rejected: AccessToken) -> AccessToken | None:
        current = self._token
        if current is not None and current.token != rejected.token:
            return current
        if self._cache is not None:
            cached = _from_cached(await self._cache_get())
            if (
                cached is not None
                and cached.token != rejected.token
                and not cached.is_expiring_within(EXPIRY_BUFFER_SECONDS)
            ):
                self._token = cached
                return cached
        return None

    async def _fetch_and_cache(self) -> AccessToken:
        token = await self._fetch()
        self._token = token
        await self._cache_set(token)
        return token

    async def _cache_get(self) -> dict[str, Any] | None:
        if self._cache is None:
            return None
        try:
            return await self._cache.get(self._key)
        except Exception as exc:
            _cache_failed("get", exc)
            return None

    async def _cache_set(self, token: AccessToken) -> None:
        if self._cache is None:
            return
        try:
            await self._cache.set(self._key, token.to_dict(), _ttl(token))
        except Exception as exc:
            _cache_failed("set", exc)

    async def _cache_delete(self) -> None:
        if self._cache is None:
            return
        try:
            await self._cache.delete(self._key)
        except Exception as exc:
            _cache_failed("delete", exc)

    async def _fetch(self) -> AccessToken:
        _assert_credentials_present(self._credentials)
        try:
            response = await self._http.post(
                self._base_url.rstrip("/") + "/oauth/token", data=_form(self._credentials)
            )
        except httpx.HTTPError as exc:
            raise _unreachable(exc) from exc
        return _parse_token_response(response.status_code, response.headers, response.text)
