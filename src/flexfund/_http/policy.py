"""Sans-IO retry and envelope decisions shared by the sync and async transports."""

from __future__ import annotations

import json
import random
from collections.abc import Mapping
from typing import Any

from flexfund._http.errors import map_response

IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

MAX_RETRY_AFTER_SECONDS = 60.0
"""Longest we will sleep on a server-supplied ``Retry-After``; a hostile or broken server
must not be able to park the caller for hours."""

BASE_DELAY_SECONDS = 0.5
"""Backoff ceiling for attempt 1; it doubles per attempt."""

_default_rng = random.Random()


def is_idempotent(method: str) -> bool:
    return method.upper() in IDEMPOTENT_METHODS


def is_retryable(status: int, method: str) -> bool:
    """429 is retried regardless of method (the request was never processed).

    5xx is retried only for idempotent methods: FlexFund's write endpoints are not
    guaranteed idempotent, and after a 5xx we cannot tell whether the write already landed.
    """
    if status == 429:
        return True
    return status >= 500 and is_idempotent(method)


def backoff_delay(attempt: int, rng: random.Random | None = None) -> float:
    """Exponential backoff with full jitter: uniform(0, 0.5 * 2**(attempt - 1)).

    Full jitter (rather than a small offset on a fixed backoff) stops many clients that
    failed at the same instant from retrying in lockstep.
    """
    ceiling = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
    return (rng or _default_rng).uniform(0.0, ceiling)


def unwrap_envelope(status: int, headers: Mapping[str, str], raw_body: str) -> Any:
    """Return ``data`` from a ``{success, message, data}`` envelope.

    A "2xx" that is not a dict with a truthy ``success`` is a server-side anomaly and is
    raised as an error rather than silently returned as ``None``.
    """
    try:
        decoded = json.loads(raw_body) if raw_body.strip() else None
    except ValueError:
        decoded = None
    if not isinstance(decoded, dict) or not decoded.get("success"):
        raise map_response(status, headers, raw_body)
    return decoded.get("data")


def assert_safe_path(path: str) -> None:
    """Reject ``.``/``..`` segments, which URL normalization would turn into another endpoint."""
    if any(segment in (".", "..") for segment in path.split("/")):
        raise ValueError(f"Unsafe request path {path!r}: dot segments are not allowed.")
