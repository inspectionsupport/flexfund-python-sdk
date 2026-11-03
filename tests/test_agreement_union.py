"""``transaction_agreement.show()``: a pending or a signed agreement, told apart by ``status``."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from conftest import BASE_URL, envelope
from flexfund import AsyncFlexFundClient, FlexFundClient, ResponseError
from flexfund.models.transaction_agreement_pending import TransactionAgreementPending
from flexfund.models.transaction_agreement_signed import TransactionAgreementSigned

PENDING: dict[str, Any] = {
    "status": "pending",
    "url": None,
    "html": "<p>agreement</p>",
    "has_signing_link": True,
    "card_tokenizer_url": "https://tokenizer.example.test/",
    "client": {"name": "A Client", "email": "client@example.com", "phone": None},
    "total_fee": "$734.99",
    "inspection_date": "2026-10-01",
}
SIGNED: dict[str, Any] = {
    "status": "signed",
    "signer_name": "A Client",
    "signed_at": "2026-10-02T14:30:00+00:00",
    "url": "https://pdf.example.test/signed.pdf",
    "html": None,
}
URL = f"{BASE_URL}/v20260322/transaction-agreement/order-uuid"


def mint_token(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{BASE_URL}/oauth/token").mock(
        return_value=httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
    )


def serve(respx_mock: respx.MockRouter, data: Any) -> None:
    mint_token(respx_mock)
    respx_mock.get(URL).mock(return_value=httpx.Response(200, json=envelope(data)))


def show(respx_mock: respx.MockRouter, data: Any) -> Any:
    serve(respx_mock, data)
    with FlexFundClient(client_id="id", client_secret="secret", base_url=BASE_URL) as client:
        return client.transaction_agreement.show("order-uuid")


def test_a_pending_payload_is_a_pending_agreement(respx_mock: respx.MockRouter) -> None:
    result = show(respx_mock, PENDING)
    assert isinstance(result, TransactionAgreementPending)
    assert result.has_signing_link is True
    assert result.client.name == "A Client"


def test_a_signed_payload_is_a_signed_agreement(respx_mock: respx.MockRouter) -> None:
    result = show(respx_mock, SIGNED)
    assert isinstance(result, TransactionAgreementSigned)
    assert result.signer_name == "A Client"
    assert result.signed_at is not None and result.signed_at.year == 2026


@pytest.mark.parametrize(
    "data",
    [
        {**PENDING, "status": "voided"},  # a status this SDK does not know
        {k: v for k, v in PENDING.items() if k != "status"},  # no discriminator at all
        {**SIGNED, "signer_name": None},  # right tag, wrong shape
        {**PENDING, "has_signing_link": "maybe"},
        [],
        None,
    ],
)
def test_anything_else_is_a_response_error(respx_mock: respx.MockRouter, data: Any) -> None:
    with pytest.raises(ResponseError) as exc:
        show(respx_mock, data)
    assert "TransactionAgreementPending | TransactionAgreementSigned" in exc.value.message


def test_the_error_names_the_problem_but_not_the_values(respx_mock: respx.MockRouter) -> None:
    with pytest.raises(ResponseError) as exc:
        show(respx_mock, {**SIGNED, "signer_name": None, "url": "https://leak.example.test/SECRET"})
    assert "SECRET" not in exc.value.message


@pytest.mark.parametrize(
    ("data", "expected"),
    [(PENDING, TransactionAgreementPending), (SIGNED, TransactionAgreementSigned)],
)
async def test_async_client_follows_the_same_rule(
    respx_mock: respx.MockRouter, data: dict[str, Any], expected: type
) -> None:
    serve(respx_mock, data)
    async with AsyncFlexFundClient(
        client_id="id", client_secret="secret", base_url=BASE_URL
    ) as client:
        assert type(await client.transaction_agreement.show("order-uuid")) is expected
