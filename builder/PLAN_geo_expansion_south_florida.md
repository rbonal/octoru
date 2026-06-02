# Plan — Geographic Expansion: South Florida by County

**Status:** PROPOSAL. Scope (which counties/markets are active) is OPERATOR-OWNED in
`config/thresholds.json → seed_scope`; the builder cannot edit config. Expansion is
**phased and gated** — activate a market only after the prior cohort proves out
(indexing + leads), per CLAUDE.md ("expand only as cohorts prove out; never raw page count").

---

## 1. Geographic taxonomy (3 levels)
**County → Market (city/neighborhood) → Treatment page.**
South Florida = tri-county + optional Keys:
- **Miami-Dade** (LIVE): Brickell, Coral Gables, South Beach, Coconut Grove.
  Next markets: Aventura, Doral, Kendall, Wynwood/Midtown, Pinecrest, **Miami Lakes** (Bonalta's anchor), Bal Harbour.
- **Broward**: Fort Lauderdale (Las Olas), Weston, Pembroke Pines, Hollywood, Coral Springs.
- **Palm Beach**: **Boca Raton** (aesthetics-dense), Delray Beach, West Palm Beach, Palm Beach Gardens, Jupiter, Wellington.
- **Monroe (Keys)**: later/optional — thin market.

## 2. URL / information architecture (subdirectories by county)
Clean, flat-ish hierarchy (every page ≤3 clicks; matches the breadcrumb/internal-link best practices already adopted):
- **County hub:** `/{county}/` → e.g. `/broward/` (lists that county's markets + treatments)
- **Market hub:** `/{county}/{market}/` → e.g. `/palm-beach/boca-raton/` (treatments in that market)
- **Listing page:** `/{county}/{market}/{treatment}/` → e.g. `/palm-beach/boca-raton/botox/`
- Miami-Dade migrates from today's flat `/{treatment}-{neighborhood}.html` into `/miami-dade/{market}/{treatment}/`. **No redirect debt** — we haven't deployed yet.
- **Breadcrumb:** Home › Palm Beach › Boca Raton › Botox (+ BreadcrumbList schema, already built).
- **sitemap.xml** generated per build (essential at scale for indexing).

## 3. Proposed config evolution (operator adds; builder reads — never invents)
Replace the flat `neighborhoods` list with a gated geo tree:
```json
"seed_scope": {
  "treatments": ["botox", "lip-filler", "coolsculpting", "laser-hair-removal", "microneedling"],
  "geo": {
    "miami-dade": { "name": "Miami-Dade",
      "markets": { "brickell": {"name":"Brickell","status":"active"},
                   "coral-gables": {"name":"Coral Gables","status":"active"},
                   "aventura": {"name":"Aventura","status":"planned"} } },
    "broward": { "name": "Broward",
      "markets": { "fort-lauderdale": {"name":"Fort Lauderdale","status":"planned"} } },
    "palm-beach": { "name": "Palm Beach",
      "markets": { "boca-raton": {"name":"Boca Raton","status":"planned"} } }
  }
}
```
`status: active|planned` is the gate — the builder only builds `active` markets; the evaluator (or operator) flips `planned → active` as a cohort proves out. Builder never flips it.

## 4. Build architecture changes (one-time lift; builder code — I implement when approved)
- `fetch_pages`: iterate county → active market → treatment; clinic records gain `county` + `market` (or a market→county map in config).
- Slugs/paths become `/{county}/{market}/{treatment}/`; render into nested dirs under `generated/`.
- New templates: **county hub** + **market hub** (reuse the card grid + filter).
- Breadcrumbs/cross-links extend to the county level (same treatment in nearby markets; other treatments in this market; sibling markets in this county).
- **sitemap.xml** generator.
- Completeness gate unchanged — applies per market×treatment page (holds thin ones).

## 5. Data / sourcing plan (recurring cost — the real constraint)
- Per new market: one **prospector pass** (Places + clinic sites, per the density/pricing playbook) → real clinics with `county`/`market` → one **ratings pass** (permitted Places) → ship.
- Only activate a market once it clears the completeness bar for the priority treatments (≥ min_listings real providers). **Don't create empty county sections.**
- Boca Raton, Fort Lauderdale, Aventura, Miami Lakes are the densest near-term targets.

## 6. Phasing (gated rollout)
1. **Phase 1 (now):** Miami-Dade seed (4 markets) — prove indexing + leads. *(in progress)*
2. **Phase 2:** deepen Miami-Dade (Aventura, Doral, Kendall, Miami Lakes, Wynwood) — same county, lowest risk.
3. **Phase 3:** Broward (Fort Lauderdale, Weston, Pembroke Pines, Hollywood).
4. **Phase 4:** Palm Beach (Boca Raton, Delray, West Palm, PB Gardens).
5. **Phase 5:** long-tail markets + Keys.
Each phase gated by the evaluator before the next.

## 7. Risks & guardrails (bigger at scale)
- **Thin/near-duplicate content** is the #1 risk when multiplying markets. Mitigate: completeness gate per page, unique per-page data (real providers + prices + local context), drop un-densifiable pages, never boilerplate.
- **Index bloat / crawl budget:** sitemap, strong internal linking, don't generate empty combinations, noindex held/thin pages.
- **Compliance scales too:** permitted-API ratings only, consent language, claim-flow verification — per market.
- **Operational cadence:** each market = a prospector + ratings pass; plan the pipeline throughput before activating many at once.
- **Scope boundary:** activation is config (operator/evaluator); the builder builds only active scope.

## 8. What I can do on approval
Implement the architecture (config-reading for the geo tree, nested paths, county/market hubs, sitemap, breadcrumbs) behind the existing seed so nothing changes until the operator flips a market to `active`. Then drive the per-market prospector + ratings passes one market at a time.
