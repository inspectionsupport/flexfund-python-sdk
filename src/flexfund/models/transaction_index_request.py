# Generated code. Do not edit.

from typing import Any

from pydantic import Field

from flexfund._serde import FlexFundDate, FlexFundRequestModel


class TransactionIndexRequest(FlexFundRequestModel):
    """Rules are deliberately permissive — this endpoint has never rejected a parameter, and turning a
    silently-ignored value into a 422 would be a regression, not a fix.
    """

    start: int | None = None
    offset: int | None = None
    tab: str | None = None
    date_start: FlexFundDate | None = None
    date_end: FlexFundDate | None = None
    filter_account_id: int | None = None
    download: Any = None

    sort_order: list[dict[str, Any]] | None = Field(default=None, alias="sortOrder")
    """JSON-encoded string in the query string, decoded before validation"""

    filter: dict[str, Any] | None = None
    """JSON-encoded string in the query string, decoded before validation. Set account_key to restrict
    the list to one account.
    """

    search: list[dict[str, Any]] | None = None
    """JSON-encoded string in the query string, decoded before validation"""
