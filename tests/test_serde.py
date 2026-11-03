from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated, Any

import pytest
from pydantic import BaseModel, ValidationError

from flexfund._serde import (
    FlexFundBag,
    FlexFundDate,
    FlexFundDateTime,
    FlexFundIso8601,
    FlexFundRequestModel,
    FlexFundResponseModel,
    body_as_query,
    body_to_json,
    lenient,
)


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"


class Times(FlexFundResponseModel):
    day: FlexFundDate
    moment: FlexFundDateTime
    iso: FlexFundIso8601


class WithRole(FlexFundResponseModel):
    role: Annotated[Role | str, lenient(Role)]


class Body(FlexFundRequestModel):
    a: int | None = None
    b: str | None = None
    sort_order: dict[str, Any] | None = None
    nested: dict[str, Any] | None = None
    ok: bool | None = None


def test_date_round_trip() -> None:
    m = Times.model_validate(
        {"day": "2026-01-02", "moment": "2026-01-02 03:04:05", "iso": "2026-01-02T03:04:05+00:00"}
    )
    assert m.day == date(2026, 1, 2)
    assert m.moment == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert m.moment.tzinfo is not None
    assert m.model_dump(mode="json") == {
        "day": "2026-01-02",
        "moment": "2026-01-02 03:04:05",
        "iso": "2026-01-02T03:04:05+00:00",
    }


def test_naive_datetime_is_assumed_utc() -> None:
    m = Times.model_validate(
        {
            "day": "2026-01-02",
            "moment": datetime(2026, 1, 2, 3, 4, 5),
            "iso": "2026-01-02T00:00:00Z",
        }
    )
    assert m.moment.tzinfo == UTC
    assert m.moment.hour == 3


def test_aware_datetime_is_serialized_in_utc() -> None:
    plus_two = datetime(2026, 1, 2, 5, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    m = Times.model_validate(
        {"day": "2026-01-02", "moment": plus_two, "iso": "2026-01-02T00:00:00Z"}
    )
    assert m.model_dump(mode="json")["moment"] == "2026-01-02 03:00:00"


def test_bad_date_is_a_validation_error() -> None:
    with pytest.raises(ValidationError):
        Times.model_validate({"day": "01/02/2026", "moment": "x", "iso": "x"})


def test_python_mode_dump_keeps_native_types() -> None:
    m = Times.model_validate(
        {"day": "2026-01-02", "moment": "2026-01-02 03:04:05", "iso": "2026-01-02T00:00:00Z"}
    )
    assert isinstance(m.model_dump()["moment"], datetime)


def test_lenient_known_value_becomes_enum() -> None:
    assert WithRole.model_validate({"role": "admin"}).role is Role.ADMIN


def test_lenient_unknown_value_is_kept_and_warned(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="flexfund"):
        m = WithRole.model_validate({"role": "superuser"})
    assert m.role == "superuser"
    assert not isinstance(m.role, Role)
    assert "Unknown Role value 'superuser' from FlexFund; SDK may be out of date" in caplog.text


def test_lenient_non_string_still_fails() -> None:
    with pytest.raises(ValidationError):
        WithRole.model_validate({"role": 5})


class Nullable(FlexFundResponseModel):
    role: Annotated[Role | str | None, lenient(Role)] = None
    roles: list[Annotated[Role | str, lenient(Role)]] = []  # noqa: RUF012


def test_lenient_none_passes_through_silently(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="flexfund"):
        assert Nullable.model_validate({"role": None}).role is None
        assert Nullable.model_validate({}).role is None
    assert caplog.text == ""


def test_lenient_list_items() -> None:
    m = Nullable.model_validate({"roles": ["admin", "wizard"]})
    assert m.roles == [Role.ADMIN, "wizard"]
    assert m.roles[0] is Role.ADMIN


def test_request_model_rejects_unknown_fields_and_response_ignores_them() -> None:
    with pytest.raises(ValidationError):
        Body.model_validate({"zzz": 1})
    assert WithRole.model_validate({"role": "admin", "extra": 1}).role is Role.ADMIN


def test_models_are_frozen() -> None:
    with pytest.raises(ValidationError):
        Body(a=1).a = 2  # type: ignore[misc]


def test_body_to_json_strips_unset_top_level_nulls_only() -> None:
    body = Body(a=1, nested={"keep": None, "x": 1})
    assert body_to_json(body) == {"a": 1, "nested": {"keep": None, "x": 1}}


def test_body_to_json_sends_an_explicit_none_as_null() -> None:
    assert body_to_json(Body(a=1, b=None)) == {"a": 1, "b": None}


def test_body_to_json_sends_an_explicit_none_under_its_alias() -> None:
    class Aliased(FlexFundRequestModel):
        from pydantic import Field

        sort_order: str | None = Field(default=None, alias="sortOrder")

    assert body_to_json(Aliased(sort_order=None)) == {"sortOrder": None}
    assert body_to_json(Aliased()) == {}


def test_body_as_query_still_drops_every_null() -> None:
    assert body_as_query(Body(a=1, b=None)) == {"a": 1}


def test_body_to_json_none_payload() -> None:
    assert body_to_json(None) == {}


def test_body_to_json_uses_aliases() -> None:
    class Aliased(FlexFundRequestModel):
        from pydantic import Field

        sort_order: str | None = Field(default=None, alias="sortOrder")

    assert body_to_json(Aliased(sortOrder="x")) == {"sortOrder": "x"}
    assert body_to_json(Aliased(sort_order="x")) == {"sortOrder": "x"}


def test_body_as_query_json_encodes_listed_keys() -> None:
    body = Body(a=1, sort_order={"id": "desc"}, ok=True)
    query = body_as_query(body, json_encoded_keys=("sort_order",))
    assert query["a"] == 1
    assert query["ok"] is True
    assert query["sort_order"] == '{"id":"desc"}'
    assert json.loads(query["sort_order"]) == {"id": "desc"}


def test_body_as_query_leaves_absent_keys_out() -> None:
    assert body_as_query(Body(a=1), json_encoded_keys=("sort_order",)) == {"a": 1}
    assert body_as_query(None, ("sort_order",)) == {}


def test_bag_access() -> None:
    class Account(FlexFundBag):
        """doc"""

    a = Account.model_validate({"id": 1, "name": "x"})
    assert a["id"] == 1
    assert a.get("name") == "x"
    assert a.get("missing") is None
    assert a.get("missing", 7) == 7
    assert "id" in a
    assert "nope" not in a
    assert a.model_dump() == {"id": 1, "name": "x"}
    with pytest.raises(KeyError):
        a["nope"]


def test_bag_is_frozen() -> None:
    class Thing(FlexFundBag):
        pass

    with pytest.raises(ValidationError):
        Thing.model_validate({}).root = {}  # type: ignore[misc]


def test_models_are_basemodels() -> None:
    assert issubclass(FlexFundRequestModel, BaseModel)
