# Generated code. Do not edit.

from flexfund._serde import FlexFundResponseModel
from flexfund.models.transaction_list_item import TransactionListItem


class TransactionIndexResponse(FlexFundResponseModel):
    records: list[TransactionListItem]

    count: int
    """total matching rows, independent of start/offset pagination"""
