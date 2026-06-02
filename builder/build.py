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

# Public city centroids (geographic fact, not clinic data) — used ONLY for the homepage
# "nearest covered city" geolocation. Cities without an entry are omitted from the
# nearest-match set; the build never invents clinic data from these.
CITY_LATLNG = {
    "aventura": (25.9565, -80.1390), "bal-harbour": (25.8920, -80.1265), "brickell": (25.7617, -80.1918),
    "coconut-grove": (25.7282, -80.2436), "coral-gables": (25.7215, -80.2684), "doral": (25.8195, -80.3553),
    "hialeah": (25.8576, -80.2781), "homestead": (25.4687, -80.4776), "kendall": (25.6793, -80.3173),
    "key-biscayne": (25.6938, -80.1626), "miami-lakes": (25.9087, -80.3087), "miami-springs": (25.8220, -80.2895),
    "midtown": (25.8076, -80.1934), "north-miami": (25.8901, -80.1867), "palmetto-bay": (25.6218, -80.3248),
    "pinecrest": (25.6670, -80.3083), "south-beach": (25.7826, -80.1340), "sunny-isles-beach": (25.9501, -80.1223),
    "surfside": (25.8787, -80.1257),
    "coconut-creek": (26.2517, -80.1789), "cooper-city": (26.0573, -80.2717), "coral-springs": (26.2710, -80.2706),
    "dania-beach": (26.0526, -80.1437), "davie": (26.0765, -80.2521), "deerfield-beach": (26.3184, -80.0998),
    "fort-lauderdale": (26.1224, -80.1373), "hallandale-beach": (25.9812, -80.1484), "hollywood": (26.0112, -80.1495),
    "lighthouse-point": (26.2756, -80.0875), "margate": (26.2445, -80.2064), "miramar": (25.9861, -80.3035),
    "oakland-park": (26.1723, -80.1320), "parkland": (26.3098, -80.2370), "pembroke-pines": (26.0078, -80.2963),
    "plantation": (26.1276, -80.2331), "pompano-beach": (26.2379, -80.1248), "sunrise": (26.1669, -80.2564),
    "weston": (26.1004, -80.3998),
    "boca-raton": (26.3683, -80.1289), "west-palm-beach": (26.7153, -80.0534),
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
        "featured_tier": clinic.get("featured_tier", 0),
        "lead_routing_target": clinic.get("lead_routing_target"),
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
    """Build treatment x city pages over the active geo tree, applying operator-owned
    completeness thresholds. Returns (pages, report). Listing below min_listing_fields is
    excluded; page below min_page_requirements is HELD. Dry-run (enforce=False) reports only."""
    clinics = load_clinics()
    report = {"excluded_listings": [], "held_pages": []}
    if not clinics:
        print(f"[builder] no prospector data in {PROSPECTOR_DIR} — nothing to build.")
        return [], report

    req_fields = (spec or {}).get("min_listing_fields") or []
    page_reqs = (spec or {}).get("min_page_requirements") or {}
    treatments = CONFIG["seed_scope"]["treatments"]

    pages = []
    for market in active_markets():
        for t in treatments:
            matched = [c for c in clinics if _clinic_in_market(c, market) and t in (c.get("treatments") or [])]
            if not matched:
                continue
            label = f"{t}@{market['state']}/{market['county']}/{market['city']}"
            qualifying = []
            for c in matched:
                miss = listing_missing_fields(c, req_fields)
                if miss:
                    report["excluded_listings"].append({"clinic": c.get("name"), "page": label, "missing": miss})
                    print(f"[builder] listing {'excluded' if enforce else 'would-exclude (dry-run)'} (missing {miss}): {c.get('name')} on {label}")
                    if enforce:
                        continue
                qualifying.append(c)
            use = qualifying if enforce else matched
            if not use:
                report["held_pages"].append({"page": label, "reason": "no qualifying listings"})
                print(f"[builder] HELD {label}: no qualifying listings")
                continue
            page = _assemble_page(t, market, use)
            reason = page_hold_reason(page, page_reqs)
            if reason:
                report["held_pages"].append({"page": label, "reason": reason})
                print(f"[builder] {'HELD' if enforce else 'would-HOLD (dry-run)'} {label}: {reason}")
                if enforce:
                    continue
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
        groups.append({"name": f'{c["name"]}, {c["state_name"]}', "n_cities": len(cities), "cities": cities})

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
    render_sitemap(summaries)
    print(f"[builder] built hubs + homepage + claim + sitemap.xml")

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
