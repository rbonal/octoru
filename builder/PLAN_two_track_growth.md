# Octoru — Two-Track Growth Plan

_Owner: Rolando. Operating doc for the weekly striking-distance build-up and expansion sprints. Created 2026-08-18._

Work on octoru.com is divided into **two tracks with different economics**. Do not mix them in one run — that dilutes both.

Why: clicks come almost entirely from page 1 (positions 1–10). As of 2026-08-18 the site has ~140 ranked keywords but **zero in the top 10** — impressions rise, clicks stay ~0. Track A converts existing near-page-1 equity into clicks; Track B refills the funnel with new coverage. Track the real leading indicator: **# of keywords in the top 10**, not impressions.

---

## Track A — "Close the Gap" (already ranking, near the top)

**Qualifies:** a page already at positions ~11–40 for a *commercial / transactional* query. Strip out brand/navigational queries (a directory earns few clicks on those even at #1).

**Source:** weekly DataForSEO `ranked_keywords` for octoru.com, filter `rank_group 11–40`, drop navigational/brand, group by page.

**Work:** deepen content + FAQ/FAQPage + `MedicalClinic`/`AggregateRating` schema, add internal links pointing *to* the target page, and begin earning real backlinks. Template/content only — ships as an `auto/build` PR (never self-merge; merge = deploy = Rolando).

**Gating:** none. This is the **weekly default** (cheap, compounding).

**Metric:** keywords crossing into the top 10; then clicks.

### Current queue (from 2026-08-18 scan)
1. `/fl/fort-lauderdale/lip-filler/guide/` — 3 commercial queries ("lip fillers fort lauderdale", "lip injections fort lauderdale", "fort lauderdale lip injections"), ~510/mo combined, **KD 2**, pos 36–39. **Best effort-to-reward on the site.**
2. `/fl/miami-dade/coral-gables/botox/` — "botox coral gables" 170/mo, **KD 4**, transactional, **pos 24** (closest commercial to page 1; CPC ~$14).
3. `/fl/miami-dade/coral-gables/lip-filler/` — "top rated lip filler near me" 590/mo, pos 37, **KD 28** (biggest volume, slowest; FAQ-enriched 2026-08-18).

---

## Track B — "New Ground" (uncovered topics/cities, ~zero coverage)

**Qualifies:** a treatment vertical or city with real demand where octoru has **no** ranking page, or only thin/held ones.

**Source:** demand-size candidates (DataForSEO Ads volume, Miami-metro). Keep those that clear a volume floor **and** can realistically get ≥2 rated real providers per city.

**Work — 3 gated steps (NOT a solo weekly task):**
1. **Prospect + rate** real providers for the treatment × city (data pipeline; `state/cowork_places_handoff.md`).
2. **Rolando** adds the treatment/city to `config/thresholds.json` `seed_scope` — this file is hard-gated; the builder cannot edit it.
3. Builder generates the vertical across all cities; the quality gate (`min_listings=2`) culls the thin ones.

**Gating:** config edit (Rolando) + prospecting data. Run as a **monthly expansion sprint**, not weekly.

**Metric:** new pages that pass the gate → new impression footprint → graduates into Track A once they land at 11–40.

### Candidate verticals (Miami-city vol; multiply across the ~47-city metro)
| Topic | Vol | Verdict |
|---|---|---|
| IV therapy | 590/mo | **Build first** — strongest demand |
| HydraFacial | 170/mo | Strong |
| Morpheus8 | 70/mo | Moderate, premium |
| Sculptra | 70/mo | Moderate, premium |
| Semaglutide / GLP-1 | 50/mo, CPC ~$48 | High value but fierce competition + Rx/compliance sensitivity (mind the CLAUDE.md gate) |
| Kybella | collapsed (~10–30/mo now) | Skip |
| Dysport, PRP hair, chemical peel | 10–50/mo | Skip / too thin |

### ⚠ Stalled launches to resurrect first (fastest Track-B win)
Branches `seo/iv-therapy-launch` and `seo/hydrafacial-launch` already contain the full build — `config/thresholds.json` treatment edits, treatment details/pricing, learn topics, and clinic tagging (authored Jul 15–17) — but were **never merged into `auto/build`**, so neither vertical is live. HydraFacial currently only surfaces via one `/learn/` article at pos #66–97. **Action:** verify each branch builds with ≥2 rated providers per city, rebase onto current `auto/build`, and merge (Rolando). Check `seo/morpheus8-launch`, `seo/chemical-peel-launch` similarly.

### Cheapest Track-B win (no config change, no new vertical)
In-scope cities currently **held** because they have <2 rated providers. Pure **prospecting** problem — get 2+ real rated clinics in and the page ships on the next build.

---

## Cadence
- **Track A:** every weekly build-up run (default).
- **Track B:** monthly sprint, only when a vertical is greenlit + a prospecting/ratings pass is done.
- Deploy is always a **separate human merge** of the `auto/build` PR (medical-marketing compliance boundary).

## Structural ceilings (true for both tracks)
- **Local pack:** most commercial city×treatment queries show a Google map pack that absorbs top clicks. A directory can't sit in the pack — that upside runs through Google Business Profiles (Local Falcon), not these pages.
- **Link authority:** competitors on these queries carry ~20–33 referring domains; octoru pages have ~2–3. Content polish nudges KD-2/KD-4 pages onto page 1; it will **not** vault high-KD pages top-5. A real referring-domain plan is the gating lever for durable click growth.

## Related routines
- **Octoru Weekly Build-Up (Tue):** owns Track A content on `auto/build`.
- **weekly-seo-monitor (desktop):** owns GSC — indexing requests, impressions baseline, technical/indexing fixes. (Cloud scheduled runs cannot reach GSC/Chrome; indexing must run on desktop.)
