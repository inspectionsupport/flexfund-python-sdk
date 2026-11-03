<h1 align="center">FlexFund Python SDK</h1>

<p align="center">
  <strong>A public Python SDK to interact with FlexFund transactions, accounts and agreements.</strong>
</p>

<p align="center">
  FlexFund is the pay-at-close payment option from
  <a href="https://inspectionpayments.com/">Guardian Inspection Payments</a>.
</p>

<p align="center">
  <a href="https://inspectionpayments.com/">Website</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#quickstart">Quickstart</a>
</p>

This is the official Python SDK for the FlexFund REST API (`v20260322`). Use it to create and
update FlexFund transactions, look up accounts, and fetch agreements and signing links from your
own Python application. The package is `flexfund-sdk`, imported as `flexfund`.

It authenticates with FlexFund's OAuth2 `client_credentials` grant and provides:

- `FlexFundClient`, a synchronous client, and `AsyncFlexFundClient`, an asynchronous one. Both expose
  the same resources and methods.
- Pydantic v2 models for requests and responses, and enums for the API's fixed value sets.
- Typed errors, automatic retries, and token caching.
- An optional FastAPI helper, `flexfund.fastapi`.

The resources, models and enums (`flexfund.resources`, `flexfund.models`,
`flexfund.enums`) and [`docs/scopes.md`](docs/scopes.md) are generated from FlexFund's API
schema. Everything else (auth, HTTP, errors, clients) is hand-written.

## Requirements

- Python 3.12 or newer.
- `httpx` and `pydantic` v2. Both are installed automatically.
- FastAPI, only if you use `flexfund.fastapi` (the `fastapi` extra).

## Installation

The package is distributed from its Git repository, pinned to a release tag:

```sh
pip install "flexfund-sdk @ git+https://github.com/inspectionsupport/flexfund-python-sdk@v1.0.0"

# with the FastAPI helper
pip install "flexfund-sdk[fastapi] @ git+https://github.com/inspectionsupport/flexfund-python-sdk@v1.0.0"
```

With uv: `uv add "flexfund-sdk @ git+https://github.com/inspectionsupport/flexfund-python-sdk@v1.0.0"`.

## Quickstart

```python
from flexfund import FlexFundClient

with FlexFundClient(
    client_id="...",
    client_secret="...",
    base_url="https://...",  # your FlexFund API endpoint, from FlexFund support
    scopes=["account:read", "transaction:read"],
) as client:
    accounts = client.account.index(detailed=True)
    page = client.transaction.index()  # TransactionIndexResponse
    print(page.count, len(page.records))
    txn = client.transaction.show(12345)
```

The async client is the same, with `async with` and `await`:

```python
import asyncio
from flexfund import AsyncFlexFundClient


async def main() -> None:
    async with AsyncFlexFundClient(
        client_id="...",
        client_secret="...",
        base_url="https://...",  # your FlexFund API endpoint, from FlexFund support
        scopes=["account:read"],
    ) as client:
        accounts = await client.account.index()


asyncio.run(main())
```

Every endpoint is a method on a resource attribute of the client: `client.account`,
`client.transaction`, `client.transaction_agreement`.
[`docs/scopes.md`](docs/scopes.md) lists every call. Endpoints with a request body take a
model from `flexfund.models`:

```python
from flexfund.models.store_transaction_request import StoreTransactionRequest

created = client.transaction.store(
    StoreTransactionRequest(
        valid=True,
        account_key="acme",
        amount=450.0,
        order_full_address="1 Main St, Springfield",
        client_name="A Client",
        client_email="client@example.com",
        client_phone="555-0100",
    )
)
```

Notes on what comes back:

- Most calls return a model. Some schemas are free-form objects (for example `Transaction`);
  those come back as a read-only mapping wrapper with `.get(key)`, `[key]` and `in`, and the raw
  dict at `.root`.
- `client.account.index` returns `list[AccountSummary]` by default and `list[AccountDetailed]` with
  `detailed=True`. The overloads let a type checker see which, and the response is decoded with the
  model the argument implies. If the server answers with the other shape you get a `ResponseError`.
- `client.transaction_agreement.show` returns `TransactionAgreementPending | TransactionAgreementSigned`,
  told apart by `status`, so checking `agreement.status` narrows the type for you. A `status` the SDK
  does not know, or a payload that does not fit the model its `status` names, is a `ResponseError`.
- FlexFund's index endpoints return full lists; `transaction.index` is the exception and takes
  `start` / `offset` in its request model.
- Models are frozen (immutable).

### Client options

| Argument | Default | Meaning |
| --- | --- | --- |
| `client_id`, `client_secret` | required | OAuth client credentials. |
| `scopes` | `()` | Scopes to request. See [Credentials and scopes](#credentials-and-scopes). |
| `base_url` | required | Your FlexFund API endpoint URL. Contact FlexFund support for it. |
| `timeout` | `30.0` | Seconds for a request once connected. |
| `connect_timeout` | `5.0` | Seconds to establish a connection. |
| `max_attempts` | `3` | Total attempts for a retryable failure. See [Retries](#retries). |
| `token_cache` | in-memory | A `TokenCache` (`AsyncTokenCache` for the async client). |
| `verify` | `True` | Verify TLS certificates. |
| `http_client` | created for you | Your own `httpx.Client` / `httpx.AsyncClient` for API calls. |

The client closes the `httpx` clients it created itself. An `http_client` you pass in is yours to
close. If you pass one, it must already carry the right `base_url`; the SDK does not set it. Its
`base_url` must be on the same scheme, host and port as the client's `base_url`, under the same
HTTPS rule, because it receives the access token on every request; anything else is a `ValueError`.

`verify=False` turns off TLS certificate checks for both the API and the token request. It emits a
`UserWarning` unless the host is a local development host (`localhost`, `*.localhost`, `*.test`).

## FastAPI integration

`flexfund.fastapi` builds one `AsyncFlexFundClient` when the app starts, closes it on shutdown
and hands it to your handlers as a dependency. Install the `fastapi` extra first.

```python
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from flexfund import AsyncFlexFundClient, FlexFundError
from flexfund.fastapi import FlexFundDep, flexfund_lifespan


def make_client() -> AsyncFlexFundClient:
    return AsyncFlexFundClient(
        client_id=os.environ["FLEXFUND_CLIENT_ID"],
        client_secret=os.environ["FLEXFUND_CLIENT_SECRET"],
        base_url=os.environ["FLEXFUND_BASE_URL"],
        scopes=["account:read"],
    )


app = FastAPI(lifespan=flexfund_lifespan(make_client))


@app.exception_handler(FlexFundError)
async def flexfund_error_handler(request: Request, exc: FlexFundError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": exc.message})


@app.get("/accounts")
async def accounts(flexfund: FlexFundDep):
    return await flexfund.account.index()
```

If you already have a lifespan, nest `flexfund_client_context(factory, app)` inside it instead.
It builds the client, stores it on `app.state.flexfund` (which `FlexFundDep` reads), and closes it on
exit:

```python
from contextlib import asynccontextmanager
from flexfund.fastapi import flexfund_client_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with flexfund_client_context(make_client, app):
        ...  # your own startup
        yield


app = FastAPI(lifespan=lifespan)
```

`FlexFundDep` raises a `RuntimeError` if no client was registered on the app.

## Credentials and scopes

FlexFund issues an OAuth client (id and secret) per account. Request the scopes you need with
`scopes=[...]`; the token carries only those. Scopes follow the pattern `<resource>:read` and
`<resource>:write`.

**[Full scope reference](docs/scopes.md)** lists every scope and the SDK calls it gates. That file is
generated from the same schema the API enforces, so it cannot drift from the server.

A `403` (`AuthorizationError`) does not always mean a missing scope. Some endpoints additionally
check the role of the account or user behind the OAuth client, and reject a role that is too low
even when the scope is granted. If a call returns a 403 and you did request the right scope, the
account's role is usually what needs to change, not the SDK call.

Keep the client secret out of source control. The SDK never logs it, never includes it in the
`repr()` of its objects, and never writes it to a token cache.

## Errors

Every failure is a subclass of `FlexFundError`; neither `httpx` nor `pydantic` exceptions escape a resource method for anything the server sent.

```text
FlexFundError
├── AuthenticationError   401, or the token endpoint refusing the credentials
├── AuthorizationError    403 (missing scope, or the account's role forbids it)
├── NotFoundError         404
├── ConflictError         409 (permanent; retrying the same request will not help)
├── ValidationError       422
├── RateLimitError        429 (from the API after retries, or from the token endpoint)
├── ResponseError         a 2xx whose body does not match the expected schema
└── ServerError           5xx (API or token endpoint), any other unexpected response, network failures
```

Every error has `.message`, `.status_code` (`None` if no response arrived), `.body` (the decoded JSON
error body, if any) and `.raw_body` (the response text). An error raised while obtaining a token
never carries the token: if the token response was malformed, its `access_token` is redacted in
`.body` and `.raw_body` is `None`.

A token endpoint that is down or rate-limiting raises `ServerError` or `RateLimitError`, never
`AuthenticationError`, so `AuthenticationError` can be treated as "fix the credentials" and the other
two as "try again later".

```python
from flexfund import NotFoundError, RateLimitError, ValidationError

try:
    client.transaction.show("does-not-exist")
except NotFoundError:
    ...
except ValidationError as exc:
    for field, messages in exc.errors.items():
        print(field, messages)
except RateLimitError as exc:
    print("retry in", exc.retry_after)
```

`ResponseError` means the call succeeded but the SDK cannot turn the reply into a model, usually
because the API and this SDK version disagree about its shape. Retrying will not help. `.body` holds
the decoded `data` when it was an object, and the original `pydantic.ValidationError` is its
`__cause__`. The message names the offending fields but never their values. A malformed token
response is an `AuthenticationError` instead.

Building a *request* model yourself with bad values still raises `pydantic.ValidationError` locally,
before anything is sent: that is a mistake in your own code, not a failure of the API.

FlexFund reports a 422 in two different body shapes, one with `code` and a string `message`, the
other with a `message` list and no `code`. `ValidationError.errors` reads the per-field messages
(`{field: [message, ...]}`) correctly from either, and `.message` is always a string (list messages
are joined with `; `). The exception is chosen from the HTTP status, never from the body's `code`.

`ValidationError` has the same name as `pydantic.ValidationError`. If you use both, import the module
rather than the class:

```python
from flexfund import errors

try:
    ...
except errors.ValidationError:
    ...
```

Building a request model can also fail locally with `pydantic.ValidationError` before anything is
sent (for example, an unknown enum value, or an unexpected field).

## Retries

The transport retries automatically, up to `max_attempts` total attempts, with exponential backoff
and full jitter (0 to 0.5 s for the first retry, doubling each time). A `Retry-After` header replaces
the computed delay.

| Failure | GET / HEAD / OPTIONS | POST / PUT / DELETE |
| --- | --- | --- |
| 429 | retried | retried (the request was not processed) |
| 5xx | retried | **not** retried |
| network error / timeout | retried | **not** retried |

Writes are never retried after a 5xx or network error, because there is no way to know whether the
write already landed. Retry those yourself if you know the operation is safe to repeat.

A single `401` triggers one token refresh and one replay of the request, which does not count against
`max_attempts`. A second 401 raises `AuthenticationError`, since `client_credentials` has no refresh
token and that means the credentials are wrong.

## Token caching

The client requests an access token on first use and reuses it until 60 seconds before it expires.
By default it is held in memory, per client, and concurrent callers share a single token request.

To share tokens across processes, pass an object implementing `TokenCache` (or `AsyncTokenCache` for
the async client, with `async def` methods). Values are JSON-safe dicts and keys are opaque hashes
of base URL, client id and scopes; the secret is never involved. `ttl_seconds` is the token's
remaining lifetime. If your cache raises (Redis is down, say), the SDK logs a warning on the
`flexfund` logger and requests a token from FlexFund instead, so a cache outage costs a token
request, not the call.

```python
import json

import redis  # your dependency, not the SDK's

from flexfund import FlexFundClient


class RedisTokenCache:
    def __init__(self, r: redis.Redis) -> None:
        self._r = r

    def get(self, key: str) -> dict | None:
        raw = self._r.get(key)
        return json.loads(raw) if raw else None

    def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        if ttl_seconds > 0:
            self._r.set(key, json.dumps(value), ex=ttl_seconds)

    def delete(self, key: str) -> None:
        self._r.delete(key)


client = FlexFundClient(..., token_cache=RedisTokenCache(redis.Redis()))
```

Cached tokens are bearer credentials: restrict access to the cache accordingly. A missing or
malformed cache entry is treated as a miss.

## Dates and timezones

Date fields are parsed to `datetime.date`, and datetime fields to timezone-aware `datetime` objects
in **UTC**, which is the timezone FlexFund uses. When you send a datetime, naive values are assumed
to be UTC, and aware values are converted to UTC. The wire formats (`YYYY-MM-DD` and
`YYYY-MM-DD HH:MM:SS`) are produced for you.

## Unknown enum values

- **Responses are lenient.** If FlexFund returns an enum value this SDK version does not know yet,
  the field keeps the raw `str` and a warning is logged to the `flexfund` logger, instead of
  failing the whole response. Enum fields in responses are therefore typed `Role | str`; compare
  with `==` (enums are `StrEnum`, so `role == "admin"` works).
- **Requests are strict.** Building a request with a value that is not a known enum member raises
  `pydantic.ValidationError` locally.

An unknown value is a hint to upgrade the SDK.

## Request bodies and `None`

**Only the `None` values you set are sent as `null`.** A field you leave out of a request model is
not sent at all, so "not set" always means "not sent" and an update never clears a value you didn't
mention. A field you set to `None` explicitly is sent as `null`: that is how an update clears a
nullable field, e.g. `UpdateTransactionRequest(agent_name=None)`. Setting a field that isn't
nullable (such as `title_confirmed`) to `None` gets a `ValidationError`, so leave it out instead.

## Environments

Contact FlexFund support for endpoint URLs. Pass the one for the environment you want (production,
staging or any other) as `base_url`; the SDK has no built-in endpoints.

## Versioning

The SDK is versioned independently of the API, using semantic versioning
(`flexfund.__version__`). The API version it was generated against is
`flexfund.API_VERSION` (`"v20260322"`), and every request path includes it. From `1.0.0`, a
breaking change to the SDK's public API only ships in a new major version; minor and patch
releases are backwards compatible. See [`CHANGELOG.md`](CHANGELOG.md).

## Development

```sh
uv sync
uv run pytest -q
uv run mkdocs serve   # API reference
```

The test suite includes live tests that call a real FlexFund and parse its answers into the typed
models. They are read-only and skipped unless you configure them:

```sh
export FLEXFUND_LIVE_BASE_URL=https://...        # the environment to test
export FLEXFUND_LIVE_CLIENT_ID=...
export FLEXFUND_LIVE_CLIENT_SECRET=...            # never commit this
uv run pytest tests/live -v -rs
```

`FLEXFUND_LIVE_SCOPES` (space-separated) overrides the default read scopes. A check that needs data the
credentials cannot see, or a permission they lack, skips and says why. Set `FLEXFUND_LIVE_VERIFY_TLS=0`
only for a local server with a self-signed certificate.

## License

MIT. See [LICENSE](LICENSE). The license covers this SDK's code; it grants no rights to the FlexFund
name or trademarks, and using the FlexFund API is governed by your agreement with FlexFund.
