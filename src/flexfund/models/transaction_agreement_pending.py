# Generated code. Do not edit.

from typing import Literal

from flexfund._serde import FlexFundResponseModel
from flexfund.models.agreement_client import AgreementClient


class TransactionAgreementPending(FlexFundResponseModel):
    status: Literal["pending"]

    url: str | None
    """Always NULL for a pending agreement, for every template kind: no document is produced until
    signing. Until the form is filled in there is only the template with empty merge fields, and the
    signing page shows no preview, so building one would be two external calls for something nobody
    sees.
    """

    has_signing_link: bool
    """whether a public signing link has already been issued for this order. A boolean, never the token
    itself — the token is the only thing guarding the public signing route. The transaction page
    uses this to warn before regenerating a link the client may already have been sent.
    """

    card_tokenizer_url: str
    """CardSecure hosted-tokenizer URL for the signing form's iframe. Resolved server-side so the
    origin the browser tokenizes against and the credentials the $0.01 verification auth uses can
    never disagree — a UAT token presented to the production merchant is an invisible decline.
    """

    client: AgreementClient
    """what the order already knows about the client, so the signing form can prefill instead of asking
    them to retype it. Any field may be null. Not a new disclosure on the public token route: the
    same values are merged into the agreement document this endpoint already returns.
    """

    html: str | None
    """the rendered agreement HTML, for inline display — the same document the PDF is generated from,
    without the print stylesheet. Null for a transaction_agreement row still referencing a template
    from before the FlexFund HTML import, which has no HTML body to render.
    """

    total_fee: str
    """the order's Total Fee, preformatted for display (e.g. "$734.99"). The signing form prints it in
    the closing-cost terms above the signature; it is the same number and formatting the agreement
    document itself carries as %inspectiontotalfee%, since the two appear on the same page.
    """

    inspection_date: str | None
    """the order's order_date, as a bare Y-m-d calendar date (already in the order's own timezone —
    order_date is naive local wall-clock, not UTC). No new disclosure on the public token route: the
    signer is the client whose inspection this is.
    """
