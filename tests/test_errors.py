from __future__ import annotations

import pytest

from flexfund._http.errors import map_response, network_error, retry_after_seconds
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


def test_standard_shape_uses_string_message() -> None:
    raw = '{"success": false, "message": "Nope", "code": "NOT_FOUND", "status": 404}'
    err = map_response(404, {}, raw)
    assert isinstance(err, NotFoundError)
    assert str(err) == "Nope"
    assert err.status_code == 404
    assert err.body is not None and err.body["code"] == "NOT_FOUND"
    assert err.raw_body == raw


def test_422_reshape_with_list_message() -> None:
    raw = (
        '{"success": false, "error_code": 422, "message": ["a is bad", "b is bad"],'
        ' "errors": {"a": ["a is bad"], "b": ["b is bad", "b again"]}}'
    )
    err = map_response(422, {}, raw)
    assert isinstance(err, ValidationError)
    assert err.message == "a is bad; b is bad"
    assert err.errors == {"a": ["a is bad"], "b": ["b is bad", "b again"]}


def test_422_with_string_message_and_no_errors() -> None:
    err = map_response(
        422, {}, '{"success": false, "message": "Invalid", "code": "VALIDATION_ERROR"}'
    )
    assert isinstance(err, ValidationError)
    assert err.message == "Invalid"
    assert err.errors == {}


def test_422_empty_message_list() -> None:
    err = map_response(422, {}, '{"message": []}')
    assert err.message == "Validation failed"


def test_403_with_http_error_code_maps_by_status() -> None:
    err = map_response(403, {}, '{"success": false, "message": "Forbidden", "code": "HTTP_ERROR"}')
    assert isinstance(err, AuthorizationError)


def test_401_is_authentication_error() -> None:
    assert isinstance(map_response(401, {}, '{"message": "no"}'), AuthenticationError)


def test_409_is_conflict_not_server_error() -> None:
    err = map_response(409, {}, '{"message": "Already exists"}')
    assert isinstance(err, ConflictError)
    assert not isinstance(err, ServerError)


def test_429_carries_retry_after_case_insensitively() -> None:
    err = map_response(429, {"retry-after": "12"}, '{"message": "slow down"}')
    assert isinstance(err, RateLimitError)
    assert err.retry_after == 12


def test_429_without_header() -> None:
    err = map_response(429, {}, "{}")
    assert isinstance(err, RateLimitError)
    assert err.retry_after is None


def test_non_json_body() -> None:
    err = map_response(502, {}, "<html>Bad gateway</html>")
    assert isinstance(err, ServerError)
    assert err.body is None
    assert err.raw_body == "<html>Bad gateway</html>"
    assert "non-JSON or empty" in err.message


@pytest.mark.parametrize("raw", ["", "   \n"])
def test_empty_body(raw: str) -> None:
    err = map_response(500, {}, raw)
    assert isinstance(err, ServerError)
    assert err.body is None
    assert "non-JSON or empty" in err.message


def test_json_but_not_an_object() -> None:
    err = map_response(500, {}, "[1, 2]")
    assert err.body is None


def test_unexpected_400_is_server_error() -> None:
    err = map_response(400, {}, '{"message": "bad request"}')
    assert type(err) is ServerError
    assert err.status_code == 400


def test_missing_message_falls_back_to_status() -> None:
    assert map_response(500, {}, "{}").message == "FlexFund API request failed with status 500"


def test_network_error_has_no_status() -> None:
    err = network_error("boom")
    assert isinstance(err, ServerError)
    assert err.status_code is None


def test_everything_is_a_flexfund_error() -> None:
    for status in (400, 401, 403, 404, 409, 422, 429, 500):
        assert isinstance(map_response(status, {}, "{}"), FlexFundError)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("30", 30), ("0", 0), (None, None), ("", None), ("soon", None)],
)
def test_retry_after_seconds_simple(value: str | None, expected: int | None) -> None:
    assert retry_after_seconds(value) == expected


def test_retry_after_http_date_future_and_past() -> None:
    from datetime import UTC, datetime, timedelta
    from email.utils import format_datetime

    future = format_datetime(datetime.now(UTC) + timedelta(seconds=120), usegmt=True)
    seconds = retry_after_seconds(future)
    assert seconds is not None and 110 <= seconds <= 120

    past = format_datetime(datetime.now(UTC) - timedelta(seconds=120), usegmt=True)
    assert retry_after_seconds(past) == 0
