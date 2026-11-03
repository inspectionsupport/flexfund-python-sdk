# Generated code. Do not edit.

from json import loads

import httpx
import respx

from flexfund._http.transport import AsyncTransport, SyncTransport
from flexfund.models.show_agreement_url_response import ShowAgreementUrlResponse
from flexfund.models.store_transaction_request import StoreTransactionRequest
from flexfund.models.transaction import Transaction
from flexfund.models.transaction_create_response import TransactionCreateResponse
from flexfund.models.transaction_index_request import TransactionIndexRequest
from flexfund.models.transaction_index_response import TransactionIndexResponse
from flexfund.models.transaction_update_response import TransactionUpdateResponse
from flexfund.models.update_transaction_request import UpdateTransactionRequest
from flexfund.resources.transaction import AsyncTransactionResource, TransactionResource

BASE_URL = "https://flexfund.test"


def test_index(respx_mock: respx.MockRouter, sync_transport: SyncTransport) -> None:
    data = {"records": [], "count": 42}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/transaction").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = TransactionResource(sync_transport).index(payload=TransactionIndexRequest.model_validate({}))

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/transaction"
    assert isinstance(result, TransactionIndexResponse)


async def test_index_async(respx_mock: respx.MockRouter, async_transport: AsyncTransport) -> None:
    data = {"records": [], "count": 42}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/transaction").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = await AsyncTransactionResource(async_transport).index(payload=TransactionIndexRequest.model_validate({}))

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/transaction"
    assert isinstance(result, TransactionIndexResponse)


def test_store(respx_mock: respx.MockRouter, sync_transport: SyncTransport) -> None:
    data = {"uuid": "test", "agreement_sign_url": "test", "agreement_email": "sent"}
    route = respx_mock.route(method="POST", url=BASE_URL + "/v20260322/transaction").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = TransactionResource(sync_transport).store(payload=StoreTransactionRequest.model_validate({"valid": True, "account_key": "test", "amount": 1.5, "order_full_address": "test", "client_name": "test", "client_email": "test@example.com", "client_phone": "test"}))

    request = route.calls.last.request
    assert request.method == "POST"
    assert request.url.path == "/v20260322/transaction"
    assert {"valid", "account_key", "amount", "order_full_address", "client_name", "client_email", "client_phone"} <= set(loads(request.content))
    assert isinstance(result, TransactionCreateResponse)


async def test_store_async(respx_mock: respx.MockRouter, async_transport: AsyncTransport) -> None:
    data = {"uuid": "test", "agreement_sign_url": "test", "agreement_email": "sent"}
    route = respx_mock.route(method="POST", url=BASE_URL + "/v20260322/transaction").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = await AsyncTransactionResource(async_transport).store(payload=StoreTransactionRequest.model_validate({"valid": True, "account_key": "test", "amount": 1.5, "order_full_address": "test", "client_name": "test", "client_email": "test@example.com", "client_phone": "test"}))

    request = route.calls.last.request
    assert request.method == "POST"
    assert request.url.path == "/v20260322/transaction"
    assert {"valid", "account_key", "amount", "order_full_address", "client_name", "client_email", "client_phone"} <= set(loads(request.content))
    assert isinstance(result, TransactionCreateResponse)


def test_show(respx_mock: respx.MockRouter, sync_transport: SyncTransport) -> None:
    data = {}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/transaction/42").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = TransactionResource(sync_transport).show(id=42)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/transaction/42"
    assert isinstance(result, Transaction)


async def test_show_async(respx_mock: respx.MockRouter, async_transport: AsyncTransport) -> None:
    data = {}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/transaction/42").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = await AsyncTransactionResource(async_transport).show(id=42)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/transaction/42"
    assert isinstance(result, Transaction)


def test_update(respx_mock: respx.MockRouter, sync_transport: SyncTransport) -> None:
    data = {"uuid": "test", "agreement_sign_url": "test"}
    route = respx_mock.route(method="PUT", url=BASE_URL + "/v20260322/transaction/42").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = TransactionResource(sync_transport).update(id=42, payload=UpdateTransactionRequest.model_validate({}))

    request = route.calls.last.request
    assert request.method == "PUT"
    assert request.url.path == "/v20260322/transaction/42"
    assert isinstance(result, TransactionUpdateResponse)


async def test_update_async(respx_mock: respx.MockRouter, async_transport: AsyncTransport) -> None:
    data = {"uuid": "test", "agreement_sign_url": "test"}
    route = respx_mock.route(method="PUT", url=BASE_URL + "/v20260322/transaction/42").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = await AsyncTransactionResource(async_transport).update(id=42, payload=UpdateTransactionRequest.model_validate({}))

    request = route.calls.last.request
    assert request.method == "PUT"
    assert request.url.path == "/v20260322/transaction/42"
    assert isinstance(result, TransactionUpdateResponse)


def test_agreement_url(respx_mock: respx.MockRouter, sync_transport: SyncTransport) -> None:
    data = {"agreement_sign_url": "test", "signed": True}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/transaction/42/agreement-url").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = TransactionResource(sync_transport).agreement_url(id=42)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/transaction/42/agreement-url"
    assert isinstance(result, ShowAgreementUrlResponse)


async def test_agreement_url_async(respx_mock: respx.MockRouter, async_transport: AsyncTransport) -> None:
    data = {"agreement_sign_url": "test", "signed": True}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/transaction/42/agreement-url").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = await AsyncTransactionResource(async_transport).agreement_url(id=42)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/transaction/42/agreement-url"
    assert isinstance(result, ShowAgreementUrlResponse)
