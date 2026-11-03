# Generated code. Do not edit.

from flexfund._serde import FlexFundDate, FlexFundRequestModel


class UpdateTransactionRequest(FlexFundRequestModel):
    status: str | None = None
    funding_status: str | None = None
    title_confirmed: bool | None = None

    amount: float | None = None
    """BASE amount, excluding the Client Paid Fee — the server folds the fee in server-side"""

    order_full_address: str | None = None
    client_name: str | None = None
    client_email: str | None = None
    client_phone: str | None = None

    client_full_address: str | None = None
    """the client's own address. Rendered on the agreement as %clientaddress%. Normally derived at sign
    time from the client's card billing address (see StoreTransactionRequest's client_full_address),
    but editable here too.
    """

    order_number: int | None = None
    order_date: FlexFundDate | None = None

    agent_name: str | None = None
    """the buyer's agent; editable any time, including after signing, and can be cleared with null"""

    agent_email: str | None = None
    agent_phone: str | None = None

    inspector_name: str | None = None
    """the inspector, as typed; editable on FlexFund-created orders only, and can be cleared with null"""

    inspector_email: str | None = None
