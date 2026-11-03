"""Objects nested inside responses are real models, not loose dicts."""

from __future__ import annotations

from typing import Any

import pytest

from flexfund import ResponseError
from flexfund._serde import decode
from flexfund.models.account_bundle import AccountBundle
from flexfund.models.account_o_auth_client import AccountOAuthClient
from flexfund.models.account_show_response import AccountShowResponse
from flexfund.models.agreement_client import AgreementClient
from flexfund.models.api_client import ApiClient
from flexfund.models.flex_fund_status import FlexFundStatus
from flexfund.models.office import Office
from flexfund.models.promotion import Promotion
from flexfund.models.scope_group import ScopeGroup

ACCOUNT: dict[str, Any] = {
    "id": 1,
    "name": "acme",
    "product_id": 2,
    "enabled": "yes",
    "enabled_date": "2026-01-01 00:00:00",
    "disabled_date": None,
    "checking_account_enabled": "yes",
    "w9_enabled": "no",
    "services_opt_in": None,
    "inspection_types_opt_in": None,
    "funding_status": None,
    "created_at": "2026-01-01 00:00:00",
    "updated_at": None,
    "canceled": "no",
    "test": "no",
    "client_paid_fee": None,
    "client_paid_fee_amount": "0.00",
    "client_paid_fee_enabled_date": None,
    "client_paid_fee_disabled_date": None,
    "full_name": "Acme Inspections LLC",
    "business_name": None,
    "timezone": "America/Chicago",
}
PROMOTION: dict[str, Any] = {
    "id": 7,
    "name": "Launch month",
    "start_date": "2026-10-01 00:00:00",
    "end_date": "2026-10-31 00:00:00",
    "num_inspections": None,
    "promotional_fee": 15,
    "type": "date",
}
OFFICE: dict[str, Any] = {
    "id": "office-uuid-1",
    "officeId": 1,
    "primaryOffice": True,
    "timezoneName": "America/Chicago",
}
SHOW: dict[str, Any] = {
    "account": ACCOUNT,
    "promotions": [PROMOTION],
    "flexfund": {"enabled": True},
    "offices": [OFFICE],
}

OAUTH_CLIENT: dict[str, Any] = {
    "token_url": "https://api.example.test/oauth/token",
    "grant_type": "client_credentials",
    "default_scopes": ["account:read"],
    "available_scopes": [
        {
            "resource": "account",
            "read": "account:read",
            "write": "account:write",
            "description": None,
        }
    ],
    "client": {
        "id": "9a1c",
        "name": "Acme integration",
        "revoked": False,
        "created_at": "2026-10-01 12:00:00",
        "scopes": ["account:read"],
    },
}


def test_oauth_client_details_are_typed() -> None:
    result = decode(AccountOAuthClient, OAUTH_CLIENT)
    assert isinstance(result.client, ApiClient)
    assert result.client.name == "Acme integration"
    assert result.client.revoked is False
    assert [type(group) for group in result.available_scopes] == [ScopeGroup]
    assert result.available_scopes[0].write == "account:write"


def test_an_account_without_an_api_client_has_none() -> None:
    assert decode(AccountOAuthClient, {**OAUTH_CLIENT, "client": None}).client is None


def test_a_null_client_scopes_list_means_unrestricted_and_is_kept_distinct_from_empty() -> None:
    unrestricted = decode(
        AccountOAuthClient, {**OAUTH_CLIENT, "client": {**OAUTH_CLIENT["client"], "scopes": None}}
    )
    nothing = decode(
        AccountOAuthClient, {**OAUTH_CLIENT, "client": {**OAUTH_CLIENT["client"], "scopes": []}}
    )
    assert unrestricted.client is not None and unrestricted.client.scopes is None
    assert nothing.client is not None and nothing.client.scopes == []


@pytest.mark.parametrize(
    "client",
    [{"id": "9a1c"}, {**OAUTH_CLIENT["client"], "revoked": "maybe"}],
)
def test_a_malformed_nested_object_is_a_response_error(client: dict[str, Any]) -> None:
    with pytest.raises(ResponseError) as exc:
        decode(AccountOAuthClient, {**OAUTH_CLIENT, "client": client})
    assert "client" in exc.value.message


def test_the_account_show_bundle_is_typed_end_to_end() -> None:
    result = decode(AccountShowResponse, SHOW)
    assert isinstance(result.account, AccountBundle)
    assert result.account.name == "acme"
    assert result.account.timezone == "America/Chicago"
    assert result.account.client_paid_fee_amount == "0.00"
    assert [type(p) for p in (result.promotions or [])] == [Promotion]
    assert result.promotions is not None and result.promotions[0].promotional_fee == 15
    assert [type(o) for o in result.offices] == [Office]
    assert result.offices[0].office_id == 1
    assert result.offices[0].primary_office is True
    assert isinstance(result.flexfund, FlexFundStatus)
    assert result.flexfund.enabled is True


def test_the_external_account_model_leaves_out_commercial_terms_and_credentials() -> None:
    hidden = {
        "fee_per_inspection",
        "fee_per_submission",
        "minimum_dollar_threshold",
        "maximum_dollar_threshold",
        "oauth_client_id",
        "disabled_by",
        "disabled_reason",
        "funding_warning",
        "verification_amount",
        "state_id",
    }
    assert not hidden & set(AccountBundle.model_fields)
    assert not {"account_id", "vendor_id", "created_by", "show"} & set(Promotion.model_fields)


def test_promotions_may_be_absent_and_a_missing_required_field_is_a_response_error() -> None:
    assert decode(AccountShowResponse, {**SHOW, "promotions": None}).promotions is None
    with pytest.raises(ResponseError):
        decode(AccountShowResponse, {**SHOW, "account": {"id": 1}})


def test_an_office_with_only_some_fields_is_accepted() -> None:
    """Offices come from an upstream system, so every field is optional."""
    result = decode(Office, {"officeId": 3})
    assert result.office_id == 3
    assert result.id is None


def test_agreement_client_fields_may_be_null() -> None:
    result = decode(AgreementClient, {"name": None, "email": "a@example.com", "phone": None})
    assert result.email == "a@example.com"
    assert result.name is None
