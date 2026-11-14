"""Source-backed clinic offers and comparable local price ranges."""

from datetime import date
import json
from urllib.parse import urlsplit


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


def price_groups(clinics):
    """Group unrestricted rates only when their verified scopes match exactly.

    A comparison record describes the matching product or technique, billing
    basis, and relevant inclusions. The source may publish an offer without
    establishing these details. Such offers stay visible on the clinic card.
    """
    groups = {}
    for clinic in clinics:
        for offer in clinic["price_offers"]:
            if offer["eligibility"] != "standard" or offer.get("starting"):
                continue
            comparison = offer.get("comparison")
            if not isinstance(comparison, dict):
                continue
            label, unit, scope = (comparison.get(k) for k in ("label", "unit", "scope"))
            if (
                not isinstance(label, str) or not label.strip()
                or not isinstance(unit, str) or not unit.strip()
                or not isinstance(scope, dict) or not scope.get("product") or not scope.get("billing_basis")
            ):
                continue
            key = (label, unit, json.dumps(scope, sort_keys=True))
            rates = groups.setdefault(key, {})
            rates.setdefault(clinic["slug"], set()).add(offer["amount_cents"])

    result = []
    for (label, unit, _), rates in groups.items():
        amounts = [next(iter(rate)) for rate in rates.values() if len(rate) == 1]
        if len(amounts) < 2:
            continue
        low, high = _usd(min(amounts)), _usd(max(amounts))
        result.append({
            "label": label,
            "display": f"{low}–{high} {unit}" if low != high else f"{low} {unit}",
            "clinic_count": len(amounts),
        })
    return result
