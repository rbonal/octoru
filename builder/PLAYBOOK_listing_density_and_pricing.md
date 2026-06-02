# Playbook — Listing Density & Pricing (reusable)

**When to use:** building or improving any treatment × neighborhood (or service × location)
directory where thin, near-identical pages won't index or convert. Goal: make each page
*dense, unique, accurate, and priced* — without padding or fabricating. Applies to GlowMap
and any "local providers by category × area" project.

**Why it matters:** thin/near-duplicate pages are the #1 reason programmatic directory pages
fail to index. Depth + real per-page data is what ranks and converts. (`CLAUDE.md`: optimize
for ranking + leads, never raw page count; no near-duplicate pages.)

---

## Target bar per page
- **6–10 real providers** where the market supports it. **Minimum 2 real** to publish at all.
- Each listing: name, **address, phone**, booking URL, languages, **treatments offered**, and
  **starting price where published**. Rating comes later from a permitted API (never scraped).
- A **unique intro** built from real signals (provider count, observed price range w/ unit,
  languages) — NOT a boilerplate paragraph repeated across neighborhoods.

## Step-by-step
1. **Scope, don't widen.** Densify *existing* treatment×neighborhood pages (more providers).
   Adding new treatments/neighborhoods is the evaluator's scope decision — don't do it unilaterally.
2. **Find candidates.** Web search variants: `med spa <neighborhood> <city> <treatment>`,
   `<treatment> <neighborhood> price`, `best <category> <area>`. Collect from results.
3. **Exclude ruthlessly** (no padding):
   - Out-of-geo (wrong neighborhood/city) — verify the *printed address*, not the marketing.
   - Chain locations in the wrong area (dedupe by address, not name).
   - Demo/marketing sites and aggregators that aren't a real clinic.
4. **Verify each on its OWN site** (public business info = compliant): exact address, phone,
   booking URL, languages, and which target treatments it actually lists. Only claim a treatment
   the clinic actually offers.
5. **Pricing.** Pull *published* starting prices from the clinic's site/price page. Record per
   treatment with the correct **unit** (botox = per unit, filler = per syringe, body/laser =
   per session/package). Many clinics don't publish prices — leave null, don't guess. Don't mix
   a per-unit price and a package price in the same "from $X" without labeling the unit.
6. **Neighborhood label** = the neighborhood the clinic lists itself under (self-reported),
   EXCEPT when the printed address is squarely a *different* neighborhood — then use the address
   and flag it (on-page address must not contradict the page header).
7. **Stage, then gate.** Put records in the staging draft (e.g. `data/seed_candidates_DRAFT.json`),
   not the build path, until ratings exist. Map to `data/prospector/SCHEMA.md`. The builder's
   quality gate is the final arbiter of what ships.
8. **Drop the un-densifiable.** If a treatment×neighborhood has <2 real providers (common for
   scarce services like CoolSculpting / laser hair removal), recommend **dropping** the page
   rather than shipping it thin. Quality over count.

## Compliance guardrails (non-negotiable)
- **Ratings only from a permitted API** (e.g. Google Places). Never scrape Google/Yelp ratings
  or review text; never fabricate. No permitted rating → no `AggregateRating` → page can't ship.
- Real, specific clinic data only. No template filler, no near-duplicate prose.
- Contact info pulled from the clinic's own site is fine; that is not "scraping reviews."

## Build-pipeline hooks (this repo)
- `_assemble_page()` builds the unique intro (provider count + price range + languages).
- `_clinic_for_page()` shapes a clinic + carries gate flags verbatim; adds `price_unit`,
  `treatments_offered`, `google_listing_url`.
- `page_summary()` → homepage card data (provider count, `from_price`).
- `page_links()` → breadcrumbs + cross-links (internal-link best practice).
- Pricing units: `TREATMENT_UNITS`. Display names: `TREATMENT_NAMES` / `NEIGHBORHOOD_NAMES`.

## Common pitfalls
- Boilerplate intros repeated across neighborhoods → near-duplicate penalty. Keep them data-driven.
- Padding with far/irrelevant businesses to hit a count → hurts trust + rankings.
- Claiming treatments a clinic doesn't list → inaccurate listings.
- Hand-copying Google ratings to "fill the gap" → violates the permitted-API rule.
