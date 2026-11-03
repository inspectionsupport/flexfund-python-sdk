# Generated code. Do not edit.

from typing import Any
from urllib.parse import quote

from flexfund._http.transport import AsyncTransport, SyncTransport
from flexfund._serde import body_as_query, body_to_json, decode
from flexfund.models.show_agreement_url_response import ShowAgreementUrlResponse
from flexfund.models.store_transaction_request import StoreTransactionRequest
from flexfund.models.transaction import Transaction
from flexfund.models.transaction_create_response import TransactionCreateResponse
from flexfund.models.transaction_index_request import TransactionIndexRequest
from flexfund.models.transaction_index_response import TransactionIndexResponse
from flexfund.models.transaction_update_response import TransactionUpdateResponse
from flexfund.models.update_transaction_request import UpdateTransactionRequest


class TransactionResource:
    """SDK access to the `transaction` endpoint (v20260322). Use `client.transaction`; don't construct directly."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def index(
        self,
        payload: TransactionIndexRequest | None = None,
    ) -> TransactionIndexResponse:
        """Lists transactions your credentials can access, with optional filtering, sorting, and pagination.
        The filter/search/sortOrder query parameters are JSON-encoded strings, not nested objects.

        Scopes: `transaction:read`

        Args:
            payload: The request body.

        Example request body:
            ```json
            {
                "start": 0,
                "offset": 25,
                "tab": "open",
                "sortOrder": "[{\\"name\\":\\"created_date\\",\\"direction\\":\\"desc\\"}]",
                "filter": "{\\"filter_process_status\\":[\\"funded\\"]}",
                "search": "[{\\"term\\":\\"address\\",\\"value\\":\\"123 Main St\\"}]"
            }
            ```
        """
        query: dict[str, Any] = body_as_query(payload, json_encoded_keys=("sortOrder", "filter", "search"))
        data = self._transport.request("GET", "v20260322/transaction", query=query)
        return decode(TransactionIndexResponse, data)

    def store(
        self,
        payload: StoreTransactionRequest,
    ) -> TransactionCreateResponse:
        """Creates a new transaction under the account identified by account_key. Returns 201 on success.

        Scopes: `transaction:write`

        Args:
            payload: The request body.

        Raises:
            ValidationError: Includes a disabled account or a disabled order office.
        """
        data = self._transport.request("POST", "v20260322/transaction", json=body_to_json(payload))
        return decode(TransactionCreateResponse, data)

    def show(
        self,
        id: int | str,
    ) -> Transaction:
        """Returns one transaction, if your credentials are authorized to view it.

        Scopes: `transaction:read`

        Args:
            id: The resource id.

        Raises:
            NotFoundError: Unknown uuid, or a uuid outside the caller's account.
        """
        data = self._transport.request("GET", f"v20260322/transaction/{quote(str(id), safe='')}")
        return decode(Transaction, data)

    def update(
        self,
        id: int | str,
        payload: UpdateTransactionRequest | None = None,
    ) -> TransactionUpdateResponse:
        """Updates an existing transaction, if your credentials are authorized to change it.

        Scopes: `transaction:write`

        Args:
            id: The resource id.
            payload: The request body.

        Raises:
            NotFoundError: Unknown uuid, or a uuid outside the caller's account.
        """
        data = self._transport.request("PUT", f"v20260322/transaction/{quote(str(id), safe='')}", json=body_to_json(payload))
        return decode(TransactionUpdateResponse, data)

    def agreement_url(
        self,
        id: int | str,
    ) -> ShowAgreementUrlResponse:
        """Returns the current public signing link for a FlexFund-created order's agreement, without changing
        it.

        Scopes: `transaction:read`

        Args:
            id: The resource id.

        Raises:
            NotFoundError: Unknown uuid, or a uuid outside the caller's account.
            ValidationError: The order was not created in FlexFund, so it has no signing link here.
        """
        data = self._transport.request("GET", f"v20260322/transaction/{quote(str(id), safe='')}/agreement-url")
        return decode(ShowAgreementUrlResponse, data)


class AsyncTransactionResource:
    """Async SDK access to the `transaction` endpoint (v20260322). Use `client.transaction`; don't construct directly."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def index(
        self,
        payload: TransactionIndexRequest | None = None,
    ) -> TransactionIndexResponse:
        """Lists transactions your credentials can access, with optional filtering, sorting, and pagination.
        The filter/search/sortOrder query parameters are JSON-encoded strings, not nested objects.

        Scopes: `transaction:read`

        Args:
            payload: The request body.

        Example request body:
            ```json
            {
                "start": 0,
                "offset": 25,
                "tab": "open",
                "sortOrder": "[{\\"name\\":\\"created_date\\",\\"direction\\":\\"desc\\"}]",
                "filter": "{\\"filter_process_status\\":[\\"funded\\"]}",
                "search": "[{\\"term\\":\\"address\\",\\"value\\":\\"123 Main St\\"}]"
            }
            ```
        """
        query: dict[str, Any] = body_as_query(payload, json_encoded_keys=("sortOrder", "filter", "search"))
        data = await self._transport.request("GET", "v20260322/transaction", query=query)
        return decode(TransactionIndexResponse, data)

    async def store(
        self,
        payload: StoreTransactionRequest,
    ) -> TransactionCreateResponse:
        """Creates a new transaction under the account identified by account_key. Returns 201 on success.

        Scopes: `transaction:write`

        Args:
            payload: The request body.

        Raises:
            ValidationError: Includes a disabled account or a disabled order office.
        """
        data = await self._transport.request("POST", "v20260322/transaction", json=body_to_json(payload))
        return decode(TransactionCreateResponse, data)

    async def show(
        self,
        id: int | str,
    ) -> Transaction:
        """Returns one transaction, if your credentials are authorized to view it.

        Scopes: `transaction:read`

        Args:
            id: The resource id.

        Raises:
            NotFoundError: Unknown uuid, or a uuid outside the caller's account.
        """
        data = await self._transport.request("GET", f"v20260322/transaction/{quote(str(id), safe='')}")
        return decode(Transaction, data)

    async def update(
        self,
        id: int | str,
        payload: UpdateTransactionRequest | None = None,
    ) -> TransactionUpdateResponse:
        """Updates an existing transaction, if your credentials are authorized to change it.

        Scopes: `transaction:write`

        Args:
            id: The resource id.
            payload: The request body.

        Raises:
            NotFoundError: Unknown uuid, or a uuid outside the caller's account.
        """
        data = await self._transport.request("PUT", f"v20260322/transaction/{quote(str(id), safe='')}", json=body_to_json(payload))
        return decode(TransactionUpdateResponse, data)

    async def agreement_url(
        self,
        id: int | str,
    ) -> ShowAgreementUrlResponse:
        """Returns the current public signing link for a FlexFund-created order's agreement, without changing
        it.

        Scopes: `transaction:read`

        Args:
            id: The resource id.

        Raises:
            NotFoundError: Unknown uuid, or a uuid outside the caller's account.
            ValidationError: The order was not created in FlexFund, so it has no signing link here.
        """
        data = await self._transport.request("GET", f"v20260322/transaction/{quote(str(id), safe='')}/agreement-url")
        return decode(ShowAgreementUrlResponse, data)
