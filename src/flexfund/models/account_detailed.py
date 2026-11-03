# Generated code. Do not edit.

from typing import Annotated

from flexfund._serde import FlexFundResponseModel, lenient
from flexfund.enums.enabled import Enabled


class AccountDetailed(FlexFundResponseModel):
    id: int
    name: str
    business_name: str | None
    product_id: int
    product: str
    enabled: Annotated[Enabled | str, lenient(Enabled)]
    enabled_date: str | None
    disabled_date: str | None
    canceled: Annotated[Enabled | str, lenient(Enabled)]
    test: Annotated[Enabled | str, lenient(Enabled)]
    checking_account_enabled: Annotated[Enabled | str, lenient(Enabled)]
    w9_enabled: Annotated[Enabled | str, lenient(Enabled)]
    services_opt_in: str | None
    inspection_types_opt_in: str | None
    funding_status: str | None
    client_paid_fee: str | None
    client_paid_fee_amount: str | None
