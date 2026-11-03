"""Every generated resource module must be reachable from both clients.

The PHP SDK's hand-written client silently lacked four accessors; here the accessors are
generated, and this pins that no resource module is left without one.
"""

import pkgutil

import pytest

from flexfund import AsyncFlexFundClient, FlexFundClient, resources


def _resource_modules() -> list[str]:
    return sorted(m.name for m in pkgutil.iter_modules(resources.__path__))


def test_there_are_resources() -> None:
    assert _resource_modules() == ["account", "transaction", "transaction_agreement"]


@pytest.mark.parametrize("name", _resource_modules())
def test_sync_client_exposes_resource(name: str) -> None:
    client = FlexFundClient(
        client_id="test-client-id",
        client_secret="test-client-secret",
        scopes=[],
        base_url="https://flexfund.test",
    )
    try:
        resource = getattr(client, name)
        assert type(resource).__name__.endswith("Resource")
        assert not type(resource).__name__.startswith("Async")
    finally:
        client.close()


@pytest.mark.parametrize("name", _resource_modules())
async def test_async_client_exposes_resource(name: str) -> None:
    client = AsyncFlexFundClient(
        client_id="test-client-id",
        client_secret="test-client-secret",
        scopes=[],
        base_url="https://flexfund.test",
    )
    try:
        resource = getattr(client, name)
        assert type(resource).__name__.startswith("Async")
    finally:
        await client.aclose()
