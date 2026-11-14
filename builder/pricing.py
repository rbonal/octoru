"""Source-backed clinic offers and comparable local price ranges."""

from datetime import date
from urllib.parse import urlsplit


# Services migrated to structured offers. An unreviewed legacy amount for these
# services cannot establish what a clinic actually offers or what a range includes.
STRUCTURED_PRICE_SERVICES = frozenset({"botox", "liposuction"})

_ELIGIBILITY = {
    "standard": "",
    "member": "Members only",
    "new_patient": "New patients only",
    "add_on": "Add-on only",
}


def _usd(cents):
    dollars, remainder = divmod(cents, 100)
    return f"${dollars:,}.{remainder:02d}" if remainder else f"${dollars:,}"


def current_offers(records, today):
    """Present priced offers only when their source and terms can be shown."""
    offers = []
    for record in records:
        if not isinstance(record, dict):
            continue
        cents = record.get("amount_cents")
        label = record.get("label")
        source = record.get("source_url")
        eligibility = record.get("eligibility")
        if (
            type(cents) is not int
            or cents <= 0
            or not isinstance(label, str)
            or not label.strip()
            or not isinstance(source, str)
            or not isinstance(eligibility, str)
            or eligibility not in _ELIGIBILITY
        ):
            continue
        try:
            url = urlsplit(source)
            checked = date.fromisoformat(record["checked"])
            expiry = date.fromisoformat(record["expires"]) if record.get("expires") else None
        except (KeyError, TypeError, ValueError):
            continue
        if url.scheme != "https" or not url.hostname or checked > today or (expiry and expiry < today):
            continue
        offers.append({
            **record,
            "amount": _usd(cents),
            "eligibility_label": _ELIGIBILITY[eligibility],
        })
    return offers


def price_groups(clinics, treatment):
    """Summarize only unrestricted, source-backed rates for a matched scope."""
    rates = {}
    for clinic in clinics:
        for offer in clinic["price_offers"]:
            if offer["eligibility"] != "standard" or offer.get("starting"):
                continue
            # Only product-specific per-unit Botox charges are comparable in the
            # pilot. Area prices and surgical quotes stay as named offers until
            # their exact coverage and fee inclusions can be compared.
            if (treatment == "botox" and offer.get("product") == "botox-cosmetic"
                    and offer.get("basis") == "per_unit" and offer.get("standard_unit_rate") is True):
                rates.setdefault(clinic["slug"], set()).add(offer["amount_cents"])
    amounts = [next(iter(rate)) for rate in rates.values() if len(rate) == 1]
    if len(amounts) < 2:
        return []
    low, high = _usd(min(amounts)), _usd(max(amounts))
    return [{
        "label": "Standard Botox Cosmetic per-unit rates",
        "display": f"{low}–{high} per unit" if low != high else f"{low} per unit",
        "clinic_count": len(amounts),
    }]
