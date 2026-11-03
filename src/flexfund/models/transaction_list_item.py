# Generated code. Do not edit.

from flexfund._serde import FlexFundResponseModel


class TransactionListItem(FlexFundResponseModel):
    uuid: str | None = None
    account_id: int | None = None
    account_key: str | None = None
    order_full_address: str | None = None
    order_number: int | None = None
    client_name: str | None = None
    amount: float | None = None
    inspector_amount: float | None = None
    inspector_name: str | None = None
    funding_status: str | None = None
    order_date: str | None = None
    closing_date: str | None = None
    title_confirmed: bool | None = None
    collections_status: str | None = None
    status: str | None = None
    created_date: str | None = None
    closing_information: bool | None = None
    promotion: bool | None = None
    funding_date: str | None = None
