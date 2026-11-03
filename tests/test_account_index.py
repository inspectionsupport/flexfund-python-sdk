"""``account.index()``: the response shape follows the ``detailed`` argument, and is checked."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from conftest import BASE_URL, envelope
from flexfund import FlexFundClient, ResponseError
from flexfund.models.account_detailed import AccountDetailed
from flexfund.models.account_summary import AccountSummary

SUMMARY_ROW = {"id": 1, "name": "acme"}
DETAILED_ROW: dict[str, Any] = {
    "id": 1,
    "name": "acme",
    "business_name": "Acme Inspections",
    "product_id": 2,
    "product": "isn",
    "enabled": "yes",
    "enabled_date": None,
    "disabled_date": None,
    "canceled": "no",
    "test": "no",
    "checking_account_enabled": "yes",
    "w9_enabled": "no",
    "services_opt_in": None,
    "inspection_types_opt_in": None,
    "funding_status": None,
    "client_paid_fee": None,
    "client_paid_fee_amount": "0.00",
}


@pytest.fixture
def client(respx_mock: respx.MockRouter) -> FlexFundClient:
    respx_mock.post(f"{BASE_URL}/oauth/token").mock(
        return_value=httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
    )
    return FlexFundClient(client_id="id", client_secret="secret", base_url=BASE_URL)


def serve(respx_mock: respx.MockRouter, rows: Any) -> respx.Route:
    return respx_mock.get(f"{BASE_URL}/v20260322/account").mock(
        return_value=httpx.Response(200, json=envelope(rows))
    )


def test_detailed_true_returns_account_detailed_rows(
    respx_mock: respx.MockRouter, client: FlexFundClient
) -> None:
    route = serve(respx_mock, [DETAILED_ROW])
    rows = client.account.index(detailed=True)
    assert [type(r) for r in rows] == [AccountDetailed]
    assert rows[0].business_name == "Acme Inspections"
    assert route.calls.last.request.url.params["detailed"] == "1"


@pytest.mark.parametrize("kwargs", [{}, {"detailed": False}, {"detailed": None}])
def test_otherwise_returns_account_summary_rows(
    respx_mock: respx.MockRouter, client: FlexFundClient, kwargs: dict[str, Any]
) -> None:
    serve(respx_mock, [SUMMARY_ROW])
    rows = client.account.index(**kwargs)
    assert [type(r) for r in rows] == [AccountSummary]
    assert rows[0].name == "acme"


def test_a_summary_row_is_not_accepted_as_detailed(
    respx_mock: respx.MockRouter, client: FlexFundClient
) -> None:
    """The caller asked for detail; a lean row means the server and SDK disagree, so say so."""
    serve(respx_mock, [SUMMARY_ROW])
    with pytest.raises(ResponseError) as exc:
        client.account.index(detailed=True)
    assert "AccountDetailed" in exc.value.message


def test_a_non_list_response_is_a_response_error(
    respx_mock: respx.MockRouter, client: FlexFundClient
) -> None:
    serve(respx_mock, {"id": 1})
    with pytest.raises(ResponseError):
        client.account.index()


async def test_async_client_follows_the_same_rule(respx_mock: respx.MockRouter) -> None:
    from flexfund import AsyncFlexFundClient

    respx_mock.post(f"{BASE_URL}/oauth/token").mock(
        return_value=httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
    )
    serve(respx_mock, [DETAILED_ROW])
    async with AsyncFlexFundClient(client_id="id", client_secret="secret", base_url=BASE_URL) as c:
        rows = await c.account.index(detailed=True)
        assert [type(r) for r in rows] == [AccountDetailed]
    serve(respx_mock, [SUMMARY_ROW])
    async with AsyncFlexFundClient(client_id="id", client_secret="secret", base_url=BASE_URL) as c:
        assert [type(r) for r in await c.account.index()] == [AccountSummary]
