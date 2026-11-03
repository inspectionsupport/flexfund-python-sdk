# Generated code. Do not edit.

from typing import Annotated, Literal

from flexfund._serde import FlexFundIso8601, FlexFundResponseModel, lenient
from flexfund.enums.third_party_type2 import ThirdPartyType2


class TransactionAgreementSigned(FlexFundResponseModel):
    status: Literal["signed"]
    signer_name: str
    signed_at: FlexFundIso8601 | None

    url: str
    """pdfutil-v2 public URL for a freshly regenerated copy of the signed document (regenerated on
    every fetch — nothing is stored)
    """

    html: str | None
    """the rendered agreement HTML, for inline display — the same document the PDF is generated from,
    without the print stylesheet. Null for a transaction_agreement row still referencing a template
    from before the FlexFund HTML import, which has no HTML body to render.
    """

    third_party_type: Annotated[ThirdPartyType2 | str | None, lenient(ThirdPartyType2)] = None
    card_brand: str | None = None
    card_last_four: str | None = None
