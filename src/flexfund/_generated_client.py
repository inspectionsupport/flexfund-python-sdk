# Generated code. Do not edit.

from functools import cached_property

from flexfund._http.transport import AsyncTransport, SyncTransport
from flexfund.resources.account import AccountResource, AsyncAccountResource
from flexfund.resources.transaction import AsyncTransactionResource, TransactionResource
from flexfund.resources.transaction_agreement import (
    AsyncTransactionAgreementResource,
    TransactionAgreementResource,
)


class _ResourceAccessors:
    _transport: SyncTransport

    @cached_property
    def transaction(self) -> TransactionResource:
        return TransactionResource(self._transport)

    @cached_property
    def account(self) -> AccountResource:
        return AccountResource(self._transport)

    @cached_property
    def transaction_agreement(self) -> TransactionAgreementResource:
        return TransactionAgreementResource(self._transport)


class _AsyncResourceAccessors:
    _transport: AsyncTransport

    @cached_property
    def transaction(self) -> AsyncTransactionResource:
        return AsyncTransactionResource(self._transport)

    @cached_property
    def account(self) -> AsyncAccountResource:
        return AsyncAccountResource(self._transport)

    @cached_property
    def transaction_agreement(self) -> AsyncTransactionAgreementResource:
        return AsyncTransactionAgreementResource(self._transport)
