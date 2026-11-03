"""Pluggable token caches.

Implement :class:`TokenCache` (or :class:`AsyncTokenCache` for the async client) to share
tokens across processes, e.g. with Redis. Values are JSON-safe dicts; keys are already
hashed and contain no secret.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TokenCache(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None: ...

    def delete(self, key: str) -> None: ...


@runtime_checkable
class AsyncTokenCache(Protocol):
    async def get(self, key: str) -> dict[str, Any] | None: ...

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None: ...

    async def delete(self, key: str) -> None: ...


class InMemoryTokenCache:
    """Process-local cache with TTLs. Not shared across processes. Safe for threads."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            expires, value = entry
            if expires <= time.monotonic():
                del self._items[key]
                return None
            return dict(value)

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        with self._lock:
            self._items[key] = (time.monotonic() + ttl_seconds, dict(value))

    def delete(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)
