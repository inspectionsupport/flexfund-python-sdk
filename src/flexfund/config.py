"""HTTP tuning knobs for the FlexFund clients."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClientConfig:
    """Connection settings shared by the sync and async clients."""

    base_url: str
    connect_timeout: float = 5.0
    """Seconds allowed to establish a connection."""
    timeout: float = 30.0
    """Seconds allowed for the rest of a request (read, write, pool)."""
    max_attempts: int = 3
    """Total attempts, including the first, for a retryable failure."""
    verify: bool = True
    """Whether to verify TLS certificates."""
