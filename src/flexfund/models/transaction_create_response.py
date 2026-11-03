# Generated code. Do not edit.

from typing import Annotated

from flexfund._serde import FlexFundResponseModel, lenient
from flexfund.enums.agreement_email import AgreementEmail


class TransactionCreateResponse(FlexFundResponseModel):
    uuid: str
    agreement_sign_url: str

    agreement_email: Annotated[AgreementEmail | str, lenient(AgreementEmail)]
    """whether the client was emailed their signing link; the order is created either way"""
