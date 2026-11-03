# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/) independently of the FlexFund API version.

## [Unreleased]

## [1.0.0] - 2026-11-03

First stable release. Targets the FlexFund REST API `v20260322`. From here on, breaking changes to
the public API ship only in a new major version. 0.2.0 was never released: its changes are below.

### Added

- `StoreTransactionRequest` and `UpdateTransactionRequest` take the buyer's agent (`agent_name`,
  `agent_email`, `agent_phone`) and the inspector (`inspector_name`, `inspector_email`). All are optional;
  on update they can be cleared with `None`, and the inspector can only be edited on orders created in
  FlexFund.
- `TransactionCreateResponse.agreement_email` (the new `AgreementEmail` enum: `sent`, `failed`,
  `not_configured`) says whether the client was emailed their signing link. The order is created either
  way.

### Changed

- **`base_url` is now required, and `environment=` and the `Environment` enum are gone.** The SDK no
  longer ships endpoint URLs; contact FlexFund support for yours and pass it as `base_url`.
  `FlexFundClient(..., environment="production")` becomes `FlexFundClient(..., base_url="<your URL>")`.
- The SDK is now MIT-licensed (it was proprietary). Releases 0.1.0 and 0.1.1 keep their original
  terms.
- A token endpoint that is down, unreachable or rate-limiting now raises `ServerError` or
  `RateLimitError` instead of `AuthenticationError`, so callers that treat `AuthenticationError` as
  permanent no longer drop work over an outage. **If you caught `AuthenticationError` to handle a
  token-endpoint outage, catch `ServerError` too.**
- A caller-supplied `http_client` must have a `base_url` on the same origin as the client's
  `base_url`, and is held to the same HTTPS rule; otherwise the client raises `ValueError`. Before,
  any `http_client` was accepted and received the access token.
- `verify=False` for a non-local host now emits a `UserWarning`.
- `max_attempts` below 1 raises `ValueError` (it used to behave like 1).
- Request bodies now send a field you set to `None` explicitly as JSON `null`, which is how an update
  clears a nullable field (`UpdateTransactionRequest(agent_name=None)` removes the buyer's agent). Fields
  you leave out are still not sent. Before 1.0.0 an explicit `None` was dropped like an unset field, so
  code that passes `None` to mean "don't change" must leave the field out instead: a nullable field such
  as `order_number` would now be cleared, and a non-nullable one such as `title_confirmed` gets a
  `ValidationError` (422).
- `agreement_email` is a required field of `TransactionCreateResponse`, so a server that does not send it
  yet makes `transaction.store()` raise `ResponseError`. Upgrade once the server you call has the change.

### Fixed

- A response body that can't be decoded (e.g. a bad gzip encoding) or too many redirects on your
  own `http_client` raised a raw `httpx` exception; it is now a `ServerError`.
- A `Retry-After` header with an absurd number of digits crashed the retry path with
  `OverflowError`/`ValueError`; it is now clamped.
- A malformed token response (bad `expires_in`) left the live access token on the
  `AuthenticationError`'s `.body` and `.raw_body`, where error trackers could capture it. It is
  now redacted.
- An exception from a custom `TokenCache`/`AsyncTokenCache` (a Redis outage) escaped every call; it
  is now logged as a warning and the token is requested from FlexFund instead.

### Security

- The lockfile now pins `certifi` 2026.10.23, past PYSEC-2026-4320. This affects development and CI
  installs only; installing the SDK resolves your own `certifi`.

## [0.1.1] - 2026-10-13

First supported release (0.1.0 was an early pre-release; see below). Targets the FlexFund REST API
`v20260322`.

### Added

- `FlexFundClient` and `AsyncFlexFundClient`, with `account`, `transaction` and `transaction_agreement`
  resources and Pydantic v2 models for every request and response.
- OAuth2 `client_credentials` authentication with in-memory and pluggable token caching. When many
  concurrent requests are rejected with a 401 for the same token they share one refresh, instead of each
  minting a new token.
- Typed responses where the shape depends on the call: `account.index()` returns
  `list[AccountDetailed]` with `detailed=True` and `list[AccountSummary]` otherwise, and
  `transaction_agreement.show()` returns `TransactionAgreementPending | TransactionAgreementSigned`,
  narrowed by checking `status`.
- A single error hierarchy under `FlexFundError`. A successful response the SDK cannot parse raises
  `ResponseError`, and a malformed token response raises `AuthenticationError`, so
  `except FlexFundError` covers everything the server can send. Building a request model with bad values
  still raises `pydantic.ValidationError` locally, before anything is sent.
- Automatic retries with backoff, an optional FastAPI helper (`flexfund.fastapi`), and a read-only live
  contract test suite (`tests/live`) that checks the typed models against a real server.

### Known limitations

- `Transaction` is a read-only mapping wrapper, not a typed model; read fields with `.get(key)`.
- Office rows (`AccountShowResponse.offices`) model only the fields that are always present.

## [0.1.0] - 2026-10-07

Early pre-release, superseded by 0.1.1 and not recommended. Generated sync and async clients and models for
the FlexFund REST API `v20260322`, before the typed responses, `ResponseError`, the coalesced token refresh
and the live contract tests described above.
