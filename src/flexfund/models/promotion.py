# Generated code. Do not edit.

from pydantic import Field

from flexfund._serde import FlexFundResponseModel


class Promotion(FlexFundResponseModel):
    """One active promotion on an account."""

    id: int
    name: str
    start_date: str
    end_date: str | None

    num_inspections: int | None
    """for a count-type promotion, how many inspections it covers"""

    promotional_fee: int

    type_: str = Field(alias="type")
    """date (runs between start_date and end_date) or count (covers num_inspections inspections)"""
