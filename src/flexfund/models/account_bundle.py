# Generated code. Do not edit.

from typing import Annotated

from flexfund._serde import FlexFundResponseModel, lenient
from flexfund.enums.enabled import Enabled


class AccountBundle(FlexFundResponseModel):
    """The account's own record."""

    id: int

    name: str
    """the account's key: the value used as {account} in the account routes and as account_key when
    creating a transaction
    """

    product_id: int
    enabled: Annotated[Enabled | str, lenient(Enabled)]
    enabled_date: str | None
    disabled_date: str | None
    checking_account_enabled: Annotated[Enabled | str, lenient(Enabled)]
    w9_enabled: Annotated[Enabled | str, lenient(Enabled)]
    services_opt_in: str | None
    inspection_types_opt_in: str | None
    funding_status: str | None
    created_at: str | None
    updated_at: str | None
    canceled: Annotated[Enabled | str, lenient(Enabled)]
    test: Annotated[Enabled | str, lenient(Enabled)]
    client_paid_fee: str | None

    client_paid_fee_amount: str | None
    """a DECIMAL column, serialised as a string such as "0.00"
    """

    client_paid_fee_enabled_date: str | None
    client_paid_fee_disabled_date: str | None
    full_name: str | None
    business_name: str | None

    timezone: str | None
    """IANA timezone name"""
