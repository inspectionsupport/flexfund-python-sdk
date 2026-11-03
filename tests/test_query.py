from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from flexfund._http.query import encode_query


class Color(StrEnum):
    RED = "red"


def test_booleans_are_1_and_0() -> None:
    assert encode_query({"a": True, "b": False}) == [("a", "1"), ("b", "0")]


def test_none_is_skipped() -> None:
    assert encode_query({"a": None, "b": 1}) == [("b", "1")]


def test_lists_are_indexed() -> None:
    assert encode_query({"k": ["a", "b"]}) == [("k[0]", "a"), ("k[1]", "b")]


def test_nested_dicts() -> None:
    assert encode_query({"k": {"sub": 1, "deep": {"x": True}}}) == [
        ("k[sub]", "1"),
        ("k[deep][x]", "1"),
    ]


def test_list_of_dicts() -> None:
    assert encode_query({"k": [{"a": 1}]}) == [("k[0][a]", "1")]


def test_empty_containers_emit_nothing() -> None:
    assert encode_query({"a": [], "b": {}}) == []


def test_none_and_empty_input() -> None:
    assert encode_query(None) == []
    assert encode_query({}) == []


def test_scalars() -> None:
    assert encode_query({"i": 5, "f": 1.5, "s": "x y", "e": Color.RED}) == [
        ("i", "5"),
        ("f", "1.5"),
        ("s", "x y"),
        ("e", "red"),
    ]


def test_dates() -> None:
    assert encode_query(
        {"d": date(2026, 1, 2), "t": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)}
    ) == [
        ("d", "2026-01-02"),
        ("t", "2026-01-02 03:04:05"),
    ]


def test_zero_is_not_skipped() -> None:
    assert encode_query({"n": 0, "s": ""}) == [("n", "0"), ("s", "")]
