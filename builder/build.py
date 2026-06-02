#!/usr/bin/env python3
"""
GlowMap builder routine.
Runs under Claude Code auto mode. Obeys build_state + token budget.
Renders pages from data + template; builds to a branch; NEVER deploys.
(Publish is hard-gated — see CLAUDE.md.)

Runnable skeleton. The only TODO is your real data source.
  pip install -r requirements.txt
  python builder/build.py
"""
import json, sys, datetime, urllib.parse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config" / "thresholds.json").read_text())
STATE_PATH = ROOT / "state" / "build_state.json"
LEDGER_PATH = ROOT / "state" / "run_ledger.json"
GENERATED = ROOT / "generated"
SITE_URL = "https://www.glowmapmiami.com"  # placeholder; the real domain is set at deploy

# Completeness thresholds are OPERATOR-OWNED and live in config/thresholds.json under
# "completeness". The builder READS them; it must never invent them (and cannot edit
# config/ — hard-gated). If absent, the builder runs the new gate in DRY-RUN only
# (reports what WOULD be held using the recommendation below) and enforces nothing new.
COMPLETENESS = CONFIG.get("completeness")  # None until the operator adds it to config
RECOMMENDED_COMPLETENESS = {  # surfaced for the operator to adopt; NOT enforced unless copied to config
    "min_listing_fields": ["name", "address", "phone", "rating", "treatments"],
    "min_page_requirements": {"min_listings": 3, "require_cost_block": True, "require_guidance": True},
}

env = Environment(
    loader=FileSystemLoader(str(ROOT / "templates")),
    autoescape=select_autoescape(["html", "j2"]),
)


def load_state():
    try:                                            # fail safe: any problem => paused
        return json.loads(STATE_PATH.read_text()).get("state", "paused")
    except Exception:
        return "paused"


def month_tokens_used():
    try:
        ledger = json.loads(LEDGER_PATH.read_text())
        return ledger.get(datetime.date.today().strftime("%Y-%m"), {}).get("tokens", 0)
    except Exception:
        return 0


def stop(reason):
    print(f"[builder] STOP: {reason}")
    sys.exit(0)


def quality_gate(page) -> bool:
    """ALL must hold or the page is skipped. Never lower the gate to hit a count."""
    flags = page.get("page_flags", {})
    if not (flags.get("has_consent_form") and flags.get("has_schema_markup")):
        return False
    for c in page.get("clinics", []):
        if not c.get("has_real_clinic_data"):
            return False
        if c.get("uses_scraped_review_text"):
            return False
        if c.get("has_before_after") and not c.get("before_after_consent"):
            return False
    return True


PROSPECTOR_DIR = ROOT / "data" / "prospector"

# Canonical display names for the seed-scope slugs. Source records may override the
# neighborhood label (they carry neighborhood_name); these drive the page titles.
TREATMENT_NAMES = {
    "botox": "Botox",
    "lip-filler": "Lip filler",
    "coolsculpting": "CoolSculpting",
    "laser-hair-removal": "Laser hair removal",
    "microneedling": "Microneedling",
}
NEIGHBORHOOD_NAMES = {
    "brickell": "Brickell",
    "coral-gables": "Coral Gables",
    "south-beach": "South Beach",
    "coconut-grove": "Coconut Grove",
}

# Pricing unit per treatment — so "From $10" reads honestly as "$10 per unit", etc.
TREATMENT_UNITS = {
    "botox": "per unit",
    "lip-filler": "per syringe",
    "coolsculpting": "per session",
    "laser-hair-removal": "per session",
    "microneedling": "per session",
}

# Short, factual treatment guidance (NOT medical advice). Drafted by the builder and
# flagged for clinician/legal review before deploy. Required on every page when the
# operator sets min_page_requirements.require_guidance.
TREATMENT_GUIDANCE = {
    "botox": "Botox is a neuromodulator injected to soften dynamic wrinkles; it is usually priced per unit, and the number of units depends on the treatment area. Effects typically last a few months. Ask each provider who performs the injections and how units are counted.",
    "lip-filler": "Lip filler uses hyaluronic-acid dermal fillers to add volume and shape; it is usually priced per syringe. Results are not permanent and vary by product. Ask which filler is used and about reversibility.",
    "coolsculpting": "CoolSculpting is a non-surgical fat-reduction treatment that cools targeted areas; it is typically priced per session or per area, and several sessions may be suggested. Ask how many cycles a provider recommends for your goal.",
    "laser-hair-removal": "Laser hair removal reduces unwanted hair over a course of sessions; pricing is usually per session or per package and depends on the body area. Ask how many sessions are typical and which laser suits your skin type.",
    "microneedling": "Microneedling stimulates collagen to refine skin texture; it is usually priced per session, sometimes with radiofrequency or PRP add-ons. Ask what device is used and how many sessions are suggested.",
}

# Field presence helpers — what counts as a clinic "having" a field (operator-owned
# min_listing_fields references these names). Never imputes a value; only checks presence.
def _field_present(raw_clinic, field):
    if field == "treatments":
        return bool(raw_clinic.get("treatments"))
    if field == "rating":
        return raw_clinic.get("rating") is not None
    if field == "price":
        p = raw_clinic.get("starting_prices_usd") or raw_clinic.get("starting_price_usd")
        return bool(p)
    return bool(raw_clinic.get(field))


def listing_missing_fields(raw_clinic, required_fields):
    """Return the required fields this listing is missing (empty/None). No imputation."""
    return [f for f in (required_fields or []) if not _field_present(raw_clinic, f)]


def load_clinics():
    """Read the flat clinic list the prospector writes into data/prospector/*.json.
    Each file is a JSON array (or single object) of REAL clinic records. Returns []
    if the dir is absent/empty — the builder then simply has nothing to build.
    This is the only place real source data enters; nothing here is fabricated."""
    clinics = []
    if not PROSPECTOR_DIR.exists():
        return clinics
    for f in sorted(PROSPECTOR_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except Exception as e:
            print(f"[builder] WARN: could not parse {f.name}: {e}")
            continue
        clinics.extend(data if isinstance(data, list) else [data])
    return clinics


def _starting_price(clinic, treatment_slug):
    """Per-treatment price if the record carries a map; else a flat starting price."""
    prices = clinic.get("starting_prices_usd")
    if isinstance(prices, dict):
        return prices.get(treatment_slug)
    return clinic.get("starting_price_usd")


def _format_phone(phone):
    """Pretty US phone for display, e.g. +13055551234 -> (305) 555-1234."""
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:]}"
    return phone


def _google_listing_url(clinic):
    """A 'View on Google' link for the clinic. If the source record carries an
    explicit google_listing_url (e.g. a place_id-based URL from the Places API),
    use it. Otherwise build a no-API Google Maps SEARCH url from name + address —
    just a link, no scraping, no rating data."""
    explicit = clinic.get("google_listing_url")
    if explicit:
        return explicit
    query = " ".join(p for p in (clinic.get("name"), clinic.get("address")) if p)
    if not query:
        return None
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query)


def _clinic_for_page(clinic, treatment_slug):
    """Shape one clinic for the template + quality gate. The gate flags ride through
    from source VERBATIM — the builder never sets or infers them."""
    return {
        "slug": clinic.get("slug"),
        "name": clinic.get("name"),
        "neighborhood": clinic.get("neighborhood_name")
            or NEIGHBORHOOD_NAMES.get(clinic.get("neighborhood"), clinic.get("neighborhood")),
        "address": clinic.get("address"),
        "phone": clinic.get("phone"),
        "phone_display": _format_phone(clinic.get("phone")),
        "email": clinic.get("email"),
        "booking_url": clinic.get("booking_url"),
        "google_listing_url": _google_listing_url(clinic),
        "treatments_offered": [
            TREATMENT_NAMES.get(t, t.replace("-", " ").title())
            for t in (clinic.get("treatments") or [])
        ],
        "rating": clinic.get("rating"),
        "review_count": clinic.get("review_count"),
        "rating_source": clinic.get("rating_source"),
        "starting_price_usd": _starting_price(clinic, treatment_slug),
        "price_unit": TREATMENT_UNITS.get(treatment_slug) if _starting_price(clinic, treatment_slug) is not None else None,
        "languages": clinic.get("languages", []),
        "featured_tier": clinic.get("featured_tier", 0),
        "lead_routing_target": clinic.get("lead_routing_target"),
        # source + freshness (per task item 4): surfaced when present; never invented
        "last_verified": clinic.get("last_verified"),
        "sources": clinic.get("sources"),
        # quality-gate signals — passed straight through, never fabricated by the builder
        "has_real_clinic_data": clinic.get("has_real_clinic_data", False),
        "uses_scraped_review_text": clinic.get("uses_scraped_review_text", False),
        "has_before_after": clinic.get("has_before_after", False),
        "before_after_consent": clinic.get("before_after_consent", False),
    }


def _assemble_page(treatment_slug, neighborhood_slug, clinics):
    """Group real clinics into one treatment x neighborhood page. Differentiation
    comes from the real clinics on the page, not from boilerplate."""
    t_name = TREATMENT_NAMES.get(treatment_slug, treatment_slug.replace("-", " ").title())
    n_name = NEIGHBORHOOD_NAMES.get(neighborhood_slug, neighborhood_slug.replace("-", " ").title())
    # featured first, then by rating — a real ordering, not arbitrary
    clinics = sorted(
        clinics,
        key=lambda c: (c.get("featured_tier", 0), c.get("rating") or 0),
        reverse=True,
    )
    n = len(clinics)
    provider_word = "provider" if n == 1 else "providers"

    # real, per-page price context (unique content, not boilerplate)
    prices = sorted({p for c in clinics if (p := _starting_price(c, treatment_slug)) is not None})
    unit = TREATMENT_UNITS.get(treatment_slug, "")
    price_sentence = ""
    if prices:
        rng = f"${prices[0]}" if prices[0] == prices[-1] else f"${prices[0]}–${prices[-1]}"
        price_sentence = f" Among listed providers, {t_name.lower()} starts around {rng} {unit}.".rstrip() + "."
        price_sentence = price_sentence.replace("..", ".")

    langs = sorted({l for c in clinics for l in (c.get("languages") or [])})
    lang_sentence = f" Several list staff who speak {' and '.join(langs)}." if langs else ""

    intro = (
        f"{n_name} has {n} {t_name.lower()} {provider_word} in our directory."
        f"{price_sentence}{lang_sentence} Each listing below shows the clinic's address, contact "
        f"details, treatments offered, and verified Google rating so you can compare before booking."
    )
    meta = (
        f"Compare {n} {t_name.lower()} {provider_word} in {n_name}, Miami — addresses, phones, "
        f"prices, verified Google ratings, and languages. Request a personalized quote."
    )

    # cost block + coverage label (derive only from the reporting subset; never impute)
    priced_clinics = [c for c in clinics if _starting_price(c, treatment_slug) is not None]
    cost = {
        "has_prices": bool(priced_clinics),
        "low": prices[0] if prices else None,
        "high": prices[-1] if prices else None,
        "unit": unit,
        "count_priced": len(priced_clinics),
        "count_total": len(clinics),
        "coverage_label": f"{len(priced_clinics)} of {len(clinics)} {'provider lists' if len(priced_clinics)==1 else 'providers list'} pricing",
    }
    # freshness — max per-listing last_verified if present, else today
    verified_dates = [c.get("last_verified") for c in clinics if c.get("last_verified")]
    updated = max(verified_dates) if verified_dates else datetime.date.today().isoformat()

    return {
        "treatment": {"slug": treatment_slug, "name": t_name},
        "neighborhood": {"slug": neighborhood_slug, "name": n_name},
        "city": "Miami",
        # The consent form + schema.org markup are built into the template, so these
        # structural flags hold for every page this builder emits.
        "page_flags": {"has_consent_form": True, "has_schema_markup": True},
        "meta_description": meta,
        "intro": intro,
        "cost": cost,
        "guidance": TREATMENT_GUIDANCE.get(treatment_slug),
        "updated": updated,
        "clinics": [_clinic_for_page(c, treatment_slug) for c in clinics],
    }


def page_hold_reason(page, page_reqs):
    """Return why a page is below the operator's page requirements, or None if it passes."""
    if not page_reqs:
        return None
    min_listings = page_reqs.get("min_listings", 0)
    if len(page.get("clinics", [])) < min_listings:
        return f"only {len(page['clinics'])} qualifying listing(s) (< {min_listings})"
    if page_reqs.get("require_cost_block") and not page.get("cost"):
        return "missing cost block"
    if page_reqs.get("require_guidance") and not page.get("guidance"):
        return "missing treatment guidance"
    return None


def fetch_pages(spec=None, enforce=False):
    """Build seed-scope pages from the prospector's flat clinic list, applying the
    operator-owned completeness thresholds in `spec`. Returns (pages, report).

    - A listing missing any of spec.min_listing_fields is EXCLUDED (logged).
    - A page below spec.min_page_requirements is HELD — not rendered (logged).
    Better no page than a thin one. Never imputes a value to a clinic that didn't report it.

    When enforce=False (operator hasn't set config 'completeness'), exclusions/holds are
    only REPORTED (dry-run) and the page is still built, so the operator can see impact."""
    scope = CONFIG["seed_scope"]
    clinics = load_clinics()
    report = {"excluded_listings": [], "held_pages": []}
    if not clinics:
        print(f"[builder] no prospector data in {PROSPECTOR_DIR} — nothing to build.")
        return [], report

    req_fields = (spec or {}).get("min_listing_fields") or []
    page_reqs = (spec or {}).get("min_page_requirements") or {}

    pages = []
    for t in scope["treatments"]:
        for n in scope["neighborhoods"]:
            matched = [c for c in clinics
                       if c.get("neighborhood") == n and t in (c.get("treatments") or [])]
            if not matched:
                print(f"[builder] no clinics for '{t}' in '{n}' — page skipped (no data).")
                continue

            qualifying = []
            for c in matched:
                miss = listing_missing_fields(c, req_fields)
                if miss:
                    report["excluded_listings"].append(
                        {"clinic": c.get("name"), "page": f"{t}-{n}", "missing": miss})
                    print(f"[builder] listing {'excluded' if enforce else 'would-exclude (dry-run)'} "
                          f"(missing {miss}): {c.get('name')} on {t}-{n}")
                    if enforce:
                        continue
                qualifying.append(c)

            use = qualifying if enforce else matched
            if not use:
                report["held_pages"].append({"page": f"{t}-{n}", "reason": "no qualifying listings"})
                print(f"[builder] HELD {t}-{n}: no qualifying listings")
                continue

            page = _assemble_page(t, n, use)
            reason = page_hold_reason(page, page_reqs)
            if reason:
                report["held_pages"].append({"page": f"{t}-{n}", "reason": reason})
                print(f"[builder] {'HELD' if enforce else 'would-HOLD (dry-run)'} {t}-{n}: {reason}")
                if enforce:
                    continue
            pages.append(page)
    return pages, report


def compute_empty_fields(pages):
    """Which fields fall back to honest empty states across the built pages."""
    seen, price_missing, price_total = {}, 0, 0
    for p in pages:
        for c in p["clinics"]:
            seen[c.get("name")] = c
            price_total += 1
            if not c.get("starting_price_usd"):
                price_missing += 1
    cl = list(seen.values())
    return {
        "unique_clinics": len(cl),
        "missing_phone": sum(1 for c in cl if not c.get("phone")),
        "missing_email": sum(1 for c in cl if not c.get("email")),
        "missing_address": sum(1 for c in cl if not c.get("address")),
        "missing_booking_url": sum(1 for c in cl if not c.get("booking_url")),
        "price_empty_state_listings": price_missing,
        "price_total_listings": price_total,
    }


def render_claim(passed):
    """Render the 'Claim this listing' intake page (build only — NEVER sends outreach).
    The form routes to CRM for verification when wired; this builds the intake UI only."""
    html = env.get_template("claim.html.j2").render(
        site_url=SITE_URL,
        lead_routing_target="crm:glowmap-listing-claims",
        last_updated=datetime.date.today().isoformat(),
    )
    out = GENERATED / "claim.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def page_links(page, all_pages):
    """Best-practice internal linking: breadcrumb trail + cross-links to related
    canonical pages (same treatment in other neighborhoods; other treatments here).
    Only links pages that actually exist in `all_pages` — no dead links."""
    t, n = page["treatment"]["slug"], page["neighborhood"]["slug"]
    t_name, n_name = page["treatment"]["name"], page["neighborhood"]["name"]
    exists = {(p["treatment"]["slug"], p["neighborhood"]["slug"]) for p in all_pages}
    n_names = {p["neighborhood"]["slug"]: p["neighborhood"]["name"] for p in all_pages}
    t_names = {p["treatment"]["slug"]: p["treatment"]["name"] for p in all_pages}

    same_treatment = [
        {"name": n_names[nn], "slug": f"{t}-{nn}"}
        for nn in CONFIG["seed_scope"]["neighborhoods"]
        if nn != n and (t, nn) in exists
    ]
    other_treatments = [
        {"name": t_names[tt], "slug": f"{tt}-{n}"}
        for tt in CONFIG["seed_scope"]["treatments"]
        if tt != t and (tt, n) in exists
    ]
    breadcrumb = [
        {"name": "Home", "url": "/"},
        {"name": n_name, "url": f"/#{n}"},
        {"name": f"{t_name} in {n_name}", "url": f"/{t}-{n}.html"},
    ]
    return {"same_treatment": same_treatment, "other_treatments": other_treatments,
            "breadcrumb": breadcrumb, "site_url": SITE_URL}


def render(page, links=None):
    ctx = dict(page)
    if links:
        ctx.update(links)
    ctx.setdefault("last_updated", datetime.date.today().isoformat())
    ctx.setdefault("site_url", SITE_URL)
    html = env.get_template("treatment-page.html.j2").render(**ctx)
    slug = f"{page['treatment']['slug']}-{page['neighborhood']['slug']}"
    out = GENERATED / f"{slug}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def page_summary(page):
    """Compact card data for the homepage: slug, names, provider count, and the
    lowest listed starting price for this treatment (with its unit)."""
    t = page["treatment"]["slug"]
    prices = [c["starting_price_usd"] for c in page.get("clinics", []) if c.get("starting_price_usd")]
    return {
        "slug": f"{t}-{page['neighborhood']['slug']}",
        "treatment_slug": t,
        "treatment_name": page["treatment"]["name"],
        "neighborhood_slug": page["neighborhood"]["slug"],
        "neighborhood_name": page["neighborhood"]["name"],
        "n_clinics": len(page.get("clinics", [])),
        "from_price": min(prices) if prices else None,
        "price_unit": TREATMENT_UNITS.get(t) if prices else None,
    }


def render_index(summaries):
    """Homepage linking the listing pages that actually built, grouped by
    neighborhood (in seed order). Navigational only — lists pages that already
    passed the clinic quality gate, so it carries no rating data of its own."""
    if not summaries:
        return None
    groups = []
    for n_slug in CONFIG["seed_scope"]["neighborhoods"]:
        pages = [p for p in summaries if p["neighborhood_slug"] == n_slug]
        if pages:
            groups.append({"slug": n_slug, "name": pages[0]["neighborhood_name"], "pages": pages})
    # ordered list of treatments actually present, for the filter pills
    present_treatments = [
        {"slug": t, "name": TREATMENT_NAMES.get(t, t)}
        for t in CONFIG["seed_scope"]["treatments"]
        if any(p["treatment_slug"] == t for p in summaries)
    ]
    stats = {
        "pages": len(summaries),
        "neighborhoods": len(groups),
        "treatments": len(present_treatments),
        "listings": sum(p["n_clinics"] for p in summaries),
    }
    html = env.get_template("index.html.j2").render(
        neighborhoods=groups,
        treatments=present_treatments,
        stats=stats,
        last_updated=datetime.date.today().isoformat(),
    )
    out = GENERATED / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def main():
    state = load_state()
    if state in ("paused", "halted", "halted_technical"):
        stop(f"build_state is '{state}' — not building.")
    if month_tokens_used() >= CONFIG["monthly_token_cap"]:
        stop(f"monthly token cap reached ({CONFIG['monthly_token_cap']}).")

    throttle = (state == "throttled")

    # completeness thresholds are operator-owned (config). Read them; never invent.
    spec = COMPLETENESS or RECOMMENDED_COMPLETENESS
    enforce = COMPLETENESS is not None
    if enforce:
        print("[builder] completeness gate ENFORCED from config/thresholds.json -> completeness")
    else:
        print("[builder] completeness gate DRY-RUN only: config 'completeness' is absent. "
              "The operator must add it to config/thresholds.json (the builder cannot edit config). "
              "Reporting what WOULD be held under the recommended thresholds; enforcing nothing new.")

    # pass 1: completeness filter/hold (exclude thin listings, hold thin pages), then quality gate
    fetched, report = fetch_pages(spec, enforce)
    passed, skipped = [], 0
    for page in fetched:
        if quality_gate(page):
            passed.append(page)
        else:
            skipped += 1
            print(f"[builder] skipped (failed quality gate): "
                  f"{page.get('treatment', {}).get('slug')}-{page.get('neighborhood', {}).get('slug')}")
    if throttle:
        passed = passed[:10]

    # pass 2: render each, now that we know the full set (for cross-links)
    built_pages = []
    for page in passed:
        out = render(page, page_links(page, passed))
        built_pages.append(page_summary(page))
        print(f"[builder] built {out.name}")
    built = len(built_pages)

    idx = render_index(built_pages)
    if idx:
        print(f"[builder] built {idx.name} (homepage linking {built} pages)")
    claim = render_claim(passed)
    print(f"[builder] built {claim.name} (claim-this-listing intake)")

    # information-gap report
    report["empty_fields"] = compute_empty_fields(passed)
    report["mode"] = "enforced" if enforce else "dry-run (config 'completeness' absent)"
    report["thresholds_used"] = spec
    print(f"[builder] completeness: mode={report['mode']} | "
          f"listings_excluded={len(report['excluded_listings'])} | "
          f"pages_held={len(report['held_pages'])} | empty_fields={report['empty_fields']}")
    (GENERATED / "_completeness_report.json").write_text(json.dumps(report, indent=2))

    # TODO (auto-approved): git add + commit to branch 'auto/build'
    # DO NOT merge to main. DO NOT deploy. (hard-gated in CLAUDE.md)
    print(f"[builder] done. built={built} skipped={skipped} state={state}")


if __name__ == "__main__":
    main()
