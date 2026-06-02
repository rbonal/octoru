#!/usr/bin/env python3
"""
GlowMap builder routine.
Runs under Claude Code auto mode. Obeys build_state + token budget.
Renders pages from data + template; builds to a branch; NEVER deploys.
(Publish is hard-gated — see CLAUDE.md.)

Geo hierarchy: state > county > city > treatment, read from the OPERATOR-OWNED
config seed_scope.geo tree (builder reads, never invents, cannot edit config).
Back-compat: if config has only the flat seed_scope.neighborhoods, those are treated
as active cities in Miami-Dade, Florida.
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

# Completeness thresholds are OPERATOR-OWNED (config/thresholds.json -> "completeness").
# Builder READS them; never invents them; cannot edit config (hard-gated). Absent -> DRY-RUN.
COMPLETENESS = CONFIG.get("completeness")
RECOMMENDED_COMPLETENESS = {
    "min_listing_fields": ["name", "address", "phone", "rating", "treatments"],
    "min_page_requirements": {"min_listings": 3, "require_cost_block": True, "require_guidance": True},
}

# Monetization: flat placement only. Revenue is never tied to per-patient/per-inquiry
# value. See data/monetization_policy.json for the full model.
# Slot cap: max featured listings per page (prevents all-paid pages). Operator can set
# completeness.max_featured_per_page in config; defaults to 3.
MAX_FEATURED_PER_PAGE = int((COMPLETENESS or {}).get("max_featured_per_page", 3))

# Place taxonomy: loaded from data/places.json (operator-owned).
# Provides place type, parent_place for rollup, lat/lng for geolocation.
_PLACES_PATH = ROOT / "data" / "places.json"
try:
    _PLACES_RAW = [p for p in json.loads(_PLACES_PATH.read_text()) if not p.get("_comment")]
except Exception:
    _PLACES_RAW = []
PLACES_BY_SLUG = {p["slug"]: p for p in _PLACES_RAW}

def _place_type(slug):
    """Returns the type ('municipality'|'neighborhood'|'cdp') for a place slug, or None."""
    return PLACES_BY_SLUG.get(slug, {}).get("type")

def _parent_slug(slug):
    """Returns the parent_place slug for a neighborhood/CDP, or None."""
    return PLACES_BY_SLUG.get(slug, {}).get("parent_place")

env = Environment(
    loader=FileSystemLoader(str(ROOT / "templates")),
    autoescape=select_autoescape(["html", "j2"]),
)

PROSPECTOR_DIR = ROOT / "data" / "prospector"

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
TREATMENT_UNITS = {
    "botox": "per unit",
    "lip-filler": "per syringe",
    "coolsculpting": "per session",
    "laser-hair-removal": "per session",
    "microneedling": "per session",
}
TREATMENT_GUIDANCE = {
    "botox": "Botox is a neuromodulator injected to soften dynamic wrinkles; it is usually priced per unit, and the number of units depends on the treatment area. Effects typically last a few months. Ask each provider who performs the injections and how units are counted.",
    "lip-filler": "Lip filler uses hyaluronic-acid dermal fillers to add volume and shape; it is usually priced per syringe. Results are not permanent and vary by product. Ask which filler is used and about reversibility.",
    "coolsculpting": "CoolSculpting is a non-surgical fat-reduction treatment that cools targeted areas; it is typically priced per session or per area, and several sessions may be suggested. Ask how many cycles a provider recommends for your goal.",
    "laser-hair-removal": "Laser hair removal reduces unwanted hair over a course of sessions; pricing is usually per session or per package and depends on the body area. Ask how many sessions are typical and which laser suits your skin type.",
    "microneedling": "Microneedling stimulates collagen to refine skin texture; it is usually priced per session, sometimes with radiofrequency or PRP add-ons. Ask what device is used and how many sessions are suggested.",
}

# Short factual treatment blurbs for the homepage cards (not pricing — pricing is real-data only).
TREATMENT_DESC = {
    "botox": "Wrinkle-relaxing injections, priced per unit.",
    "lip-filler": "Hyaluronic-acid lip enhancement, priced per syringe.",
    "coolsculpting": "Non-invasive fat reduction, priced per area.",
    "laser-hair-removal": "Multi-session hair reduction, priced by area.",
    "microneedling": "Collagen-induction skin treatment, per session.",
}

# City centroids for geolocation — sourced from data/places.json (operator-owned taxonomy).
# Falls back to empty if places.json is absent; the build never invents clinic data from these.
CITY_LATLNG = {
    p["slug"]: (p["lat"], p["lng"])
    for p in _PLACES_RAW
    if p.get("lat") and p.get("lng")
}


def treatment_cards(all_clinics):
    """Homepage treatment cards. 'Typical from' price is computed from REAL listing prices;
    treatments without enough real data get the honest empty state (no placeholder $)."""
    cards = []
    for t in CONFIG["seed_scope"]["treatments"]:
        vals = sorted({p for c in all_clinics if (p := _starting_price(c, t)) is not None})
        unit = TREATMENT_UNITS.get(t, "")
        if len(vals) >= 2:
            disp = f"${vals[0]}–${vals[-1]} {unit}".strip()
        elif len(vals) == 1:
            disp = f"from ${vals[0]} {unit}".strip()
        else:
            disp = None   # honest empty state -> template renders "Varies"
        cards.append({"slug": t, "name": TREATMENT_NAMES.get(t, t),
                      "desc": TREATMENT_DESC.get(t, ""), "from_display": disp})
    return cards


# ----------------------------------------------------------------------------------
# Geographic hierarchy: state > county > city (OPERATOR-OWNED in config seed_scope.geo)
# ----------------------------------------------------------------------------------
# City -> county map (so a flat seed_scope.neighborhoods list still gets correct counties
# when the operator hasn't supplied a full seed_scope.geo tree). Florida only for now.
CITY_COUNTY = {
    # Miami-Dade
    "aventura": "miami-dade", "bal-harbour": "miami-dade", "brickell": "miami-dade",
    "coconut-grove": "miami-dade", "coral-gables": "miami-dade", "doral": "miami-dade",
    "hialeah": "miami-dade", "homestead": "miami-dade", "kendall": "miami-dade",
    "key-biscayne": "miami-dade", "miami-lakes": "miami-dade", "miami-springs": "miami-dade",
    "midtown": "miami-dade", "north-miami": "miami-dade", "palmetto-bay": "miami-dade",
    "pinecrest": "miami-dade", "south-beach": "miami-dade", "sunny-isles-beach": "miami-dade",
    "surfside": "miami-dade",
    # Broward
    "coconut-creek": "broward", "cooper-city": "broward", "coral-springs": "broward",
    "dania-beach": "broward", "davie": "broward", "deerfield-beach": "broward",
    "fort-lauderdale": "broward", "hallandale-beach": "broward", "hollywood": "broward",
    "lighthouse-point": "broward", "margate": "broward", "miramar": "broward",
    "oakland-park": "broward", "parkland": "broward", "pembroke-pines": "broward",
    "plantation": "broward", "pompano-beach": "broward", "sunrise": "broward", "weston": "broward",
    # Palm Beach
    "boca-raton": "palm-beach", "west-palm-beach": "palm-beach",
    "delray-beach": "palm-beach", "palm-beach-gardens": "palm-beach",
    "jupiter": "palm-beach", "wellington": "palm-beach", "boynton-beach": "palm-beach",
    "north-palm-beach": "palm-beach", "royal-palm-beach": "palm-beach",
    "lake-worth-beach": "palm-beach", "greenacres": "palm-beach", "palm-beach": "palm-beach",
}
COUNTY_NAMES = {"miami-dade": "Miami-Dade", "broward": "Broward", "palm-beach": "Palm Beach"}


def _legacy_geo():
    """No seed_scope.geo -> derive a CORRECT state/county/city tree from the flat
    'neighborhoods' list using CITY_COUNTY (unknown cities default to Miami-Dade)."""
    geo = {"fl": {"name": "Florida", "abbr": "FL", "status": "active", "counties": {}}}
    for c in CONFIG["seed_scope"].get("neighborhoods", []):
        county = CITY_COUNTY.get(c, "miami-dade")
        cc = geo["fl"]["counties"].setdefault(
            county, {"name": COUNTY_NAMES.get(county, county.replace("-", " ").title()),
                     "status": "active", "cities": {}})
        cc["cities"][c] = {"name": NEIGHBORHOOD_NAMES.get(c, c.replace("-", " ").title()), "status": "active"}
    return geo


GEO = CONFIG["seed_scope"].get("geo") or _legacy_geo()


def _is_active(node):
    return (node or {}).get("status", "active") == "active"


def active_markets():
    """Every fully-active state > county > city chain, as flat market dicts."""
    out = []
    for s_slug, s in GEO.items():
        if not _is_active(s):
            continue
        for c_slug, c in (s.get("counties") or {}).items():
            if not _is_active(c):
                continue
            for city_slug, city in (c.get("cities") or {}).items():
                if not _is_active(city):
                    continue
                out.append({
                    "state": s_slug, "state_name": s.get("name", s_slug),
                    "state_abbr": s.get("abbr", s_slug.upper()),
                    "county": c_slug, "county_name": c.get("name", c_slug),
                    "city": city_slug, "city_name": city.get("name", city_slug),
                })
    return out


def page_path(market, treatment_slug):
    return f"{market['state']}/{market['county']}/{market['city']}/{treatment_slug}"


def page_url(market, treatment_slug):
    return f"/{page_path(market, treatment_slug)}/"


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


def _field_present(raw_clinic, field):
    if field == "treatments":
        return bool(raw_clinic.get("treatments"))
    if field == "rating":
        return raw_clinic.get("rating") is not None
    if field == "price":
        return bool(raw_clinic.get("starting_prices_usd") or raw_clinic.get("starting_price_usd"))
    return bool(raw_clinic.get(field))


def listing_missing_fields(raw_clinic, required_fields):
    """Required fields this listing is missing (empty/None). No imputation."""
    return [f for f in (required_fields or []) if not _field_present(raw_clinic, f)]


def load_clinics():
    """Read the flat clinic list the prospector writes into data/prospector/*.json.
    Real records only; nothing fabricated. Returns [] if absent/empty."""
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
    prices = clinic.get("starting_prices_usd")
    if isinstance(prices, dict):
        return prices.get(treatment_slug)
    return clinic.get("starting_price_usd")


def _format_phone(phone):
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:]}"
    return phone


def _google_listing_url(clinic):
    explicit = clinic.get("google_listing_url")
    if explicit:
        return explicit
    query = " ".join(p for p in (clinic.get("name"), clinic.get("address")) if p)
    if not query:
        return None
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query)


def _clinic_for_page(clinic, treatment_slug):
    """Shape one clinic for the template + quality gate. Gate flags ride through verbatim."""
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
        # Flat-placement monetization fields (all operator-set, never builder-inferred).
        # featured_tier > 0 = paid flat placement; never tied to per-patient value.
        "featured_tier": clinic.get("featured_tier", 0),
        # campaigns_prospect: flag routes to Bonalta Campaigns CRM pipeline (stub).
        # Triggered by placement purchase, NOT lead count.
        "campaigns_prospect": bool(clinic.get("campaigns_prospect", False)),
        # placement_tier: null=organic; "standard"|"premium"=flat placement subscriber.
        "placement_tier": clinic.get("placement_tier"),
        # sponsored: True means all outbound links from this clinic must carry rel="sponsored".
        "sponsored": bool(clinic.get("featured_tier", 0) or clinic.get("placement_tier")),
        # Free inquiry routing: booking_url and phone are always free for patients.
        # The lead form forwards inquiries to the clinic at no charge — see monetization_policy.json.
        "last_verified": clinic.get("last_verified"),
        "sources": clinic.get("sources"),
        "has_real_clinic_data": clinic.get("has_real_clinic_data", False),
        "uses_scraped_review_text": clinic.get("uses_scraped_review_text", False),
        "has_before_after": clinic.get("has_before_after", False),
        "before_after_consent": clinic.get("before_after_consent", False),
    }


def _assemble_page(treatment_slug, market, clinics):
    """Group real clinics into one treatment x city page. Differentiation comes from
    the real clinics + market-specific context, not boilerplate."""
    t_name = TREATMENT_NAMES.get(treatment_slug, treatment_slug.replace("-", " ").title())
    city_name = market["city_name"]
    clinics = sorted(clinics, key=lambda c: (c.get("featured_tier", 0), c.get("rating") or 0), reverse=True)
    # Slot cap: limit paid featured listings so pages never go all-paid. Any featured clinic
    # beyond MAX_FEATURED_PER_PAGE is demoted to organic (featured_tier=0) on THIS page only —
    # the source record is NOT changed.
    featured_count = 0
    capped = []
    for c in clinics:
        if c.get("featured_tier", 0) > 0:
            if featured_count < MAX_FEATURED_PER_PAGE:
                featured_count += 1
                capped.append(c)
            else:
                capped.append({**c, "featured_tier": 0, "sponsored": bool(c.get("placement_tier"))})
        else:
            capped.append(c)
    clinics = capped
    n = len(clinics)
    provider_word = "provider" if n == 1 else "providers"

    prices = sorted({p for c in clinics if (p := _starting_price(c, treatment_slug)) is not None})
    unit = TREATMENT_UNITS.get(treatment_slug, "")
    price_sentence = ""
    if prices:
        rng = f"${prices[0]}" if prices[0] == prices[-1] else f"${prices[0]}–${prices[-1]}"
        price_sentence = f" Among listed providers, {t_name.lower()} starts around {rng} {unit}.".replace("..", ".")

    langs = sorted({l for c in clinics for l in (c.get("languages") or [])})
    lang_sentence = f" Several list staff who speak {' and '.join(langs)}." if langs else ""

    intro = (
        f"{city_name} ({market['county_name']}, {market['state_abbr']}) has {n} {t_name.lower()} "
        f"{provider_word} in our directory.{price_sentence}{lang_sentence} Each listing below shows the "
        f"clinic's address, contact details, treatments offered, and verified Google rating so you can compare before booking."
    )
    meta = (
        f"Compare {n} {t_name.lower()} {provider_word} in {city_name}, {market['state_abbr']} — addresses, "
        f"phones, prices, verified Google ratings, and languages. Request a personalized quote."
    )

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
    verified_dates = [c.get("last_verified") for c in clinics if c.get("last_verified")]
    updated = max(verified_dates) if verified_dates else datetime.date.today().isoformat()

    return {
        "treatment": {"slug": treatment_slug, "name": t_name},
        "neighborhood": {"slug": market["city"], "name": city_name},   # template compat: city
        "city": market["state_abbr"],                                  # trailing region in H1
        "geo": market,
        "path": page_path(market, treatment_slug),
        "page_flags": {"has_consent_form": True, "has_schema_markup": True},
        "meta_description": meta,
        "intro": intro,
        "cost": cost,
        "guidance": TREATMENT_GUIDANCE.get(treatment_slug),
        "updated": updated,
        "clinics": [_clinic_for_page(c, treatment_slug) for c in clinics],
    }


def _clinic_in_market(clinic, market):
    """A clinic belongs to a market if its city slug matches; county/state, if the record
    carries them, must also match (future-proof disambiguation for national data)."""
    if clinic.get("neighborhood") != market["city"]:
        return False
    if clinic.get("county") and clinic["county"] != market["county"]:
        return False
    if clinic.get("state") and clinic["state"] != market["state"]:
        return False
    return True


def page_hold_reason(page, page_reqs):
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
    """Build treatment x place pages, applying completeness thresholds and place-taxonomy
    rollup. Returns (pages, report).

    Place taxonomy (data/places.json):
    - A clinic appears at its MOST SPECIFIC qualifying place (neighborhood > CDP > municipality).
    - De-duplication: once a clinic is assigned to a neighborhood/CDP page, it is NOT included
      on the parent municipality page (prevents the same clinic appearing on both Brickell and
      Miami pages).
    - Rollup: if a neighborhood/CDP treatment page is below min_page_requirements AND the place
      has a parent_place, its qualifying clinics are rolled up to the parent place. The thin
      neighborhood page is NOT built; the parent page gains those clinics.

    Listing below min_listing_fields is excluded; page below min_page_requirements is HELD
    (unless rollup to parent is possible). Dry-run (enforce=False) reports only."""
    clinics = load_clinics()
    report = {
        "excluded_listings": [], "held_pages": [],
        "rolled_up": [],   # {clinic, from_place, to_place, treatment}
        "deduped": [],     # {clinic, kept_at, not_shown_at}
    }
    if not clinics:
        print(f"[builder] no prospector data in {PROSPECTOR_DIR} — nothing to build.")
        return [], report

    req_fields = (spec or {}).get("min_listing_fields") or []
    page_reqs = (spec or {}).get("min_page_requirements") or {}
    min_listings = page_reqs.get("min_listings", 0)
    treatments = CONFIG["seed_scope"]["treatments"]

    # Step 1: qualify clinics per market (apply field exclusions).
    def _qualify(matched, label):
        ok, excl = [], []
        for c in matched:
            miss = listing_missing_fields(c, req_fields)
            if miss:
                report["excluded_listings"].append({"clinic": c.get("name"), "page": label, "missing": miss})
                print(f"[builder] listing {'excluded' if enforce else 'would-exclude (dry-run)'} "
                      f"(missing {miss}): {c.get('name')} on {label}")
                excl.append(c)
            else:
                ok.append(c)
        return ok if enforce else matched  # dry-run: use all

    # Step 2: collect rollup pools keyed by (parent_slug, county, state, treatment).
    rollup_pool = {}   # (parent_city, county, state, treatment) -> [clinics]
    # Track which clinic slugs have been "claimed" by a specific place (for de-dup).
    claimed = {}       # clinic_slug -> city_slug (the place that will show this clinic)

    pages = []
    markets = list(active_markets())

    # First pass: process neighborhoods/CDPs to see what rolls up.
    for market in markets:
        city = market["city"]
        place_type = _place_type(city)
        parent = _parent_slug(city)
        is_child = place_type in ("neighborhood", "cdp") and parent

        for t in treatments:
            matched = [c for c in clinics if _clinic_in_market(c, market) and t in (c.get("treatments") or [])]
            if not matched:
                continue
            label = f"{t}@{market['state']}/{market['county']}/{city}"
            use = _qualify(matched, label)
            if not use:
                continue
            page = _assemble_page(t, market, use)
            reason = page_hold_reason(page, page_reqs) if enforce else None
            # For dry-run without enforce, only roll up if the page would be GENUINELY thin.
            would_be_thin = len(use) < min_listings if min_listings else False

            if is_child and (reason or would_be_thin):
                # Roll up to parent instead of shipping a thin neighborhood page.
                key = (parent, market["county"], market["state"], t)
                rollup_pool.setdefault(key, []).extend(use)
                for c in use:
                    slug = c.get("slug") or c.get("name")
                    report["rolled_up"].append({
                        "clinic": c.get("name"), "from_place": city,
                        "to_place": parent, "treatment": t
                    })
                    claimed[slug] = parent  # will appear on parent, not on city page
                reason_str = reason or f"thin ({len(use)} < {min_listings})"
                report["held_pages"].append({"page": label, "reason": f"rolled up to {parent}: {reason_str}"})
                print(f"[builder] {'HOLD→rollup' if enforce else 'would-HOLD→rollup (dry-run)'} {label}: rolled to {parent}")
            else:
                if reason:
                    report["held_pages"].append({"page": label, "reason": reason})
                    print(f"[builder] {'HELD' if enforce else 'would-HOLD (dry-run)'} {label}: {reason}")
                    if enforce:
                        continue
                # Claim these clinics at this specific place.
                for c in use:
                    slug = c.get("slug") or c.get("name")
                    if slug not in claimed:
                        claimed[slug] = city
                pages.append(page)

    # Ensure every parent place that received rolled-up clinics exists as a market.
    # Parent places (e.g. "miami", "miami-beach") may not be in the config's neighborhoods
    # list; we synthesise a market entry for them from places.json so rollup pages build.
    existing_cities = {m["city"] for m in markets}
    for (parent_city, county, state, _t) in rollup_pool:
        if parent_city not in existing_cities:
            p_data = PLACES_BY_SLUG.get(parent_city, {})
            markets.append({
                "state": state, "state_name": "Florida",
                "state_abbr": state.upper() if len(state) <= 3 else "FL",
                "county": county,
                "county_name": COUNTY_NAMES.get(county, county.replace("-", " ").title()),
                "city": parent_city,
                "city_name": p_data.get("name", parent_city.replace("-", " ").title()),
            })
            existing_cities.add(parent_city)
            print(f"[builder] activated rollup target: {parent_city} (received clinics from children)")

    # Second pass: municipality pages. Only include clinics NOT already claimed by a child place.
    for market in markets:
        city = market["city"]
        place_type = _place_type(city)
        is_parent = place_type == "municipality"
        if not is_parent:
            continue

        for t in treatments:
            # Base clinics: directly assigned to this municipality.
            direct = [c for c in clinics if _clinic_in_market(c, market) and t in (c.get("treatments") or [])]
            # Add any rolled-up clinics from child places.
            rolled = rollup_pool.get((city, market["county"], market["state"], t), [])
            for c in rolled:
                slug = c.get("slug") or c.get("name")
                report["rolled_up"]  # already recorded above

            # De-dup: exclude direct clinics already claimed by a child place.
            deduped_direct = []
            for c in direct:
                slug = c.get("slug") or c.get("name")
                if claimed.get(slug, city) != city:
                    # Claimed by a child neighborhood — skip from municipality page.
                    report["deduped"].append({
                        "clinic": c.get("name"), "kept_at": claimed[slug], "not_shown_at": city
                    })
                    print(f"[builder] dedup: {c.get('name')} kept at {claimed[slug]}, not shown at {city}")
                else:
                    deduped_direct.append(c)

            all_clinics = deduped_direct + rolled
            if not all_clinics:
                continue
            label = f"{t}@{market['state']}/{market['county']}/{city}"
            use = _qualify(all_clinics, label)
            if not use:
                continue
            page = _assemble_page(t, market, use)
            reason = page_hold_reason(page, page_reqs) if enforce else None
            if reason:
                report["held_pages"].append({"page": label, "reason": reason})
                print(f"[builder] {'HELD' if enforce else 'would-HOLD (dry-run)'} {label}: {reason}")
                if enforce:
                    continue
            for c in use:
                slug = c.get("slug") or c.get("name")
                if slug not in claimed:
                    claimed[slug] = city
            pages.append(page)

    return pages, report


def compute_empty_fields(pages):
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


def page_summary(page):
    m = page["geo"]
    t = page["treatment"]["slug"]
    prices = [c["starting_price_usd"] for c in page.get("clinics", []) if c.get("starting_price_usd")]
    return {
        "treatment_slug": t, "treatment_name": page["treatment"]["name"],
        "state": m["state"], "state_name": m["state_name"], "state_abbr": m["state_abbr"],
        "county": m["county"], "county_name": m["county_name"],
        "city": m["city"], "city_name": m["city_name"],
        "url": page_url(m, t),
        "n_clinics": len(page.get("clinics", [])),
        "from_price": min(prices) if prices else None,
        "price_unit": TREATMENT_UNITS.get(t) if prices else None,
    }


def page_links(page, all_pages):
    """Breadcrumb (Home > State > County > City > Treatment) + cross-links to related
    canonical pages (same treatment in sibling cities; other treatments in this city)."""
    m = page["geo"]
    t = page["treatment"]["slug"]
    t_name = page["treatment"]["name"]
    exists = {(p["geo"]["state"], p["geo"]["county"], p["geo"]["city"], p["treatment"]["slug"]) for p in all_pages}
    tnames = {p["treatment"]["slug"]: p["treatment"]["name"] for p in all_pages}
    cnames = {(p["geo"]["state"], p["geo"]["county"], p["geo"]["city"]): p["geo"]["city_name"] for p in all_pages}

    same_treatment = []
    for (st, co, ci, tr) in sorted(exists):
        if tr == t and co == m["county"] and ci != m["city"]:
            same_treatment.append({"name": cnames[(st, co, ci)], "url": f"/{st}/{co}/{ci}/{tr}/"})
    other_treatments = []
    for tr in CONFIG["seed_scope"]["treatments"]:
        if tr != t and (m["state"], m["county"], m["city"], tr) in exists:
            other_treatments.append({"name": tnames[tr], "url": f"/{m['state']}/{m['county']}/{m['city']}/{tr}/"})

    breadcrumb = [
        {"name": "Home", "url": "/"},
        {"name": m["state_name"], "url": f"/{m['state']}/"},
        {"name": m["county_name"], "url": f"/{m['state']}/{m['county']}/"},
        {"name": m["city_name"], "url": f"/{m['state']}/{m['county']}/{m['city']}/"},
        {"name": f"{t_name} in {m['city_name']}", "url": page_url(m, t)},
    ]
    return {"same_treatment": same_treatment, "other_treatments": other_treatments,
            "breadcrumb": breadcrumb, "site_url": SITE_URL,
            "city_label": f"{m['city_name']}, {m['state_abbr']}"}


def _write(path_rel, html):
    out = GENERATED / path_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def render(page, links=None):
    ctx = dict(page)
    if links:
        ctx.update(links)
    ctx.setdefault("last_updated", datetime.date.today().isoformat())
    ctx.setdefault("site_url", SITE_URL)
    html = env.get_template("treatment-page.html.j2").render(**ctx)
    return _write(f"{page['path']}/index.html", html)


def render_hub(title, subtitle, breadcrumb, cards, rel_path, intro=None):
    html = env.get_template("hub.html.j2").render(
        title=title, subtitle=subtitle, breadcrumb=breadcrumb, cards=cards, intro=intro,
        site_url=SITE_URL, last_updated=datetime.date.today().isoformat())
    return _write(f"{rel_path}/index.html" if rel_path else "index_hub.html", html)


def render_hubs(summaries):
    """State, county, and city hub pages from the built listing summaries."""
    states = {}
    for s in summaries:
        states.setdefault(s["state"], {"name": s["state_name"], "counties": {}})
        co = states[s["state"]]["counties"].setdefault(s["county"], {"name": s["county_name"], "cities": {}})
        ci = co["cities"].setdefault(s["city"], {"name": s["city_name"], "pages": []})
        ci["pages"].append(s)

    for st, sdata in states.items():
        # city hubs
        for co, cdata in sdata["counties"].items():
            for ci, cidata in cdata["cities"].items():
                cards = [{"title": p["treatment_name"], "sub": f"{p['n_clinics']} provider" + ("" if p["n_clinics"] == 1 else "s"),
                          "url": p["url"],
                          "chip": (f"from ${p['from_price']} {p['price_unit']}" if p["from_price"] else None)}
                         for p in sorted(cidata["pages"], key=lambda x: x["treatment_name"])]
                bc = [{"name": "Home", "url": "/"}, {"name": sdata["name"], "url": f"/{st}/"},
                      {"name": cdata["name"], "url": f"/{st}/{co}/"},
                      {"name": cidata["name"], "url": f"/{st}/{co}/{ci}/"}]
                render_hub(f"Med spas in {cidata['name']}, {sdata['name']}",
                           f"{len(cidata['pages'])} treatment guides for {cidata['name']}", bc, cards, f"{st}/{co}/{ci}")
            # county hub
            ccards = [{"title": cidata["name"], "sub": f"{len(cidata['pages'])} treatment" + ("" if len(cidata['pages']) == 1 else "s"),
                       "url": f"/{st}/{co}/{ci}/", "chip": None}
                      for ci, cidata in sorted(cdata["cities"].items(), key=lambda kv: kv[1]["name"])]
            bc = [{"name": "Home", "url": "/"}, {"name": sdata["name"], "url": f"/{st}/"}, {"name": cdata["name"], "url": f"/{st}/{co}/"}]
            render_hub(f"Med spas in {cdata['name']} County, {sdata['name']}",
                       f"{len(cdata['cities'])} cities", bc, ccards, f"{st}/{co}")
        # state hub
        scards = [{"title": cdata["name"] + " County", "sub": f"{len(cdata['cities'])} cities",
                   "url": f"/{st}/{co}/", "chip": None}
                  for co, cdata in sorted(sdata["counties"].items(), key=lambda kv: kv[1]["name"])]
        bc = [{"name": "Home", "url": "/"}, {"name": sdata["name"], "url": f"/{st}/"}]
        render_hub(f"Med spa directory — {sdata['name']}", f"{len(sdata['counties'])} counties", bc, scards, st)
    return states


COUNTY_ORDER = ["miami-dade", "broward", "palm-beach"]


def render_index(summaries):
    """Homepage (design/landing): real stats, real county->city grid (with real treatment
    counts), real treatment cards (real prices or honest 'varies'), and the geolocation
    nearest-city set built from real covered cities. Renders templates/home.html.j2."""
    if not summaries:
        return None
    counties = {}  # (state, county) -> {name, state_name, cities}
    for s in summaries:
        key = (s["state"], s["county"])
        c = counties.setdefault(key, {"name": s["county_name"], "state_name": s["state_name"], "cities": {}})
        ci = c["cities"].setdefault(s["city"], {
            "name": s["city_name"], "url": f'/{s["state"]}/{s["county"]}/{s["city"]}/', "treats": set()})
        ci["treats"].add(s["treatment_slug"])

    order = sorted(counties, key=lambda k: (COUNTY_ORDER.index(k[1]) if k[1] in COUNTY_ORDER else 99, k[1]))
    groups = []
    for key in order:
        c = counties[key]
        cities = [{"name": v["name"], "url": v["url"], "n_treatments": len(v["treats"]),
                   "data_treatments": " ".join(sorted(v["treats"]))}
                  for _, v in sorted(c["cities"].items(), key=lambda kv: kv[1]["name"])]
        groups.append({"slug": key[1], "short_name": c["name"],
                       "name": f'{c["name"]}, {c["state_name"]}', "n_cities": len(cities), "cities": cities})

    stats = {
        "listings": sum(s["n_clinics"] for s in summaries),
        "cities": len({(s["state"], s["county"], s["city"]) for s in summaries}),
        "counties": len(counties),
    }

    # geolocation nearest-city set: covered cities that have a known centroid
    city_url = {s["city"]: f'/{s["state"]}/{s["county"]}/{s["city"]}/' for s in summaries}
    city_name = {s["city"]: s["city_name"] for s in summaries}
    geo_cities = [{"name": city_name[c], "slug": c, "lat": lat, "lng": lng, "url": city_url[c]}
                  for c, (lat, lng) in CITY_LATLNG.items() if c in city_url]

    html = env.get_template("home.html.j2").render(
        groups=groups, stats=stats, treatments=treatment_cards(load_clinics()),
        geo_cities_json=json.dumps(geo_cities),
        last_updated=datetime.date.today().isoformat(), site_url=SITE_URL)
    return _write("index.html", html)


def render_claim():
    html = env.get_template("claim.html.j2").render(
        site_url=SITE_URL, lead_routing_target="crm:glowmap-listing-claims",
        last_updated=datetime.date.today().isoformat())
    return _write("claim.html", html)


def render_advertise():
    """Placement / advertise page. Intake only — no card data on site.
    Checkout is Bonalta Payments hosted (gated). Routes interest to Campaigns CRM."""
    policy = {}
    try:
        policy = json.loads((ROOT / "data" / "monetization_policy.json").read_text())
    except Exception:
        pass
    slot_cap = (policy.get("placement_subscription") or {}).get("slot_cap_per_page", 3)
    crm_pipeline = (policy.get("campaigns_upsell") or {}).get("crm_pipeline", "crm:glowmap-campaigns-prospect")
    html = env.get_template("advertise.html.j2").render(
        site_url=SITE_URL, slot_cap=slot_cap,
        crm_pipeline=crm_pipeline,
        last_updated=datetime.date.today().isoformat())
    return _write("advertise.html", html)


def render_sitemap(summaries):
    urls = ["/", "/claim.html"]
    seen_hubs = set()
    for s in summaries:
        for hub in (f"/{s['state']}/", f"/{s['state']}/{s['county']}/", f"/{s['state']}/{s['county']}/{s['city']}/"):
            if hub not in seen_hubs:
                seen_hubs.add(hub); urls.append(hub)
        urls.append(s["url"])
    today = datetime.date.today().isoformat()
    body = "\n".join(
        f"  <url><loc>{SITE_URL}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n"
    return _write("sitemap.xml", xml)


def main():
    state = load_state()
    if state in ("paused", "halted", "halted_technical"):
        stop(f"build_state is '{state}' — not building.")
    if month_tokens_used() >= CONFIG["monthly_token_cap"]:
        stop(f"monthly token cap reached ({CONFIG['monthly_token_cap']}).")

    throttle = (state == "throttled")
    spec = COMPLETENESS or RECOMMENDED_COMPLETENESS
    enforce = COMPLETENESS is not None
    print(f"[builder] geo: {len(active_markets())} active market(s); completeness "
          f"{'ENFORCED from config' if enforce else 'DRY-RUN (config completeness absent; cannot edit config)'}")

    fetched, report = fetch_pages(spec, enforce)
    passed, skipped = [], 0
    for page in fetched:
        if quality_gate(page):
            passed.append(page)
        else:
            skipped += 1
            print(f"[builder] skipped (failed quality gate): {page['path']}")
    if throttle:
        passed = passed[:10]

    summaries = []
    for page in passed:
        out = render(page, page_links(page, passed))
        summaries.append(page_summary(page))
        print(f"[builder] built {out.relative_to(GENERATED)}")
    built = len(summaries)

    render_hubs(summaries)
    render_index(summaries)
    render_claim()
    render_advertise()
    render_sitemap(summaries)
    print(f"[builder] built hubs + homepage + claim + advertise + sitemap.xml")

    report["empty_fields"] = compute_empty_fields(passed)
    report["mode"] = "enforced" if enforce else "dry-run (config 'completeness' absent)"
    report["thresholds_used"] = spec
    print(f"[builder] completeness: mode={report['mode']} | listings_excluded={len(report['excluded_listings'])} | "
          f"pages_held={len(report['held_pages'])} | empty_fields={report['empty_fields']}")
    (GENERATED / "_completeness_report.json").write_text(json.dumps(report, indent=2))

    # DO NOT merge to main. DO NOT deploy. (hard-gated in CLAUDE.md)
    print(f"[builder] done. built={built} skipped={skipped} state={state}")


if __name__ == "__main__":
    main()
