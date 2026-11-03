# Generated code. Do not edit.

from pydantic import Field

from flexfund._serde import FlexFundResponseModel


class Office(FlexFundResponseModel):
    """One of the account's offices. Only the fields that are always present are included."""

    id: str | None = None
    """the office's uuid"""

    office_id: int | None = Field(default=None, alias="officeId")
    primary_office: bool | None = Field(default=None, alias="primaryOffice")

    timezone_name: str | None = Field(default=None, alias="timezoneName")
    """IANA timezone name"""
