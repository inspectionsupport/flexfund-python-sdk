"""PHP ``http_build_query``-style query encoding.

The FlexFund API's query conventions differ from httpx defaults:

* booleans must be ``1``/``0`` (``"true"``/``"false"`` are rejected);
* lists must be ``key[0]=a&key[1]=b`` (a repeated ``key=a&key=b`` keeps only the last value);
* nested mappings must be ``key[sub]=v``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

# Widened to httpx's accepted pair type (list is invariant); every value we emit is a str.
QueryPair = tuple[str, str | int | float | bool | None]


def encode_query(params: Mapping[str, Any] | None) -> list[QueryPair]:
    """Flatten ``params`` into ``(key, value)`` pairs; ``None`` values are skipped."""
    pairs: list[QueryPair] = []
    if params:
        for key, value in params.items():
            _flatten(str(key), value, pairs)
    return pairs


def _flatten(key: str, value: Any, out: list[QueryPair]) -> None:
    if value is None:
        return
    if isinstance(value, Mapping):
        for sub_key, sub_value in value.items():
            _flatten(f"{key}[{sub_key}]", sub_value, out)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for index, item in enumerate(value):
            _flatten(f"{key}[{index}]", item, out)
    else:
        out.append((key, _scalar(value)))


def _scalar(value: Any) -> str:
    if isinstance(value, Enum):
        return _scalar(value.value)
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)
