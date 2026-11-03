"""Failures the server causes must stay inside FlexFundError, however the response is malformed."""

from __future__ import annotations

import httpx
import pydantic
import pytest
import respx

from conftest import BASE_URL, envelope
from flexfund import FlexFundClient, FlexFundError, ResponseError
from flexfund._serde import decode, decode_list
from flexfund.auth.credentials import ClientCredentials
from flexfund.auth.provider import AsyncTokenProvider, TokenProvider
from flexfund.auth.token import AccessToken
from flexfund.errors import AuthenticationError
from flexfund.models.store_transaction_request import StoreTransactionRequest
from flexfund.models.transaction_create_response import TransactionCreateResponse

CREDS = ClientCredentials("id", "secret", ("a:read",))
VALID_CREATE = {
    "uuid": "u-1",
    "agreement_sign_url": "https://example.test/sign",
    "agreement_email": "sent",
}


def make_client() -> FlexFundClient:
    return FlexFundClient(client_id="id", client_secret="secret", base_url=BASE_URL)


# -- response hydration -------------------------------------------------------------------


def test_decode_returns_the_model_for_a_valid_body() -> None:
    assert decode(TransactionCreateResponse, VALID_CREATE).uuid == "u-1"


def test_decode_wraps_a_schema_mismatch_in_response_error() -> None:
    with pytest.raises(ResponseError) as exc:
        decode(TransactionCreateResponse, {"uuid": 5})
    assert isinstance(exc.value, FlexFundError)
    assert isinstance(exc.value.__cause__, pydantic.ValidationError)
    assert "TransactionCreateResponse" in exc.value.message
    assert exc.value.body == {"uuid": 5}


def test_response_error_message_names_fields_but_never_echoes_values() -> None:
    with pytest.raises(ResponseError) as exc:
        decode(TransactionCreateResponse, {"uuid": "TOP-SECRET-VALUE", "agreement_sign_url": 7})
    assert "agreement_sign_url" in exc.value.message
    assert "TOP-SECRET-VALUE" not in exc.value.message
    assert "TOP-SECRET-VALUE" not in str(exc.value)


def test_decode_list_reports_the_failing_item() -> None:
    with pytest.raises(ResponseError) as exc:
        decode_list(TransactionCreateResponse, [VALID_CREATE, {"uuid": 1}])
    assert "item 1" in exc.value.message


@pytest.mark.parametrize("data", [None, {"uuid": "u-1"}, "text", 5])
def test_decode_list_rejects_a_non_list(data: object) -> None:
    with pytest.raises(ResponseError):
        decode_list(TransactionCreateResponse, data)


def test_a_malformed_successful_resource_response_is_a_flexfund_error(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.post(f"{BASE_URL}/oauth/token").mock(
        return_value=httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
    )
    respx_mock.post(f"{BASE_URL}/v20260322/transaction").mock(
        return_value=httpx.Response(201, json=envelope({"uuid": 12345}))
    )
    request = StoreTransactionRequest(
        valid=True,
        account_key="acme",
        amount=1.0,
        order_full_address="1 Main St",
        client_name="A Client",
        client_email="client@example.com",
        client_phone="555-0100",
    )
    with make_client() as client, pytest.raises(FlexFundError) as exc:
        client.transaction.store(request)
    assert isinstance(exc.value, ResponseError)
    assert not isinstance(exc.value, pydantic.ValidationError)


def test_building_a_bad_request_model_still_raises_pydantic_locally() -> None:
    """Request-side validation is deliberately NOT wrapped: it is a bug in the caller's code."""
    with pytest.raises(pydantic.ValidationError):
        StoreTransactionRequest.model_validate({"valid": "not-a-bool"})


# -- token parsing ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"access_token": "t", "expires_in": "soon"},
        {"access_token": "t", "expires_in": "NaN"},
        {"access_token": "t", "expires_in": -5},
        {"access_token": "t", "expires_in": [1]},
        {"access_token": "t", "expires_in": True},
        {"access_token": "", "expires_in": 3600},
        {"access_token": 12345, "expires_in": 3600},
        {"access_token": ["t"], "expires_in": 3600},
    ],
)
def test_a_malformed_token_response_is_an_authentication_error(
    respx_mock: respx.MockRouter, body: dict[str, object]
) -> None:
    respx_mock.post(f"{BASE_URL}/oauth/token").mock(return_value=httpx.Response(200, json=body))
    with pytest.raises(AuthenticationError) as exc:
        TokenProvider(httpx.Client(), BASE_URL, CREDS).token()
    assert "malformed token response" in exc.value.message
    assert exc.value.status_code == 200


@pytest.mark.parametrize("body", [{"access_token": "t", "expires_in": "soon"}, {"x": 1}])
async def test_a_malformed_token_response_is_an_authentication_error_async(
    respx_mock: respx.MockRouter, body: dict[str, object]
) -> None:
    respx_mock.post(f"{BASE_URL}/oauth/token").mock(return_value=httpx.Response(200, json=body))
    async with httpx.AsyncClient() as http:
        with pytest.raises(AuthenticationError):
            await AsyncTokenProvider(http, BASE_URL, CREDS).token()


def test_a_numeric_string_expires_in_is_accepted() -> None:
    token = AccessToken.from_token_response({"access_token": "t", "expires_in": "3600"})
    assert token.token == "t"
    assert not token.is_expiring_within(3000)


def test_the_malformed_token_error_never_contains_the_token() -> None:
    with pytest.raises(ValueError) as exc:
        AccessToken.from_token_response({"access_token": "SECRET-TOKEN", "expires_in": "soon"})
    assert "SECRET-TOKEN" not in str(exc.value)
