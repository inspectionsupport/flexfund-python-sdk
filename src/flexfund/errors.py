"""Exception hierarchy raised by the SDK.

Every failure surfaces as a :class:`FlexFundError` subclass; ``httpx`` exceptions
never leak out of the resource methods, and neither does ``pydantic`` for anything the server
sent: a response that does not match the expected schema is a :class:`ResponseError`, and a
malformed token response is an :class:`AuthenticationError`.

The one deliberate exception is building a *request* model yourself: that raises
``pydantic.ValidationError`` locally, before anything is sent, because it is a mistake in your
own code and not a failure of the API.

Note: :class:`ValidationError` clashes by name with ``pydantic.ValidationError``.
The clash is accepted; import this module as ``from flexfund import errors``
and refer to ``errors.ValidationError`` when both are in play.
"""

from __future__ import annotations

from typing import Any


class FlexFundError(Exception):
    """Base class for every error the SDK raises."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        body: dict[str, Any] | None = None,
        raw_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        """HTTP status, or ``None`` when no response was received."""
        self.body = body
        """The decoded JSON error body, when there was one."""
        self.raw_body = raw_body
        """The undecoded response body, when there was one."""


class AuthenticationError(FlexFundError):
    """HTTP 401, or any failure to obtain an access token."""


class AuthorizationError(FlexFundError):
    """HTTP 403: the token lacks a scope, or the account's role forbids the action."""


class NotFoundError(FlexFundError):
    """HTTP 404."""


class ConflictError(FlexFundError):
    """HTTP 409: a permanent conflict. Retrying the same request will not help."""


class ValidationError(FlexFundError):
    """HTTP 422."""

    @property
    def errors(self) -> dict[str, list[str]]:
        """Per-field messages from the body's ``errors`` member (empty if absent)."""
        raw = (self.body or {}).get("errors")
        if not isinstance(raw, dict):
            return {}
        result: dict[str, list[str]] = {}
        for field, messages in raw.items():
            if isinstance(messages, list):
                result[str(field)] = [str(m) for m in messages]
            else:
                result[str(field)] = [str(messages)]
        return result


class RateLimitError(FlexFundError):
    """HTTP 429."""

    def __init__(
        self,
        message: str,
        status_code: int | None = 429,
        body: dict[str, Any] | None = None,
        raw_body: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, status_code, body, raw_body)
        self.retry_after = retry_after
        """Seconds the server asked us to wait, when it said."""


class ResponseError(FlexFundError):
    """The API answered successfully (HTTP 2xx) but the body does not match the expected schema.

    This is not a failed request: the call went through. It means the SDK cannot turn what came
    back into a model, typically because the API and this SDK version disagree about the shape.
    ``body`` holds the decoded ``data`` when it was a JSON object, and the original
    ``pydantic.ValidationError`` is available as ``__cause__``. Retrying will not help.
    """


class ServerError(FlexFundError):
    """HTTP 5xx, any other unexpected non-2xx, and network failures (``status_code=None``)."""
