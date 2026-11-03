"""Optional FastAPI integration (install with the ``fastapi`` extra).

.. code-block:: python

    app = FastAPI(lifespan=flexfund_lifespan(lambda: AsyncFlexFundClient(...)))

    @app.get("/x")
    async def x(flexfund: FlexFundDep): ...

To combine with a lifespan of your own, nest :func:`flexfund_client_context` inside it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Annotated

try:
    from fastapi import Depends, FastAPI, Request
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    raise ImportError(
        "flexfund.fastapi requires FastAPI. Install it with: pip install 'flexfund-sdk[fastapi]'"
    ) from exc

from flexfund.client import AsyncFlexFundClient

Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


@asynccontextmanager
async def flexfund_client_context(
    factory: Callable[[], AsyncFlexFundClient], app: FastAPI | None = None
) -> AsyncIterator[AsyncFlexFundClient]:
    """Build a client, yield it, and close it on exit.

    If ``app`` is given the client is also stored on ``app.state.flexfund``.
    """
    client = factory()
    try:
        if app is not None:
            app.state.flexfund = client
        yield client
    finally:
        await client.aclose()


def flexfund_lifespan(factory: Callable[[], AsyncFlexFundClient]) -> Lifespan:
    """A FastAPI lifespan that builds the client on startup and closes it on shutdown."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with flexfund_client_context(factory, app):
            yield

    return lifespan


def get_flexfund(request: Request) -> AsyncFlexFundClient:
    """Dependency returning the client stored by :func:`flexfund_lifespan`."""
    client = getattr(request.app.state, "flexfund", None)
    if client is None:
        raise RuntimeError(
            "No FlexFund client on app.state.flexfund; use flexfund_lifespan() or "
            "flexfund_client_context(factory, app)."
        )
    if not isinstance(client, AsyncFlexFundClient):
        raise RuntimeError("app.state.flexfund is not an AsyncFlexFundClient.")
    return client


FlexFundDep = Annotated[AsyncFlexFundClient, Depends(get_flexfund)]
