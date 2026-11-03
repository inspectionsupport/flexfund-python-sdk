# Generated code. Do not edit.

from typing import Any, Literal, overload
from urllib.parse import quote

from flexfund._http.transport import AsyncTransport, SyncTransport
from flexfund._serde import decode, decode_list
from flexfund.models.account_detailed import AccountDetailed
from flexfund.models.account_o_auth_client import AccountOAuthClient
from flexfund.models.account_show_response import AccountShowResponse
from flexfund.models.account_summary import AccountSummary


class AccountResource:
    """SDK access to the `account` endpoint (v20260322). Use `client.account`; don't construct directly."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    @overload
    def index(
        self,
        *,
        detailed: Literal[True],
    ) -> list[AccountDetailed]: ...

    @overload
    def index(
        self,
        *,
        detailed: Literal[False] | None = None,
    ) -> list[AccountSummary]: ...

    @overload
    def index(
        self,
        *,
        detailed: bool,
    ) -> list[AccountDetailed] | list[AccountSummary]: ...

    def index(
        self,
        *,
        detailed: bool | None = None,
    ) -> list[AccountDetailed] | list[AccountSummary]:
        """Lists accounts visible to the caller (all accounts for a Super Admin, just their own otherwise).
        Lean {id, name} shape by default; pass ?detailed=1 for the full field set.

        Scopes: `account:read`

        Args:
            detailed: Return the full field set instead of {id, name}.

        Returns:
            AccountDetailed[] when `detailed` is true,
            otherwise AccountSummary[].
        """
        query: dict[str, Any] = {}
        if detailed is not None:
            query["detailed"] = detailed
        data = self._transport.request("GET", "v20260322/account", query=query)
        if detailed:
            return decode_list(AccountDetailed, data)
        return decode_list(AccountSummary, data)

    def show(
        self,
        id: int | str,
    ) -> AccountShowResponse:
        """Returns the account detail bundle (account, promotions, offices and feature settings).

        Scopes: `account:read`

        Args:
            id: The resource id.

        Raises:
            NotFoundError: Unknown account key.
        """
        data = self._transport.request("GET", f"v20260322/account/{quote(str(id), safe='')}")
        return decode(AccountShowResponse, data)

    def oauth_client(
        self,
        id: int | str,
    ) -> AccountOAuthClient:
        """Returns the API client credentials configured for this account, excluding the secret, along with the
        token URL and grant type needed to use them.

        Scopes: `account:read`

        Args:
            id: The resource id.

        Raises:
            NotFoundError: Unknown account.
        """
        data = self._transport.request("GET", f"v20260322/account/{quote(str(id), safe='')}/oauth-client")
        return decode(AccountOAuthClient, data)


class AsyncAccountResource:
    """Async SDK access to the `account` endpoint (v20260322). Use `client.account`; don't construct directly."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    @overload
    async def index(
        self,
        *,
        detailed: Literal[True],
    ) -> list[AccountDetailed]: ...

    @overload
    async def index(
        self,
        *,
        detailed: Literal[False] | None = None,
    ) -> list[AccountSummary]: ...

    @overload
    async def index(
        self,
        *,
        detailed: bool,
    ) -> list[AccountDetailed] | list[AccountSummary]: ...

    async def index(
        self,
        *,
        detailed: bool | None = None,
    ) -> list[AccountDetailed] | list[AccountSummary]:
        """Lists accounts visible to the caller (all accounts for a Super Admin, just their own otherwise).
        Lean {id, name} shape by default; pass ?detailed=1 for the full field set.

        Scopes: `account:read`

        Args:
            detailed: Return the full field set instead of {id, name}.

        Returns:
            AccountDetailed[] when `detailed` is true,
            otherwise AccountSummary[].
        """
        query: dict[str, Any] = {}
        if detailed is not None:
            query["detailed"] = detailed
        data = await self._transport.request("GET", "v20260322/account", query=query)
        if detailed:
            return decode_list(AccountDetailed, data)
        return decode_list(AccountSummary, data)

    async def show(
        self,
        id: int | str,
    ) -> AccountShowResponse:
        """Returns the account detail bundle (account, promotions, offices and feature settings).

        Scopes: `account:read`

        Args:
            id: The resource id.

        Raises:
            NotFoundError: Unknown account key.
        """
        data = await self._transport.request("GET", f"v20260322/account/{quote(str(id), safe='')}")
        return decode(AccountShowResponse, data)

    async def oauth_client(
        self,
        id: int | str,
    ) -> AccountOAuthClient:
        """Returns the API client credentials configured for this account, excluding the secret, along with the
        token URL and grant type needed to use them.

        Scopes: `account:read`

        Args:
            id: The resource id.

        Raises:
            NotFoundError: Unknown account.
        """
        data = await self._transport.request("GET", f"v20260322/account/{quote(str(id), safe='')}/oauth-client")
        return decode(AccountOAuthClient, data)
