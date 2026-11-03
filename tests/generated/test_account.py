# Generated code. Do not edit.

from urllib.parse import parse_qs

import httpx
import respx

from flexfund._http.transport import AsyncTransport, SyncTransport
from flexfund.models.account_detailed import AccountDetailed
from flexfund.models.account_o_auth_client import AccountOAuthClient
from flexfund.models.account_show_response import AccountShowResponse
from flexfund.resources.account import AccountResource, AsyncAccountResource

BASE_URL = "https://flexfund.test"


def _query_keys(request: httpx.Request) -> set[str]:
    """Query keys with PHP-style `key[0]` / `key[sub]` suffixes folded back to `key`."""
    return {key.split("[", 1)[0] for key in parse_qs(request.url.query.decode())}


def test_index(respx_mock: respx.MockRouter, sync_transport: SyncTransport) -> None:
    data = [{"id": 42, "name": "test", "business_name": "test", "product_id": 42, "product": "test", "enabled": "yes", "enabled_date": "test", "disabled_date": "test", "canceled": "yes", "test": "yes", "checking_account_enabled": "yes", "w9_enabled": "yes", "services_opt_in": "test", "inspection_types_opt_in": "test", "funding_status": "test", "client_paid_fee": "test", "client_paid_fee_amount": "test"}]
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/account").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = AccountResource(sync_transport).index(detailed=True)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/account"
    assert {"detailed"} <= _query_keys(request)
    assert len(result) == 1
    assert isinstance(result[0], AccountDetailed)


async def test_index_async(respx_mock: respx.MockRouter, async_transport: AsyncTransport) -> None:
    data = [{"id": 42, "name": "test", "business_name": "test", "product_id": 42, "product": "test", "enabled": "yes", "enabled_date": "test", "disabled_date": "test", "canceled": "yes", "test": "yes", "checking_account_enabled": "yes", "w9_enabled": "yes", "services_opt_in": "test", "inspection_types_opt_in": "test", "funding_status": "test", "client_paid_fee": "test", "client_paid_fee_amount": "test"}]
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/account").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = await AsyncAccountResource(async_transport).index(detailed=True)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/account"
    assert {"detailed"} <= _query_keys(request)
    assert len(result) == 1
    assert isinstance(result[0], AccountDetailed)


def test_show(respx_mock: respx.MockRouter, sync_transport: SyncTransport) -> None:
    data = {"account": {"id": 42, "name": "test", "product_id": 42, "enabled": "yes", "enabled_date": "test", "disabled_date": "test", "checking_account_enabled": "yes", "w9_enabled": "yes", "services_opt_in": "test", "inspection_types_opt_in": "test", "funding_status": "test", "created_at": "test", "updated_at": "test", "canceled": "yes", "test": "yes", "client_paid_fee": "test", "client_paid_fee_amount": "test", "client_paid_fee_enabled_date": "test", "client_paid_fee_disabled_date": "test", "full_name": "test", "business_name": "test", "timezone": "test"}, "promotions": [], "flexfund": {"enabled": True}, "offices": []}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/account/42").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = AccountResource(sync_transport).show(id=42)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/account/42"
    assert isinstance(result, AccountShowResponse)


async def test_show_async(respx_mock: respx.MockRouter, async_transport: AsyncTransport) -> None:
    data = {"account": {"id": 42, "name": "test", "product_id": 42, "enabled": "yes", "enabled_date": "test", "disabled_date": "test", "checking_account_enabled": "yes", "w9_enabled": "yes", "services_opt_in": "test", "inspection_types_opt_in": "test", "funding_status": "test", "created_at": "test", "updated_at": "test", "canceled": "yes", "test": "yes", "client_paid_fee": "test", "client_paid_fee_amount": "test", "client_paid_fee_enabled_date": "test", "client_paid_fee_disabled_date": "test", "full_name": "test", "business_name": "test", "timezone": "test"}, "promotions": [], "flexfund": {"enabled": True}, "offices": []}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/account/42").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = await AsyncAccountResource(async_transport).show(id=42)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/account/42"
    assert isinstance(result, AccountShowResponse)


def test_oauth_client(respx_mock: respx.MockRouter, sync_transport: SyncTransport) -> None:
    data = {"token_url": "test", "grant_type": "test", "default_scopes": [], "available_scopes": [], "client": {"id": "test", "name": "test", "revoked": True, "created_at": "test", "scopes": []}}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/account/42/oauth-client").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = AccountResource(sync_transport).oauth_client(id=42)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/account/42/oauth-client"
    assert isinstance(result, AccountOAuthClient)


async def test_oauth_client_async(respx_mock: respx.MockRouter, async_transport: AsyncTransport) -> None:
    data = {"token_url": "test", "grant_type": "test", "default_scopes": [], "available_scopes": [], "client": {"id": "test", "name": "test", "revoked": True, "created_at": "test", "scopes": []}}
    route = respx_mock.route(method="GET", url=BASE_URL + "/v20260322/account/42/oauth-client").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": data}),
    )

    result = await AsyncAccountResource(async_transport).oauth_client(id=42)

    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/v20260322/account/42/oauth-client"
    assert isinstance(result, AccountOAuthClient)
