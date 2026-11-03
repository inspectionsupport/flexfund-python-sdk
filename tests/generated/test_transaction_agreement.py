# Generated code. Do not edit.

import httpx
import respx

from flexfund._http.transport import AsyncTransport, SyncTransport
from flexfund.models.transaction_agreement_pending import TransactionAgreementPending
from flexfund.resources.transaction_agreement import (
    AsyncTransactionAgreementResource,
    TransactionAgreementResource,
)

BASE_URL = "https://flexfund.test"


def test_show(respx_mock: respx.MockRouter, sync_transport: SyncTransport) -> None:
    data = {"status": "pending", "url": "test", "html": "test", "has_signing_link": True, "card_tokenizer_url": "test", "client": {"name": "test", "email": "test", "phone": "test"}, "total_fee": "test", "inspection_date": "test"}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/transaction-agreement/42").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = TransactionAgreementResource(sync_transport).show(id=42)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/transaction-agreement/42"
    assert isinstance(result, TransactionAgreementPending)


async def test_show_async(respx_mock: respx.MockRouter, async_transport: AsyncTransport) -> None:
    data = {"status": "pending", "url": "test", "html": "test", "has_signing_link": True, "card_tokenizer_url": "test", "client": {"name": "test", "email": "test", "phone": "test"}, "total_fee": "test", "inspection_date": "test"}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/transaction-agreement/42").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = await AsyncTransactionAgreementResource(async_transport).show(id=42)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/transaction-agreement/42"
    assert isinstance(result, TransactionAgreementPending)
