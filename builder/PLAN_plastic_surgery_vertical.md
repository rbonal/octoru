# PLAN — Plastic Surgery vertical (Octoru)

Plastic surgery is a SECOND vertical alongside med spas. It reuses the existing
geo/place taxonomy, the Beta-posterior `rank_providers()`, the quality gate, and the
integrity guards — but runs under category-specific rules. Nothing here deploys; it
builds to `auto/build` and is still subject to the open ratings-integrity HALT.

## Confirmed product decisions
1. **Per-procedure pages** — each surgical procedure gets its own city page (like the
   5 med-spa treatments). Best procedure-level SEO ("BBL Miami", "tummy tuck Fort Lauderdale").
2. **Under-served cities still get a page** — a city×procedure with 0 local providers
   builds anyway, showing the NEAREST-city providers + an honest "No surgeons in {city}
   yet — nearest options below" state (demand/SEO capture).
3. **Surgeon ranking = the clinic's Beta-posterior score**, but the displayed rating is
   **explicitly the clinic's, never the surgeon's own**. Clinic reviews must never
   masquerade as a surgeon's personal rating.

## Data model

### Category field
Every provider gains `category`: `med-spa` | `plastic-surgery` (existing data = med-spa).
Treatments/procedures and completeness thresholds become category-scoped.

### Surgical procedures (treatment slugs, plastic-surgery category)
Start focused (~7 high-volume): `bbl`, `tummy-tuck`, `breast-augmentation`,
`liposuction`, `rhinoplasty`, `mommy-makeover`, `facelift`. (Extend later:
breast-lift, blepharoplasty, gynecomastia.)
Operator-owned — added to `config/thresholds.json` seed_scope (hard-gated for the builder;
I supply the exact block).

### Surgeon entity — `data/surgeons.json` (NEW)
```
{
  "slug", "name",
  "category": "plastic-surgery",
  "type": "surgeon",
  "credentials": {                 // ALL as stated on the provider's own site — verbatim, not adjudicated
    "school": "...",               // e.g. "University of Miami Miller School of Medicine"
    "specialty": "...",            // e.g. "Plastic & Reconstructive Surgery"
    "degrees": ["MD", "FACS"],
    "boards": ["..."]              // board(s) the provider lists, copied as-stated. NEVER inferred, NEVER negated.
  },
  "credentials_source": "https://clinic.com/team/dr-x",   // URL the credentials were copied from
  "procedures": ["bbl","tummy-tuck", ...],
  "clinic_slug": "...",        // the clinic where they serve = CONTACT source
  "independent": true|false,   // solo practice -> the clinic IS their own entity
  // NO own rating/review fields — rating is the clinic's, shown as such
}
```
A surgeon's contact (phone / booking / address) = their clinic's. A surgeon may be
listed even when their clinic is also listed ("equally important inside clinics or
as an independent entity"). Listing is open to any surgeon the clinic permits to
operate — board certification is NOT a gate.

### Clinic additions
`category`, optional `accreditation` (AAAASF/AAAHC facility accreditation), and an
optional `surgeons: [slug]` back-reference.

## Listings on a procedure page (e.g. "BBL in Miami")
Two entry types, ranked together in one list:
- **Clinic** entry — as today (own rating, own contact).
- **Surgeon** entry — surgeon name + **credentials as-stated** (school / specialty / degrees /
  board, copied verbatim from the provider's site, with an inline source line "Credentials as
  listed on the provider's website") + "at {Clinic Name}", contact = clinic's. Rating rendered
  as **"{Clinic} · 4.9 (200)"** with a label making clear it is the CLINIC's rating, not the
  surgeon's.
- Surgeons sharing a clinic naturally cluster (same clinic score); each labeled with the clinic.

## Ranking (reuses the single canonical path)
- `rank_providers()` / `_provider_score()` (Beta-posterior) unchanged — still the ONLY
  ordering for every list.
- **Surgeon score = the Beta-posterior of their clinic** (inherit clinic.rating + review_count).
- Display integrity: surgeon's shown rating is labeled the clinic's. Credentials are
  descriptive display only — never a sort key (per decision #3).

## Category-specific rules
- **Completeness:** plastic-surgery `min_listings = 1` (list even one); med-spa stays 2.
  Requires the completeness gate to be category-aware (operator config).
- **Nearest-provider fallback** for 0-provider cities (uses the city centroids already in
  places.json): pull nearest providers from other cities, ranked by distance then Beta score,
  labeled "Nearby — no providers in {city} yet."

## Compliance & safety (higher-stakes than med spa)
- **Credentials are displayed as-stated, attributed to source, never adjudicated.** Copy school /
  specialty / degrees / board verbatim from the provider's own website, with an inline
  "Credentials as listed on the provider's website" line. Never assert a surgeon IS or (critically)
  IS NOT board-certified — a negative-credential claim is the liability. Absence of a board simply
  renders nothing, not a warning.
- **Facility accreditation (AAAASF/AAAHC)** shown only where the provider states it, same source rule.
- No unconsented before/after (existing gate). No outcome / "best surgeon" claims.
- Surgeon rating must be labeled the clinic's (decision #3).
- Rating-integrity guards apply to surgery providers too.

## Safety decision — RESOLVED (operator, 2026-06-06)
List any surgeon the clinic permits to operate — board certification is NOT a listing gate.
Do NOT place a verified board badge (too many boards; adjudication risk). Show credentials
exactly as the provider's site states them, source-attributed. Never publish a non-certification
claim (liability).

## Build phases
0. **Operator config** (hard-gated): add surgery procedures + category-aware completeness
   to config/thresholds.json. I'll supply the exact block.
1. **Builder code**: category field; load surgeons.json; surgeon listings + "rating for
   {clinic}" labeling + source-attributed credentials line; surgeon-score-from-clinic;
   nearest-provider fallback; category-aware gate; templates (credentials/accreditation
   as-stated, nearby empty state).
2. **Data**: prospect surgery clinics + surgeons (Places for clinics; credentials copied
   verbatim from each provider's own site with the source URL recorded); ratings pass; stage to draft.
3. **Build** to auto/build, verify, gate, integrity scan. (Still blocked from publish by the
   open med-spa ratings HALT + the deploy gate.)
