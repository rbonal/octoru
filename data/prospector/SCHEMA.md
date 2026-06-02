# Prospector input — flat clinic list

`builder/build.py` → `load_clinics()` reads **every `*.json` file in this directory**.
Each file is a JSON **array** (or a single object) of **real** clinic records. The builder
groups them into `treatment × neighborhood` pages for `config/thresholds.json → seed_scope`.

The builder never fabricates these records or their quality-gate flags — it only reads,
groups, and renders. A clinic appears on one page per (treatment it offers × its neighborhood).

## One clinic record

```json
{
  "slug": "glow-aesthetics-brickell",
  "name": "Glow Aesthetics Brickell",
  "neighborhood": "brickell",
  "neighborhood_name": "Brickell",
  "address": "1234 Brickell Ave, Miami, FL 33131",
  "phone": "+13055551234",
  "email": "hello@glowaesthetics.example",
  "booking_url": "https://glowaesthetics.example/book",
  "rating": 4.8,
  "review_count": 212,
  "rating_source": "google_places_api",
  "starting_prices_usd": { "lip-filler": 650, "botox": 12 },
  "languages": ["English", "Spanish"],
  "treatments": ["lip-filler", "botox"],
  "featured_tier": 1,
  "lead_routing_target": "crm:glowmap-injectables",

  "has_real_clinic_data": true,
  "uses_scraped_review_text": false,
  "has_before_after": false,
  "before_after_consent": false
}
```

## Field rules

| Field | Required | Notes |
|---|---|---|
| `slug`, `name`, `address`, `phone` | yes | Real, specific clinic identity. |
| `neighborhood` | yes | A **seed-scope slug** (`brickell`, `coral-gables`, `south-beach`, `coconut-grove`). Records outside the scope are ignored. |
| `neighborhood_name` | optional | Display label; falls back to the canonical map in `build.py`. |
| `treatments` | yes | List of **treatment slugs** the clinic offers (`botox`, `lip-filler`, `coolsculpting`, `laser-hair-removal`, `microneedling`). Drives which pages the clinic lands on. |
| `rating`, `review_count` | yes | For the `AggregateRating` schema markup. |
| `rating_source` | yes | **Must be a permitted API** (e.g. `google_places_api`). Never scraped Google/Yelp review text. |
| `starting_prices_usd` | optional | Per-treatment map (preferred) **or** a flat `starting_price_usd` number. |
| `languages`, `email`, `booking_url`, `featured_tier`, `lead_routing_target` | optional | `featured_tier > 0` sorts a clinic to the top and shows the "Featured" tag. |
| `google_listing_url` | optional | "View on Google" link. If omitted, the builder auto-generates a no-API Google Maps **search** URL from `name` + `address`. When the Places API is wired, pass the exact place-based URL here and it takes priority. This is a link only — it carries no rating data and does not satisfy the `AggregateRating` requirement. |
| `last_verified` | optional | ISO date the record was last verified. Surfaced on-page as "Updated [date]" (page shows the most-recent listing date, else today). |
| `sources` | optional | Per-field provenance map, e.g. `{"address": "places", "phone": "clinic_site", "price": "clinic_site"}`. Surfaced where useful; never invented. |

## Sourcing hierarchy when a field is missing
Fill a missing field in this order, and **never impute a value to a clinic that didn't report it**:
1. **Places API** (permitted) — ratings come from here only; never scraped.
2. **The clinic's OWN website** — first-party *published* info only (address, phone, prices, hours). **Never** third-party review text.
3. **Clinic-claimed/verified data** (e.g. via the Claim-your-listing intake, after human verification).
4. **Derive from the reporting subset, labeled with coverage** — e.g. a page price range shows "4 of 8 providers list pricing". A figure is shown only for the providers that reported it.
If a field still can't be sourced, the template renders an **honest empty state** (e.g. missing price → "Pricing not listed — request a quote"). No blanks, no zeros, no placeholder text.

## Completeness thresholds (OPERATOR-OWNED — lives in `config/thresholds.json`)
The builder **reads** these and **never invents** them (and cannot edit `config/`). Add this block to `config/thresholds.json` to enforce; until present the builder runs the gate in **dry-run** (reports only). A listing below `min_listing_fields` is **excluded**; a page below `min_page_requirements` is **held** (not rendered). Better no page than a thin one.

```json
"completeness": {
  "min_listing_fields": ["name", "address", "phone", "rating", "treatments"],
  "min_page_requirements": { "min_listings": 3, "require_cost_block": true, "require_guidance": true }
}
```

## Quality-gate flags (the builder passes these through verbatim — set them honestly)

A page is **written only if every clinic on it passes** (`builder/build.py` → `quality_gate`):

- `has_real_clinic_data` — must be `true`. Real, specific clinic, not filler.
- `uses_scraped_review_text` — must be `false`. No scraped review text (ratings come from a permitted API only).
- `has_before_after` — if `true`, then `before_after_consent` **must** also be `true`, else the page is skipped.
- `before_after_consent` — recorded consent for any before/after patient image.

Plus, structurally guaranteed by the template (set true for every emitted page):
the lead form's consent + privacy language, and `schema.org` `MedicalClinic` + `AggregateRating` markup.

> If a clinic can't honestly set these, leave it out. The builder skips and logs; it never
> lowers the gate to hit a page count.
