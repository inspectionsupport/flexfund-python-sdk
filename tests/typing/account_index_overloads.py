"""Static checks only: mypy verifies these ``assert_type`` calls; pytest does not collect them.

``account.index()`` returns a different shape depending on ``detailed``, and the overloads must
let a type checker see which. If this file stops type-checking, the overloads regressed to ``Any``.
"""

from __future__ import annotations

from typing import assert_type

from flexfund import AsyncFlexFundClient, FlexFundClient
from flexfund.models.account_detailed import AccountDetailed
from flexfund.models.account_summary import AccountSummary


def sync_checks(client: FlexFundClient, flag: bool) -> None:
    assert_type(client.account.index(detailed=True), list[AccountDetailed])
    assert_type(client.account.index(), list[AccountSummary])
    assert_type(client.account.index(detailed=False), list[AccountSummary])
    assert_type(client.account.index(detailed=None), list[AccountSummary])
    # A flag the checker cannot see could be either, so the honest type is the union.
    assert_type(client.account.index(detailed=flag), list[AccountDetailed] | list[AccountSummary])


async def async_checks(client: AsyncFlexFundClient, flag: bool) -> None:
    assert_type(await client.account.index(detailed=True), list[AccountDetailed])
    assert_type(await client.account.index(), list[AccountSummary])
    assert_type(await client.account.index(detailed=False), list[AccountSummary])
    assert_type(
        await client.account.index(detailed=flag), list[AccountDetailed] | list[AccountSummary]
    )
