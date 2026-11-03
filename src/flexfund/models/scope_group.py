# Generated code. Do not edit.

from flexfund._serde import FlexFundResponseModel


class ScopeGroup(FlexFundResponseModel):
    """One resource's read and write scopes."""

    resource: str
    read: str | None
    write: str | None
    description: str | None
