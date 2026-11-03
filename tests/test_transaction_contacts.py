"""The buyer's agent and inspector fields, as they go over the wire.

The generated tests send empty bodies; these pin what the API's update contract relies on:
a field set to ``None`` is sent as ``null`` (which clears it), and a field left out is not sent
at all (which leaves it alone).
"""

from __future__ import annotations

from json import loads

import httpx
import respx

from flexfund._http.transport import SyncTransport
from flexfund.models.store_transaction_request import StoreTransactionRequest
from flexfund.models.update_transaction_request import UpdateTransactionRequest
from flexfund.resources.transaction import TransactionResource

BASE_URL = "https://flexfund.test"
UPDATED = {"uuid": "abc", "agreement_sign_url": "https://sign.test/abc"}


def _sent_update(
    respx_mock: respx.MockRouter, sync_transport: SyncTransport, payload: UpdateTransactionRequest
) -> object:
    route = respx_mock.route(method="PUT", url=BASE_URL + "/v20260322/transaction/abc").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "ok", "data": UPDATED}),
    )
    TransactionResource(sync_transport).update(id="abc", payload=payload)
    return loads(route.calls.last.request.content)


def test_update_sends_none_as_null_to_clear_the_agent(
    respx_mock: respx.MockRouter, sync_transport: SyncTransport
) -> None:
    payload = UpdateTransactionRequest(agent_name=None, agent_email=None, agent_phone=None)

    assert _sent_update(respx_mock, sync_transport, payload) == {
        "agent_name": None,
        "agent_email": None,
        "agent_phone": None,
    }


def test_update_leaves_out_fields_that_were_not_set(
    respx_mock: respx.MockRouter, sync_transport: SyncTransport
) -> None:
    payload = UpdateTransactionRequest(
        inspector_name="Pat Inspector", inspector_email="pat@example.com"
    )

    assert _sent_update(respx_mock, sync_transport, payload) == {
        "inspector_name": "Pat Inspector",
        "inspector_email": "pat@example.com",
    }


def test_store_sends_the_agent_and_inspector(
    respx_mock: respx.MockRouter, sync_transport: SyncTransport
) -> None:
    created = {
        "uuid": "abc",
        "agreement_sign_url": "https://sign.test/abc",
        "agreement_email": "sent",
    }
    route = respx_mock.route(method="POST", url=BASE_URL + "/v20260322/transaction").mock(
        return_value=httpx.Response(201, json={"success": True, "message": "ok", "data": created}),
    )
    payload = StoreTransactionRequest(
        valid=True,
        account_key="acme",
        amount=450,
        order_full_address="1 Main St",
        client_name="Client",
        client_email="client@example.com",
        client_phone="5551234567",
        agent_name="Alex Agent",
        inspector_name="Pat Inspector",
    )

    TransactionResource(sync_transport).store(payload=payload)

    sent = loads(route.calls.last.request.content)
    assert sent["agent_name"] == "Alex Agent"
    assert sent["inspector_name"] == "Pat Inspector"
    assert "agent_email" not in sent
    assert "inspector_email" not in sent
