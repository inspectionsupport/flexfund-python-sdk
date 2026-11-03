from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flexfund import AsyncFlexFundClient, FlexFundClient
from flexfund.auth.credentials import ClientCredentials
from flexfund.auth.token import AccessToken

SECRET = "test-client-secret"
TOKEN = "super-secret-access-token"


def test_credentials_repr_hides_secret() -> None:
    creds = ClientCredentials("test-client-id", SECRET, ("a:read",))
    assert SECRET not in repr(creds)
    assert SECRET not in str(creds)
    assert "test-client-id" in repr(creds)


def test_access_token_repr_hides_token() -> None:
    token = AccessToken(TOKEN, datetime.now(UTC) + timedelta(hours=1), ("a:read",))
    assert TOKEN not in repr(token)
    assert TOKEN not in str(token)


def test_clients_do_not_expose_secret_in_repr() -> None:
    with FlexFundClient(
        client_id="test-client-id", client_secret=SECRET, base_url="https://flexfund.test"
    ) as c:
        assert SECRET not in repr(c)
        assert SECRET not in repr(vars(c))
        assert SECRET not in repr(vars(c._transport))
    a = AsyncFlexFundClient(
        client_id="test-client-id", client_secret=SECRET, base_url="https://flexfund.test"
    )
    assert SECRET not in repr(a)
    assert SECRET not in repr(vars(a))


def test_sensitive_model_fields_are_masked_in_repr() -> None:
    from flexfund._serde import FlexFundRequestModel

    class Credentials(FlexFundRequestModel):
        password: str
        secret: str
        account_number: str
        routing_number: str
        label: str

    shown = repr(
        Credentials(
            password="hunter2",
            secret="S3CRET",
            account_number="999",
            routing_number="111",
            label="ok",
        )
    )
    for hidden in ("hunter2", "S3CRET", "999", "111"):
        assert hidden not in shown
    assert "ok" in shown
