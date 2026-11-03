# Generated code. Do not edit.

from flexfund._serde import FlexFundResponseModel


class AgreementClient(FlexFundResponseModel):
    """What an order already knows about its client."""

    name: str | None
    email: str | None
    phone: str | None
