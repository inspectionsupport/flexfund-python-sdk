# Generated code. Do not edit.

from flexfund._serde import FlexFundResponseModel


class ShowAgreementUrlResponse(FlexFundResponseModel):
    agreement_sign_url: str
    """the order's current public signing link — unchanged by this call"""

    signed: bool
    """true when the agreement is already signed, in which case the link opens the signed document
    instead of the signing form
    """
