"""Maps non-2xx FlexFund responses to typed exceptions (sans-IO port of PHP ``ErrorMapper``).

FlexFund emits errors in two shapes:

* Standard: ``{success: false, message: str, code: str, status: int, errors: ...}``.
  A 403 also arrives as ``code: HTTP_ERROR`` (there is no dedicated "forbidden" code), so
  the mapping dispatches on HTTP status, never on ``code``.
* The 422 reshape:
  ``{success: false, error_code: 422, message: [str, ...], errors: {field: [msgs]}}``.
  There is no ``code`` key and ``message`` is a *list*.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from flexfund.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    FlexFundError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)


def map_response(status: int, headers: Mapping[str, str], raw_body: str) -> FlexFundError:
    """Build (not raise) the right exception for a non-2xx response."""
    body = _decode(raw_body)
    message = _extract_message(body, status)

    if status == 401:
        return AuthenticationError(message, status, body, raw_body)
    if status == 403:
        return AuthorizationError(message, status, body, raw_body)
    if status == 404:
        return NotFoundError(message, status, body, raw_body)
    # 409 is a PERMANENT conflict: it must not fall into the ServerError default, or a
    # queue-backed caller reading "server error" would retry it forever.
    if status == 409:
        return ConflictError(message, status, body, raw_body)
    if status == 422:
        return ValidationError(message, status, body, raw_body)
    if status == 429:
        return RateLimitError(
            message,
            status,
            body,
            raw_body,
            retry_after=retry_after_seconds(_header(headers, "Retry-After")),
        )
    # 5xx and anything unanticipated (a stray 400, a 3xx with no Location, a 2xx
    # without the envelope): a real response with a real status, just not one of the
    # shapes above, so ServerError is the honest catch-all.
    return ServerError(message, status, body, raw_body)


def network_error(reason: str) -> FlexFundError:
    """The error for a request that never got a usable HTTP response."""
    return ServerError(reason, None, None, None)


# The longest Retry-After honoured as written. Anything longer (over 300 years) is clamped
# rather than parsed: int() of thousands of digits is slow or raises, and float() overflows.
MAX_RETRY_AFTER_HEADER_SECONDS = 9_999_999_999


def retry_after_seconds(value: str | None) -> int | None:
    """Parse ``Retry-After`` (digits or an RFC 7231 HTTP-date) into seconds, clamped at 0."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if value.isascii() and value.isdigit():
        if len(value.lstrip("0")) > len(str(MAX_RETRY_AFTER_HEADER_SECONDS)):
            return MAX_RETRY_AFTER_HEADER_SECONDS
        return min(int(value), MAX_RETRY_AFTER_HEADER_SECONDS)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0, int((when - datetime.now(UTC)).total_seconds()))


def _header(headers: Mapping[str, str], name: str) -> str | None:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None


def _decode(raw_body: str) -> dict[str, Any] | None:
    if not raw_body.strip():
        return None
    try:
        decoded = json.loads(raw_body)
    except ValueError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _extract_message(body: dict[str, Any] | None, status: int) -> str:
    if body is None:
        return (
            f"FlexFund API request failed with status {status} "
            "and a non-JSON or empty response body"
        )
    message = body.get("message")
    # The 422 reshape sends `message` as a list of per-field strings; every other shape
    # sends a single string.
    if isinstance(message, list):
        return "; ".join(str(m) for m in message) if message else "Validation failed"
    if isinstance(message, str) and message:
        return message
    return f"FlexFund API request failed with status {status}"
