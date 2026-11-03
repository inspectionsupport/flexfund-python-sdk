"""OAuth client credentials."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ClientCredentials:
    """A FlexFund OAuth client id/secret plus the scopes to request.

    ``client_secret`` is excluded from ``repr`` so it cannot leak into logs or tracebacks.
    """

    client_id: str
    client_secret: str = field(repr=False)
    scopes: tuple[str, ...] = ()

    def scope_string(self) -> str:
        """Scopes space-joined, as OAuth2 expects."""
        return " ".join(self.scopes)

    def sorted_scopes(self) -> tuple[str, ...]:
        return tuple(sorted(self.scopes))
