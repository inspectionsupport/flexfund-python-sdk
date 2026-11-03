# Generated code. Do not edit.

from flexfund._serde import FlexFundResponseModel
from flexfund.models.api_client import ApiClient
from flexfund.models.scope_group import ScopeGroup


class AccountOAuthClient(FlexFundResponseModel):
    token_url: str
    """where to POST the client_credentials grant; outside the versioned prefix"""

    grant_type: str
    """always client_credentials"""

    default_scopes: list[str]
    """what a newly generated client is granted, and what a token gets when it requests no scopes —
    the :read half of the list
    """

    available_scopes: list[ScopeGroup]
    """the full scope catalogue grouped by resource, so a client can render a read/write grid without
    hardcoding resource names. read or write is null for a resource that has only one kind
    (reporting is write-only, product read-only).
    """

    client: ApiClient | None
    """null when this account has no API client yet"""
