# Generated code. Do not edit.

from flexfund._serde import FlexFundDate, FlexFundRequestModel


class StoreTransactionRequest(FlexFundRequestModel):
    valid: bool
    """false is rejected with a 403 before any account lookup"""

    account_key: str
    """must match an existing account.name"""

    product: str | None = None
    amount: float
    order_full_address: str
    client_name: str
    client_email: str
    client_phone: str

    client_full_address: str | None = None
    """the client's own address. Rendered on the agreement as %clientaddress%. Optional here — the
    signing flow derives it from the client's card billing address and writes it onto the order at
    sign time.
    """

    order_number: int | None = None
    order_date: FlexFundDate | None = None
    office_uuid: str | None = None

    agent_name: str | None = None
    """the buyer's agent; optional, and can be added later"""

    agent_email: str | None = None
    agent_phone: str | None = None

    inspector_name: str | None = None
    """the inspector, as typed; optional"""

    inspector_email: str | None = None
