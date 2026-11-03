"""Pydantic base classes, wire-format types and body helpers shared by generated code."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import UTC, date, datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainSerializer,
    RootModel,
    TypeAdapter,
)
from pydantic import ValidationError as PydanticValidationError

from flexfund.errors import ResponseError

_log = logging.getLogger("flexfund")

_DATE_FORMAT = "%Y-%m-%d"
_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


_SENSITIVE_FIELDS = frozenset(
    {"password", "secret", "card_token", "account_number", "routing_number"}
)
"""Field names whose values are masked in ``repr`` so they cannot leak into logs or tracebacks."""


class _RedactingModel(BaseModel):
    def __repr_args__(self) -> Iterator[tuple[str | None, Any]]:
        for name, value in super().__repr_args__():
            if name in _SENSITIVE_FIELDS and value is not None:
                yield name, "***"
            else:
                yield name, value


class FlexFundRequestModel(_RedactingModel):
    """Base for request models: unknown fields and unknown enum values are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class FlexFundResponseModel(_RedactingModel):
    """Base for response models: unknown fields are ignored, so new API fields are harmless."""

    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)


class FlexFundBag(RootModel[dict[str, Any]]):
    """A schema that is just a free-form object (``additionalProperties: true``).

    Wraps the raw dict and offers read-only mapping-style access.
    """

    model_config = ConfigDict(frozen=True)

    def get(self, key: str, default: Any = None) -> Any:
        return self.root.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.root[key]

    def __contains__(self, key: object) -> bool:
        return key in self.root


# -- dates --------------------------------------------------------------------------------


def _parse_date(value: Any) -> Any:
    if isinstance(value, str):
        return datetime.strptime(value, _DATE_FORMAT).date()
    return value


def _format_date(value: date) -> str:
    return value.strftime(_DATE_FORMAT)


def _parse_datetime(value: Any) -> Any:
    """Parse ``"Y-m-d H:i:s"`` (UTC, FlexFund's app timezone); naive datetimes are assumed UTC."""
    if isinstance(value, str):
        return datetime.strptime(value, _DATETIME_FORMAT).replace(tzinfo=UTC)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return value


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime(_DATETIME_FORMAT)


FlexFundDate = Annotated[
    date,
    BeforeValidator(_parse_date),
    PlainSerializer(_format_date, return_type=str, when_used="json"),
]
"""A calendar date; wire format ``YYYY-MM-DD``."""

FlexFundDateTime = Annotated[
    datetime,
    BeforeValidator(_parse_datetime),
    PlainSerializer(_format_datetime, return_type=str, when_used="json"),
]
"""A UTC-aware datetime; wire format ``YYYY-MM-DD HH:MM:SS`` (UTC)."""

FlexFundIso8601 = Annotated[
    datetime,
    PlainSerializer(lambda value: value.isoformat(), return_type=str, when_used="json"),
]
"""A datetime whose wire format is ISO 8601."""


# -- lenient enums ------------------------------------------------------------------------


def lenient[E: Enum](enum_cls: type[E]) -> BeforeValidator:
    """Validator for response enum fields, annotated ``Annotated[Role | str, lenient(Role)]``.

    A value the SDK doesn't know yet (the API added a member) is kept as the raw ``str``
    and a warning is logged, instead of failing the whole response. ``None`` and non-string
    values pass through unchanged (nullable fields annotate ``Role | str | None``).
    """

    def _validate(value: Any) -> Any:
        # Only strings are coerced; None (nullable fields) and anything else pass through
        # untouched so the surrounding union validation decides.
        if not isinstance(value, str):
            return value
        try:
            return enum_cls(value)
        except ValueError:
            _log.warning(
                "Unknown %s value %r from FlexFund; SDK may be out of date",
                enum_cls.__name__,
                value,
            )
            return value

    return BeforeValidator(_validate)


# -- request bodies -----------------------------------------------------------------------


def _dump_without_top_level_nulls(payload: BaseModel | None) -> dict[str, Any]:
    if payload is None:
        return {}
    dumped = payload.model_dump(mode="json", by_alias=True)
    return {key: value for key, value in dumped.items() if value is not None}


def body_to_json(payload: BaseModel | None) -> dict[str, Any]:
    """Dump a request model to a JSON-ready dict, dropping TOP-LEVEL ``None`` values the
    caller did not set.

    Why unset nulls are stripped: a model is a fixed shape, so a field the caller never set
    would otherwise be sent as an explicit ``null``. That is not the same statement, and
    FlexFund's validators are right to reject it: an optional boolean field 422s on a
    present null. Widening those rules to accept null would have been WORSE than the 422: an
    update applies whatever it is given, so an invented null would clear a value that was
    already set. Stripping keeps "not supplied" meaning not supplied.

    A field the caller set to ``None`` explicitly (``UpdateTransactionRequest(agent_name=None)``)
    IS sent as ``null``: that is how an update clears a nullable field such as the buyer's
    agent. ``model_fields_set`` tells the two apart; a non-nullable field set to ``None`` gets
    the server's 422, which is the right answer to that request.

    Only the top level is stripped, not nested values (so this is deliberately not
    ``exclude_none=True``, which recurses).
    """
    if payload is None:
        return {}
    fields = type(payload).model_fields
    explicit = {fields[name].alias or name for name in payload.model_fields_set}
    dumped = payload.model_dump(mode="json", by_alias=True)
    return {key: value for key, value in dumped.items() if value is not None or key in explicit}


def body_as_query(
    payload: BaseModel | None, json_encoded_keys: tuple[str, ...] = ()
) -> dict[str, Any]:
    """Like :func:`body_to_json`, for GET endpoints whose "body" travels as query parameters.

    Keys listed in ``json_encoded_keys`` (wire names) are JSON-encoded into a single string
    value (compact separators); FlexFund decodes them server-side.
    """
    query = _dump_without_top_level_nulls(payload)
    for key in json_encoded_keys:
        if key in query:
            query[key] = json.dumps(query[key], separators=(",", ":"))
    return query


# -- response decoding --------------------------------------------------------------------

_MAX_REPORTED_PROBLEMS = 3


def _problems(exc: PydanticValidationError) -> str:
    """A short, value-free summary of what did not validate.

    Only field locations and pydantic's messages are reported, never the offending input, so
    a malformed response cannot copy sensitive values into an exception message or a log line.
    """
    found = exc.errors(include_url=False, include_input=False, include_context=False)
    shown = [
        f"{'.'.join(str(part) for part in err['loc']) or '<root>'}: {err['msg']}"
        for err in found[:_MAX_REPORTED_PROBLEMS]
    ]
    more = len(found) - len(shown)
    return "; ".join(shown) + (f"; and {more} more" if more > 0 else "")


def decode[M: BaseModel](model: type[M], data: Any, *, where: str = "") -> M:
    """Build ``model`` from a response's ``data``, raising :class:`~flexfund.errors.ResponseError`.

    Generated resource methods call this instead of ``model_validate`` so that a malformed
    successful response stays inside the SDK's own error hierarchy.
    """
    try:
        return model.model_validate(data)
    except PydanticValidationError as exc:
        raise ResponseError(
            f"FlexFund returned a {model.__name__} response{where} that does not match the "
            f"expected schema ({_problems(exc)}).",
            body=data if isinstance(data, dict) else None,
        ) from exc


def decode_list[M: BaseModel](model: type[M], data: Any) -> list[M]:
    """:func:`decode` for each item of a list response; a non-list is a ``ResponseError``."""
    if not isinstance(data, list):
        raise ResponseError(
            f"FlexFund returned a {type(data).__name__} where a list of {model.__name__} "
            "was expected.",
            body=data if isinstance(data, dict) else None,
        )
    return [decode(model, item, where=f" (item {index})") for index, item in enumerate(data)]


def decode_union(adapter: TypeAdapter[Any], data: Any, what: str) -> Any:
    """Decode a response that is one of several models, told apart by a discriminator.

    ``adapter`` is a module-level ``TypeAdapter`` over
    ``Annotated[A | B, Field(discriminator=...)]``, built by the generated resource. A payload
    that matches no member, including one whose discriminator holds a value the SDK does not
    know, is a :class:`~flexfund.errors.ResponseError`.
    """
    try:
        return adapter.validate_python(data)
    except PydanticValidationError as exc:
        raise ResponseError(
            f"FlexFund returned a response that is none of {what} ({_problems(exc)}).",
            body=data if isinstance(data, dict) else None,
        ) from exc
