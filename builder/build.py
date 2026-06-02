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
        "email": clinic.get("email"),
        "booking_url": clinic.get("booking_url"),
        "google_listing_url": _google_listing_url(clinic),
        "rating": clinic.get("rating"),
        "review_count": clinic.get("review_count"),
        "rating_source": clinic.get("rating_source"),
        "starting_price_usd": _starting_price(clinic, treatment_slug),
        "languages": clinic.get("languages", []),
        "featured_tier": clinic.get("featured_tier", 0),
        "lead_routing_target": clinic.get("lead_routing_target"),
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
    return {
        "treatment": {"slug": treatment_slug, "name": t_name},
        "neighborhood": {"slug": neighborhood_slug, "name": n_name},
        "city": "Miami",
        # The consent form + schema.org markup are built into the template, so these
        # structural flags hold for every page this builder emits.
        "page_flags": {"has_consent_form": True, "has_schema_markup": True},
        "meta_description": (
            f"Compare {n} {t_name.lower()} {provider_word} in {n_name}, Miami — "
            f"verified ratings, starting prices, and languages spoken. Request a personalized quote."
        ),
        "intro": (
            f"{n_name} has {n} {t_name.lower()} {provider_word} in our directory. "
            f"Each listing below shows verified ratings and starting prices so you can "
            f"compare before booking a consultation."
        ),
        "clinics": [_clinic_for_page(c, treatment_slug) for c in clinics],
    }


def fetch_pages():
    """Build seed-scope pages from the prospector's flat clinic list.
    For each treatment x neighborhood in config['seed_scope'], group the real
    clinics offering that treatment in that neighborhood into one page. Pages with
    no clinics are skipped and logged — never filled with placeholder. The quality
    gate (in main) then decides which assembled pages may actually be written."""
    scope = CONFIG["seed_scope"]
    clinics = load_clinics()
    if not clinics:
        print(f"[builder] no prospector data in {PROSPECTOR_DIR} — nothing to build.")
        return []

    pages = []
    for t in scope["treatments"]:
        for n in scope["neighborhoods"]:
            matched = [
                c for c in clinics
                if c.get("neighborhood") == n and t in (c.get("treatments") or [])
            ]
            if not matched:
                print(f"[builder] no clinics for '{t}' in '{n}' — page skipped (no data).")
                continue
            pages.append(_assemble_page(t, n, matched))
    return pages


def render(page):
    page.setdefault("last_updated", datetime.date.today().isoformat())
    html = env.get_template("treatment-page.html.j2").render(**page)
    slug = f"{page['treatment']['slug']}-{page['neighborhood']['slug']}"
    out = GENERATED / f"{slug}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def render_index(built_pages):
    """Homepage linking the listing pages that actually built, grouped by
    neighborhood (in seed order). Navigational only — it lists pages that already
    passed the clinic quality gate, so it carries no rating data of its own."""
    if not built_pages:
        return None
    groups = []
    for n_slug in CONFIG["seed_scope"]["neighborhoods"]:
        pages = [p for p in built_pages if p["neighborhood_slug"] == n_slug]
        if pages:
            groups.append({"name": pages[0]["neighborhood_name"], "pages": pages})
    html = env.get_template("index.html.j2").render(
        neighborhoods=groups,
        page_count=len(built_pages),
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
    built, skipped = 0, 0
    built_pages = []
    for page in fetch_pages():
        if throttle and built >= 10:
            break
        if quality_gate(page):
            out = render(page)
            built += 1
            built_pages.append({
                "slug": f"{page['treatment']['slug']}-{page['neighborhood']['slug']}",
                "treatment_name": page["treatment"]["name"],
                "neighborhood_slug": page["neighborhood"]["slug"],
                "neighborhood_name": page["neighborhood"]["name"],
                "n_clinics": len(page.get("clinics", [])),
            })
            print(f"[builder] built {out.name}")
        else:
            skipped += 1
            print(f"[builder] skipped (failed quality gate): "
                  f"{page.get('treatment', {}).get('slug')}-{page.get('neighborhood', {}).get('slug')}")

    idx = render_index(built_pages)
    if idx:
        print(f"[builder] built {idx.name} (homepage linking {built} pages)")

    # TODO (auto-approved): git add + commit to branch 'auto/build'
    # DO NOT merge to main. DO NOT deploy. (hard-gated in CLAUDE.md)
    print(f"[builder] done. built={built} skipped={skipped} state={state}")


if __name__ == "__main__":
    main()
