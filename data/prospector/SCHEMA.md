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
