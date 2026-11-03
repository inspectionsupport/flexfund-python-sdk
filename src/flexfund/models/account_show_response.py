# Generated code. Do not edit.

from flexfund._serde import FlexFundResponseModel
from flexfund.models.account_bundle import AccountBundle
from flexfund.models.flex_fund_status import FlexFundStatus
from flexfund.models.office import Office
from flexfund.models.promotion import Promotion


class AccountShowResponse(FlexFundResponseModel):
    account: AccountBundle

    promotions: list[Promotion] | None
    """The account's active promotions, or null when none are available."""

    flexfund: FlexFundStatus
    """Whether FlexFund is enabled for the account."""

    offices: list[Office]
    """The account's offices. Empty when the account has none."""

    timezone_hint: str | None = None
    """Best-effort IANA timezone suggestion for the account's timezone field, derived from its primary
    office. A prefill convenience only, never authoritative. Null when no suggestion is available.
    """
