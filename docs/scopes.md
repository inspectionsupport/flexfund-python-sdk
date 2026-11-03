<!-- Generated file. Do not edit. -->

# OAuth scopes

Every scope the FlexFund REST API (`v20260322`) defines, and the SDK calls each one
gates. Pass the scopes you need as `scopes=[...]` when building the client — FlexFund
returns 403 (an `AuthorizationError`) for any call whose required scope the
token was not granted.

## `account:read`

| SDK call | HTTP |
| --- | --- |
| `client.account.index()` | `GET /v20260322/account` |
| `client.account.show()` | `GET /v20260322/account/{id}` |
| `client.account.oauth_client()` | `GET /v20260322/account/{id}/oauth-client` |

## `transaction-agreement:read`

| SDK call | HTTP |
| --- | --- |
| `client.transaction_agreement.show()` | `GET /v20260322/transaction-agreement/{id}` |

## `transaction:read`

| SDK call | HTTP |
| --- | --- |
| `client.transaction.index()` | `GET /v20260322/transaction` |
| `client.transaction.show()` | `GET /v20260322/transaction/{id}` |
| `client.transaction.agreement_url()` | `GET /v20260322/transaction/{id}/agreement-url` |

## `transaction:write`

| SDK call | HTTP |
| --- | --- |
| `client.transaction.store()` | `POST /v20260322/transaction` |
| `client.transaction.update()` | `PUT /v20260322/transaction/{id}` |
