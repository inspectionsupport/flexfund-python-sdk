# Generated code. Do not edit.

from typing import Annotated, Any
from urllib.parse import quote

from pydantic import Field, TypeAdapter

from flexfund._http.transport import AsyncTransport, SyncTransport
from flexfund._serde import decode_union
from flexfund.models.transaction_agreement_pending import TransactionAgreementPending
from flexfund.models.transaction_agreement_signed import TransactionAgreementSigned

_SHOW_RESPONSE: TypeAdapter[Any] = TypeAdapter(
    Annotated[TransactionAgreementPending | TransactionAgreementSigned, Field(discriminator="status")]
)


class TransactionAgreementResource:
    """SDK access to the `transaction-agreement` endpoint (v20260322). Use `client.transaction_agreement`; don't construct directly."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def show(
        self,
        id: int | str,
    ) -> TransactionAgreementPending | TransactionAgreementSigned:
        """Returns the agreement for an order: an unsigned preview if it hasn't been signed yet, or a freshly
        regenerated copy (template plus the recorded signature) if it has — no rendered PDF is stored
        anywhere. Authenticated, keyed by the order's uuid (the {transaction-agreement} route parameter).

        Scopes: `transaction-agreement:read`

        Args:
            id: The resource id.

        Returns:
            One of: TransactionAgreementPending | TransactionAgreementSigned, told apart by `status`
            (`pending` is TransactionAgreementPending, `signed` is TransactionAgreementSigned).

        Raises:
            NotFoundError: Unknown order uuid.
        """
        data = self._transport.request("GET", f"v20260322/transaction-agreement/{quote(str(id), safe='')}")
        result: TransactionAgreementPending | TransactionAgreementSigned = decode_union(_SHOW_RESPONSE, data, "TransactionAgreementPending | TransactionAgreementSigned")
        return result


class AsyncTransactionAgreementResource:
    """Async SDK access to the `transaction-agreement` endpoint (v20260322). Use `client.transaction_agreement`; don't construct directly."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def show(
        self,
        id: int | str,
    ) -> TransactionAgreementPending | TransactionAgreementSigned:
        """Returns the agreement for an order: an unsigned preview if it hasn't been signed yet, or a freshly
        regenerated copy (template plus the recorded signature) if it has — no rendered PDF is stored
        anywhere. Authenticated, keyed by the order's uuid (the {transaction-agreement} route parameter).

        Scopes: `transaction-agreement:read`

        Args:
            id: The resource id.

        Returns:
            One of: TransactionAgreementPending | TransactionAgreementSigned, told apart by `status`
            (`pending` is TransactionAgreementPending, `signed` is TransactionAgreementSigned).

        Raises:
            NotFoundError: Unknown order uuid.
        """
        data = await self._transport.request("GET", f"v20260322/transaction-agreement/{quote(str(id), safe='')}")
        result: TransactionAgreementPending | TransactionAgreementSigned = decode_union(_SHOW_RESPONSE, data, "TransactionAgreementPending | TransactionAgreementSigned")
        return result
