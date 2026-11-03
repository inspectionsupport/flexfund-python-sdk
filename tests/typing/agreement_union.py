"""Static checks only: mypy verifies these; pytest does not collect them.

``transaction_agreement.show()`` is a union told apart by ``status``, so checking ``status`` must
narrow it to one model. If this stops type-checking, the response regressed to ``Any``.
"""

from __future__ import annotations

from typing import assert_type

from flexfund import AsyncFlexFundClient, FlexFundClient
from flexfund.models.transaction_agreement_pending import TransactionAgreementPending
from flexfund.models.transaction_agreement_signed import TransactionAgreementSigned


def sync_checks(client: FlexFundClient) -> None:
    agreement = client.transaction_agreement.show("order-uuid")
    assert_type(agreement, TransactionAgreementPending | TransactionAgreementSigned)

    if agreement.status == "signed":
        assert_type(agreement, TransactionAgreementSigned)
        assert_type(agreement.signer_name, str)
    else:
        assert_type(agreement, TransactionAgreementPending)
        assert_type(agreement.has_signing_link, bool)


async def async_checks(client: AsyncFlexFundClient) -> None:
    agreement = await client.transaction_agreement.show("order-uuid")
    assert_type(agreement, TransactionAgreementPending | TransactionAgreementSigned)

    if agreement.status == "pending":
        assert_type(agreement, TransactionAgreementPending)
    else:
        assert_type(agreement, TransactionAgreementSigned)
