# Generated code. Do not edit.

from flexfund._serde import FlexFundResponseModel


class ApiClient(FlexFundResponseModel):
    """An account's API client (OAuth client credentials identity), without its secret."""

    id: str
    name: str
    revoked: bool
    created_at: str | None
    scopes: list[str] | None
