"""Access token value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


def _seconds(value: Any) -> int:
    """``expires_in`` as whole seconds. Absent or empty means 0 (renewed on every use)."""
    if value is None or value == "":
        return 0
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise ValueError(f"expires_in must be a number of seconds, not {type(value).__name__}")
    try:
        seconds = int(float(value))
    except (ValueError, OverflowError) as exc:
        raise ValueError("expires_in is not a number of seconds") from exc
    if seconds < 0:
        raise ValueError("expires_in is negative")
    return seconds


@dataclass(frozen=True, slots=True)
class AccessToken:
    """A ``client_credentials`` access token. There is no refresh token in this grant.

    ``token`` is excluded from ``repr`` so it cannot leak into logs or tracebacks.
    """

    token: str = field(repr=False)
    expires_at: datetime
    """Timezone-aware, UTC."""
    scopes: tuple[str, ...] = ()

    @classmethod
    def from_token_response(cls, body: dict[str, Any], now: datetime | None = None) -> AccessToken:
        """Parse a ``/oauth/token`` response body.

        Raises ``ValueError`` for a body that is not a usable token response (no token, a
        non-numeric or negative ``expires_in``); callers turn that into ``AuthenticationError``.
        """
        now = now or datetime.now(UTC)
        access_token = body.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("access_token is missing or is not a non-empty string")
        expires_in = _seconds(body.get("expires_in"))
        scope = body.get("scope")
        if isinstance(scope, list | tuple):
            scope = " ".join(str(item) for item in scope)
        scope = str(scope or "")
        return cls(
            token=access_token,
            expires_at=now + timedelta(seconds=expires_in),
            scopes=tuple(scope.split(" ")) if scope else (),
        )

    def is_expiring_within(self, seconds: float) -> bool:
        return self.expires_at <= datetime.now(UTC) + timedelta(seconds=seconds)

    def to_dict(self) -> dict[str, Any]:
        """A JSON-safe representation for :class:`~flexfund.auth.cache.TokenCache` backends."""
        return {
            "token": self.token,
            "expiresAt": self.expires_at.isoformat(),
            "scopes": list(self.scopes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AccessToken:
        """Rebuild from :meth:`to_dict` output. Raises on a malformed entry."""
        expires_at = datetime.fromisoformat(data["expiresAt"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        token = data["token"]
        if not isinstance(token, str) or not token:
            raise ValueError("cached token is not a non-empty string")
        return cls(token=token, expires_at=expires_at, scopes=tuple(data.get("scopes") or ()))
