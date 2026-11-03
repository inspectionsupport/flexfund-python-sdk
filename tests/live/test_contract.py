"""Live contract checks against a real FlexFund. Skipped unless credentials are in the environment.

Why this exists: the generated tests build their requests and responses from the same schema as the
SDK, so they can agree with each other and still disagree with the server. These call the real API
and parse its real answers into the typed models.

    FLEXFUND_LIVE_BASE_URL      e.g. https://api-staging.example.com
    FLEXFUND_LIVE_CLIENT_ID     an OAuth client's id
    FLEXFUND_LIVE_CLIENT_SECRET its secret (never commit it)
    FLEXFUND_LIVE_SCOPES        optional, space-separated; defaults to the three read scopes
    FLEXFUND_LIVE_VERIFY_TLS    optional; set to 0 ONLY for a local dev server with a self-signed
                                certificate. TLS verification is on unless you turn it off.

Every call here is read-only. A check that needs data the credentials cannot see (no
transactions, no signed agreement) or a permission they lack skips with the reason, rather than
failing or passing vacuously; anything else must pass. Whatever goes wrong, the only exceptions
allowed out are ``FlexFundError`` subclasses: a stray ``pydantic.ValidationError`` or ``httpx``
error is a failure.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import NoReturn

import pytest

from flexfund import (
    AsyncFlexFundClient,
    AuthorizationError,
    FlexFundClient,
    NotFoundError,
    ValidationError,
)
from flexfund.models.account_detailed import AccountDetailed
from flexfund.models.account_o_auth_client import AccountOAuthClient
from flexfund.models.account_show_response import AccountShowResponse
from flexfund.models.account_summary import AccountSummary
from flexfund.models.show_agreement_url_response import ShowAgreementUrlResponse
from flexfund.models.transaction import Transaction
from flexfund.models.transaction_agreement_pending import TransactionAgreementPending
from flexfund.models.transaction_agreement_signed import TransactionAgreementSigned
from flexfund.models.transaction_index_request import TransactionIndexRequest
from flexfund.models.transaction_index_response import TransactionIndexResponse

_VARS = ("FLEXFUND_LIVE_BASE_URL", "FLEXFUND_LIVE_CLIENT_ID", "FLEXFUND_LIVE_CLIENT_SECRET")
_DEFAULT_SCOPES = ["account:read", "transaction:read", "transaction-agreement:read"]

pytestmark = pytest.mark.skipif(
    not all(os.environ.get(v) for v in _VARS),
    reason="live FlexFund credentials not set in the environment",
)

NO_SUCH_UUID = "00000000-0000-0000-0000-000000000000"
# The listing defaults to the in-progress tab. "all" asks for every status, so a credential's
# completed or cancelled orders do not make these checks skip.
ALL = "all"


def _scopes() -> list[str]:
    return os.environ.get("FLEXFUND_LIVE_SCOPES", "").split() or _DEFAULT_SCOPES


def _credentials() -> dict[str, object]:
    return {
        "client_id": os.environ["FLEXFUND_LIVE_CLIENT_ID"],
        "client_secret": os.environ["FLEXFUND_LIVE_CLIENT_SECRET"],
        "base_url": os.environ["FLEXFUND_LIVE_BASE_URL"],
        "scopes": _scopes(),
        "verify": os.environ.get("FLEXFUND_LIVE_VERIFY_TLS", "1").lower()
        not in {"0", "false", "no"},
    }


@pytest.fixture(scope="module")
def client() -> Iterator[FlexFundClient]:
    with FlexFundClient(**_credentials()) as c:  # type: ignore[arg-type]
        yield c


@pytest.fixture(scope="module")
def account_name(client: FlexFundClient) -> str:
    rows = client.account.index()
    if not rows:
        pytest.skip("these credentials can see no accounts")
    return rows[0].name


@pytest.fixture(scope="module")
def first_transaction_uuid(client: FlexFundClient) -> str:
    page = client.transaction.index(TransactionIndexRequest(tab=ALL, start=0, offset=1))
    if not page.records:
        pytest.skip("these credentials can see no transactions")
    return page.records[0].uuid


def _skip_forbidden(client: FlexFundClient, what: str) -> NoReturn:
    """Skip a check the credentials may not make, saying which scopes the token does carry.

    A 403 here is a permission gap on the test credentials (a scope missing from the OAuth client's
    allow-list, or a role that is too low), not a defect in the SDK, so it must not read as one. The
    granted scopes are in the message so the gap can be fixed without guessing.
    """
    provider = client._transport._token_provider
    granted = " ".join(provider.token().scopes) if provider is not None else "?"
    pytest.skip(f"{what}; this token's scopes: [{granted}]")


def test_can_mint_a_token(client: FlexFundClient) -> None:
    provider = client._transport._token_provider
    assert provider is not None
    token = provider.token()
    assert token.token
    assert not token.is_expiring_within(60)


# -- accounts -----------------------------------------------------------------------------


def test_account_index_default_is_the_lean_shape(client: FlexFundClient) -> None:
    rows = client.account.index()
    assert rows, "a client's own account must be visible to it"
    assert {type(r) for r in rows} == {AccountSummary}
    assert all(r.name and r.id for r in rows)


def test_account_index_detailed_is_the_full_shape_for_the_same_accounts(
    client: FlexFundClient,
) -> None:
    lean = client.account.index()
    full = client.account.index(detailed=True)
    assert {type(r) for r in full} == {AccountDetailed}
    assert [r.name for r in full] == [r.name for r in lean]


def test_account_show_parses_the_typed_bundle(client: FlexFundClient, account_name: str) -> None:
    try:
        result = client.account.show(account_name)
    except AuthorizationError:
        _skip_forbidden(client, "these credentials may not read the account detail bundle")
    assert isinstance(result, AccountShowResponse)
    assert result.account.name == account_name
    assert isinstance(result.flexfund.enabled, bool)
    assert isinstance(result.offices, list)
    assert result.promotions is None or isinstance(result.promotions, list)
    assert result.timezone_hint is None or isinstance(result.timezone_hint, str)


def test_account_oauth_client_never_returns_the_secret(
    client: FlexFundClient, account_name: str
) -> None:
    try:
        result = client.account.oauth_client(account_name)
    except AuthorizationError:
        _skip_forbidden(client, "these credentials may not read the account's API client")
    assert isinstance(result, AccountOAuthClient)
    assert result.token_url
    assert result.grant_type == "client_credentials"
    assert result.available_scopes
    assert "secret" not in repr(result).lower().replace("client_secret", "")
    if result.client is not None:
        assert result.client.revoked in (True, False)


def test_an_unknown_account_is_not_found(client: FlexFundClient) -> None:
    with pytest.raises((NotFoundError, AuthorizationError)):
        client.account.show("no-such-account-key-for-contract-test")


# -- transactions -------------------------------------------------------------------------


def test_transaction_index_pages_consistently(client: FlexFundClient) -> None:
    page = client.transaction.index(TransactionIndexRequest(tab=ALL))
    assert isinstance(page, TransactionIndexResponse)
    assert page.count >= len(page.records)

    if page.count < 2:
        pytest.skip("need at least two visible transactions to check paging")

    first = client.transaction.index(TransactionIndexRequest(tab=ALL, start=0, offset=1))
    second = client.transaction.index(TransactionIndexRequest(tab=ALL, start=1, offset=1))
    assert len(first.records) == len(second.records) == 1
    assert first.records[0].uuid != second.records[0].uuid
    assert first.count == second.count == page.count


def test_transaction_rows_carry_the_account_key(client: FlexFundClient) -> None:
    page = client.transaction.index(TransactionIndexRequest(tab=ALL, start=0, offset=5))
    if not page.records:
        pytest.skip("these credentials can see no transactions")
    assert all(row.account_key for row in page.records)


def test_transaction_show_matches_the_listing(
    client: FlexFundClient, first_transaction_uuid: str
) -> None:
    result = client.transaction.show(first_transaction_uuid)
    assert isinstance(result, Transaction)
    assert result.get("uuid") == first_transaction_uuid


def test_an_unknown_transaction_is_not_found(client: FlexFundClient) -> None:
    with pytest.raises(NotFoundError):
        client.transaction.show(NO_SUCH_UUID)


def test_transaction_agreement_is_pending_or_signed(
    client: FlexFundClient, first_transaction_uuid: str
) -> None:
    try:
        agreement = client.transaction_agreement.show(first_transaction_uuid)
    except AuthorizationError:
        _skip_forbidden(client, "the token lacks the transaction-agreement:read scope")
    except (NotFoundError, ValidationError):
        pytest.skip("the first visible transaction has no agreement to show")
    assert isinstance(agreement, TransactionAgreementPending | TransactionAgreementSigned)
    # The discriminator must agree with the model the SDK picked.
    expected = "pending" if isinstance(agreement, TransactionAgreementPending) else "signed"
    assert agreement.status == expected


def test_agreement_url_for_a_visible_transaction(
    client: FlexFundClient, first_transaction_uuid: str
) -> None:
    try:
        result = client.transaction.agreement_url(first_transaction_uuid)
    except AuthorizationError:
        _skip_forbidden(client, "the token may not read this transaction's signing link")
    except (NotFoundError, ValidationError):
        pytest.skip("the first visible transaction has no signing link (not created here)")
    assert isinstance(result, ShowAgreementUrlResponse)
    assert result.agreement_sign_url.startswith("http")


# -- the async client ---------------------------------------------------------------------


async def test_async_client_reads_the_same_data(client: FlexFundClient) -> None:
    async with AsyncFlexFundClient(**_credentials()) as c:  # type: ignore[arg-type]
        async_rows = await c.account.index()
    assert [r.name for r in async_rows] == [r.name for r in client.account.index()]
