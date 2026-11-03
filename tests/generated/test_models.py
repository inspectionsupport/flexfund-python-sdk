# Generated code. Do not edit.

from typing import Any

import pytest
from pydantic import BaseModel

from flexfund.models.account_bundle import AccountBundle
from flexfund.models.account_detailed import AccountDetailed
from flexfund.models.account_o_auth_client import AccountOAuthClient
from flexfund.models.account_show_response import AccountShowResponse
from flexfund.models.account_summary import AccountSummary
from flexfund.models.agreement_client import AgreementClient
from flexfund.models.api_client import ApiClient
from flexfund.models.flex_fund_status import FlexFundStatus
from flexfund.models.office import Office
from flexfund.models.promotion import Promotion
from flexfund.models.scope_group import ScopeGroup
from flexfund.models.show_agreement_url_response import ShowAgreementUrlResponse
from flexfund.models.store_transaction_request import StoreTransactionRequest
from flexfund.models.transaction import Transaction
from flexfund.models.transaction_agreement_pending import TransactionAgreementPending
from flexfund.models.transaction_agreement_signed import TransactionAgreementSigned
from flexfund.models.transaction_create_response import TransactionCreateResponse
from flexfund.models.transaction_index_request import TransactionIndexRequest
from flexfund.models.transaction_index_response import TransactionIndexResponse
from flexfund.models.transaction_list_item import TransactionListItem
from flexfund.models.transaction_update_response import TransactionUpdateResponse
from flexfund.models.update_transaction_request import UpdateTransactionRequest

CASES: list[tuple[type[BaseModel], dict[str, Any]]] = [
    (StoreTransactionRequest, {"valid": True, "account_key": "test", "amount": 1.5, "order_full_address": "test", "client_name": "test", "client_email": "test@example.com", "client_phone": "test"}),
    (TransactionIndexRequest, {}),
    (UpdateTransactionRequest, {}),
    (AccountOAuthClient, {"token_url": "test", "grant_type": "test", "default_scopes": [], "available_scopes": [], "client": {"id": "test", "name": "test", "revoked": True, "created_at": "test", "scopes": []}}),
    (AccountSummary, {"id": 42, "name": "test"}),
    (AccountDetailed, {"id": 42, "name": "test", "business_name": "test", "product_id": 42, "product": "test", "enabled": "yes", "enabled_date": "test", "disabled_date": "test", "canceled": "yes", "test": "yes", "checking_account_enabled": "yes", "w9_enabled": "yes", "services_opt_in": "test", "inspection_types_opt_in": "test", "funding_status": "test", "client_paid_fee": "test", "client_paid_fee_amount": "test"}),
    (AccountShowResponse, {"account": {"id": 42, "name": "test", "product_id": 42, "enabled": "yes", "enabled_date": "test", "disabled_date": "test", "checking_account_enabled": "yes", "w9_enabled": "yes", "services_opt_in": "test", "inspection_types_opt_in": "test", "funding_status": "test", "created_at": "test", "updated_at": "test", "canceled": "yes", "test": "yes", "client_paid_fee": "test", "client_paid_fee_amount": "test", "client_paid_fee_enabled_date": "test", "client_paid_fee_disabled_date": "test", "full_name": "test", "business_name": "test", "timezone": "test"}, "promotions": [], "flexfund": {"enabled": True}, "offices": []}),
    (AccountBundle, {"id": 42, "name": "test", "product_id": 42, "enabled": "yes", "enabled_date": "test", "disabled_date": "test", "checking_account_enabled": "yes", "w9_enabled": "yes", "services_opt_in": "test", "inspection_types_opt_in": "test", "funding_status": "test", "created_at": "test", "updated_at": "test", "canceled": "yes", "test": "yes", "client_paid_fee": "test", "client_paid_fee_amount": "test", "client_paid_fee_enabled_date": "test", "client_paid_fee_disabled_date": "test", "full_name": "test", "business_name": "test", "timezone": "test"}),
    (Promotion, {"id": 42, "name": "test", "start_date": "test", "end_date": "test", "num_inspections": 42, "promotional_fee": 42, "type": "test"}),
    (Office, {}),
    (TransactionAgreementPending, {"status": "pending", "url": "test", "html": "test", "has_signing_link": True, "card_tokenizer_url": "test", "client": {"name": "test", "email": "test", "phone": "test"}, "total_fee": "test", "inspection_date": "test"}),
    (TransactionAgreementSigned, {"status": "signed", "signer_name": "test", "signed_at": "2026-01-01T00:00:00+00:00", "url": "test", "html": "test"}),
    (TransactionListItem, {}),
    (TransactionIndexResponse, {"records": [], "count": 42}),
    (Transaction, {}),
    (TransactionCreateResponse, {"uuid": "test", "agreement_sign_url": "test", "agreement_email": "sent"}),
    (TransactionUpdateResponse, {"uuid": "test", "agreement_sign_url": "test"}),
    (ShowAgreementUrlResponse, {"agreement_sign_url": "test", "signed": True}),
    (ScopeGroup, {"resource": "test", "read": "test", "write": "test", "description": "test"}),
    (ApiClient, {"id": "test", "name": "test", "revoked": True, "created_at": "test", "scopes": []}),
    (FlexFundStatus, {"enabled": True}),
    (AgreementClient, {"name": "test", "email": "test", "phone": "test"}),
]


@pytest.mark.parametrize(("model", "dummy"), CASES, ids=[model.__name__ for model, _ in CASES])
def test_round_trip(model: type[BaseModel], dummy: dict[str, Any]) -> None:
    instance = model.model_validate(dummy)

    assert instance.model_dump(mode="json", by_alias=True, exclude_unset=True) == dummy
