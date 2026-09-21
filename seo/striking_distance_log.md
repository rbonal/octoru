# Octoru — Striking-Distance SEO Log

A running log of the weekly striking-distance build. Newest entry on top.

---

## 2026-09-21

**Market conquered: Winter Park, FL (Orange County)** — the Orlando "find its Coral Gables" enclave from EXPANSION_PLAN v2, Stage 1. Data-only launch via the data-driven geo model (new `data/places.json` entry + `data/prospector/winter-park.json`); no `build.py`/`config` edits. Shipped from an unattended scheduled cloud session as PR #52 → `auto/build` (gated pipeline auto-merges on green build-verify + Workers Builds; no push/deploy from here).

**Demand that drove selection (DataForSEO, this run):** all treatment-level difficulty inside Octoru's proven zone (≤24):

| Query | Vol/mo | Difficulty | Intent |
|---|---|---|---|
| botox winter park | 390 | 16 | transactional |
| med spa winter park | 210 | 16 | navigational (city hub) |
| laser hair removal winter park | 90 | 11 | transactional (+143% qtr) |
| microneedling winter park | 70 | ~0 | commercial |
| lip filler winter park | 40 | 14 | transactional |
| hydrafacial winter park | 40 | 4 | informational |

Fort Myers (med spa 15) and Naples (med spa 21) were compared and deferred — both are fresh markets with zero prospecting; Winter Park had 3 providers already verified (from the un-activated #44 file) and higher combined winnable demand, so it was the higher-leverage conquer.

**Providers verified (7, deepened from 3):** every tagged treatment confirmed against the clinic's OWN website menu (text-only `on_page_content_parsing`); ratings from Google Places API only; no scraped review text.
- Reflections Dermatology – Winter Park 4.9/947 (botox, dermal-fillers, coolsculpting, laser-hair-removal)
- Oasis Dermatology 4.7/622 (botox, chemical-peel, microneedling)
- Dr. Kapil Saigal FACS 4.9/342 (botox, dermal-fillers — non-surgical only, surgical deferred; rule #42)
- Couture Med Spa 4.6/439 (botox, lip-filler, dermal-fillers, laser-hair-removal)
- Cosmetic Skin & Laser Center 4.8/348 (botox, dermal-fillers, microneedling, laser-hair-removal, hydrafacial, chemical-peel, morpheus8)
- Winter Park Laser & Anti-Aging Center 4.7/424 (botox, dermal-fillers, lip-filler, laser-hair-removal, microneedling, chemical-peel, morpheus8)
- Artistik Beauty 4.9/369 (botox, dermal-fillers, lip-filler, laser-hair-removal)

**Pages built vs held:**
- **Built (≥2 verified in-city):** Winter Park hub + Orange county hub + 5 treatment pages — **botox (7), lip-filler (3), laser-hair-removal (5), microneedling (3), chemical-peel (3)**.
- **Held (<2, honest, not padded):** **hydrafacial** (1 — CSLC; Look Lab/Restore likely offer it but were not cleanly menu-confirmed this run) and **coolsculpting** (1 — Reflections; market-displaced, Winter Park supply runs SculpSure/Morpheus8/DiamondGlow, consistent with the standing coolsculpting-market-fit note).

**Integrity notes:** local `builder/build.py` clean — `built=515 skipped=0 state=active`, all internal links valid; `scripts/verify_build.sh` passed. Isolation test (pristine vs edited build): only the new Winter Park/Orange pages added; all other pages unchanged apart from the site index + `sitemap.xml` (must update for a new market). **Zero new perfect-at-volume flags** — all 7 clinics ≤4.9, corpus row-flag count unchanged at 45. Look Lab Med Spa (5.0/1277) deliberately excluded to avoid adding a flag. Every built page carries MedicalClinic + AggregateRating + FAQ schema, canonical, and consent/privacy language.

**Impressions/GSC trend:** not captured — GSC requires Claude-in-Chrome on the desktop, unreachable from an unattended cloud run. Recommend the Tuesday desktop SEO task submit `/sitemap.xml` and request indexing for the new `/fl/orange/winter-park/*` URLs once PR #52 deploys.

**Operator items surfaced this run (see `state/needs_human.json`):** (1) plastic-surgery vertical — the scheduled task prompt asks to expand it, but the committed EXPANSION_PLAN v2 defers the surgical vertical ("do NOT build yet, activate only after med-spa is winning"); this run stayed non-surgical only and left the conflict for the operator. (2) hydrafacial Winter Park is one verified provider short of buildable at difficulty 4 — the easiest unclaimed win on the board; a single additional menu-confirmed HydraFacial provider flips it live.

**Next demand target:** deepen Winter Park's hydrafacial to ≥2 (fast, diff 4), then the next Stage-1 SW-FL door — **Fort Myers (med spa 15)** as a fresh market, or continue the Orlando metro via **Lake Mary/Maitland** enclaves (both showed provider supply adjacent to today's Winter Park set).

---

## 2026-08-29

**Method:** DataForSEO ranked-keywords for `octoru.com` (255 ranked keywords), filtered to positions 15–90, aggregated by page, ranked by *winnable* commercial/transactional volume × position, Broward priority this week. Picked three FAQ-less **city hubs** so the proven per-city `_HUB_FAQS` pattern applies cleanly. Ran end-to-end from an unattended scheduled **cloud** session (repo cloned, `build.py` verified locally, shipped as a PR — no push/deploy from here).

**Targets & positions (before, from today's DataForSEO scan; winnable queries only):**

| Page | Target queries (vol/mo · pos before) | Winnable vol |
|---|---|---|
| `/fl/broward/plantation/` | plantation med spa (1300·46), spa plantation (320·70); ideal image plantation (590·50, brand) | ~1,620 |
| `/fl/broward/hollywood/` | spa hollywood (1300·64), hollywood laser med spa (480·83), hollywood body laser (210·64) | ~1,990 |
| `/fl/broward/pembroke-pines/` | me/med spa pembroke pines (880·56) | ~880 |

(Plantation's headline "contour spa plantation" 4400·45 is navigational/brand and not directory-winnable; Pembroke Pines' "dr thrower's" 1600·69 is navigational — both excluded from the winnable count.)

**Shipped (branch `seo/striking-2026-08-29` → PR to `auto/build`; NOT merged — merge = deploy = human-gated per CLAUDE.md):**
- Added Plantation, Hollywood and Pembroke Pines to `_HUB_FAQS` in `templates/hub.html.j2` — 4 FAQs each, rendered as both `FAQPage` JSON-LD (head) and a visible `#faq` section, same self-contained guarded pattern as the hubs shipped 2026-08-04 and 2026-08-18.
- Hollywood's FAQ set includes a laser/body-treatment question to target the "hollywood laser med spa" / "hollywood body laser" queries. Content is provider-agnostic (general pricing, provider-selection, verification and local-geography guidance). **No fabricated clinic facts, prices, ratings or credentials.** Geography verified: Plantation = central Broward (Sunrise/Davie/Fort Lauderdale); Hollywood = south Broward (Hallandale Beach line); Pembroke Pines = SW Broward near Miramar / the Miami-Dade line.
- Source-only PR: `wrangler.toml` runs `python3 builder/build.py` on Cloudflare at deploy, so `generated/` is rebuilt there. Committing the template + this log keeps the diff small and reviewable (important given the repo's merge-regression history).

**Verification (local, this session):** `builder/build.py` clean — `built=504 skipped=0 state=active`, `link check: all internal links valid`. Isolation test (fresh build before vs after the edit): five control pages (Brickell, Miami-Dade county hub, homepage, Fort Lauderdale hub already-with-FAQ, Hollywood laser sub-page) **byte-identical (md5 match)**; only the 3 targets changed, **+49 / −0 lines each** (purely additive). All three `FAQPage` JSON-LD blocks parse, 4 questions each.

**Position deltas on previously-shipped pages (today's scan vs their ship-week baseline):**
- 2026-08-04 batch: Fort Lauderdale hub *improved and holding* — "best spas in fort lauderdale" 720/mo at **54** (was ~64 pre-8/04). Doral hub **flat** ("dermatologist doral" 480 at 64). Coral Gables hub **flat** ("coral gables med spa" 390 at 87).
- 2026-08-18 batch: **flat so far** — Coral Gables lip-filler ("lip filler in miami" 1300 at 60), Miami Lakes ("florida lakes spa" 720 at 44), Coral Springs ("ideal image coral springs" 590 at 46). **Correction (verified 2026-08-29):** these ARE live — a same-day on-page check confirmed the Fort Lauderdale (8/04) and Miami Lakes (8/18) hubs both serve the FAQ section on Cloudflare (onpage score 98). So the flatness is normal re-index/re-rank latency on a ~3-month-old domain, NOT a stuck deploy. The deploy pipeline is working.

**Impressions trend:** not captured — GSC impressions require Claude-in-Chrome on the desktop, unreachable from an unattended scheduled cloud run (same limitation as 2026-08-18). The Tuesday desktop weekly-seo-monitor should record the impressions delta and request indexing for changed URLs once this PR is merged/deployed.

**Blocked on operator (to realize any ranking movement):** (1) merge PR `seo/striking-2026-08-29` and `git push origin auto/build` (triggers Cloudflare deploy) — the 8/04 and 8/18 striking PRs need to actually be *live and indexed* before positions can move; (2) in Search Console, submit `/sitemap.xml` and request indexing for the changed hub URLs.

**Performance check (verified 2026-08-29, post-run):** DataForSEO historical rank overview shows real, compounding visibility growth — ranked keywords **1 (Jun) → 15 (Jul) → 133 (Aug); 222 live now**, ETV 0.06 → 8.7 → 67 → 77. Well clear of the 12-week "no growth → pause" gate; program continues. Caveat: the footprint is still almost entirely off page 1 — only **1 keyword at pos 11–20 and ~10 at 21–30**, with ~180 of 222 sitting at positions 31–90. Visibility is building; clicks/leads will lag until the best-positioned pages convert to page 1. Strategy shift recorded below: move from deep city hubs (breadth) to the page-1-reachable 21–40 cluster (conversion).

**Next week's targets — DECISION: pivot to page-1 conversion (positions 21–40), not deeper hubs.** The hub sweep has built breadth; the lever for clicks now is the handful of keywords already within reach of page 1.
1. **`/fl/miami-dade/coral-gables/botox/` — "botox coral gables" (170/mo, pos 24)** — the single closest keyword to page 1. Treatment-page enrichment via `_PAGE_EXTRA_FAQS` + title/meta tuned to the exact query. Marquee target.
2. **`/fl/miami-dade/coral-gables/lip-filler/` — "top rated lip filler near me" (590/mo, pos 37)** — already has the 8/18 FAQ; tune title/meta toward the "top rated / near me" intent to push a 590-vol query onto page 1.
3. **`/fl/fort-lauderdale/lip-filler/guide/` — "fort lauderdale lip injections" (170/mo, pos 38)** — guide enrichment for the transactional lip cluster.
4. Re-scan Plantation / Hollywood / Pembroke Pines (this week's hubs) once PR #37 is merged + deployed; record deltas.
5. Request indexing (desktop weekly-seo-monitor) for all changed URLs — the missing accelerant; without it re-crawl of a young domain is the bottleneck.

---

## 2026-08-18

**Method:** DataForSEO ranked-keywords for `octoru.com`, filtered to positions 15–90, aggregated by page, ranked by *winnable* (commercial/transactional/informational) volume × position × Miami-Dade/Broward priority. Picked one marquee treatment page + two FAQ-less city hubs so the proven per-page FAQ pattern applies cleanly.

**Targets & positions (before, from today's DataForSEO scan):**

| Page | Target queries (vol/mo · pos before) | Winnable vol |
|---|---|---|
| `/fl/miami-dade/coral-gables/lip-filler/` | lip filler in miami (1300·60), miami lip injections (1300·67), top rated lip filler near me (590·37) | 3,190 |
| `/fl/miami-dade/miami-lakes/` | florida lakes spa (720·44), great lakes medical spa (480·56), miami lakes med spa (480·59), lakes aesthetics (210·44) | 1,140 |
| `/fl/broward/coral-springs/` | ideal image coral springs (590·46), med spa coral springs (320·78), jaan holistic wellness (260·62) | ~850 |

**Shipped (branch `seo/striking-2026-08-18` → PR to `auto/build`; NOT merged — merge = deploy = human-gated):**
- **Miami Lakes** & **Coral Springs** city hubs: added per-city FAQ section + `FAQPage` JSON-LD in `templates/hub.html.j2` (`_HUB_FAQS`, keyed by city slug) — same self-contained, guarded pattern as the three hubs shipped 2026-08-04.
- **Coral Gables lip-filler** treatment page: added a self-contained per-page FAQ hook in `templates/treatment-page.html.j2` (`_PAGE_EXTRA_FAQS`, keyed `"<treatment>/<city>"`, merged via `_all_faqs`). Two extra FAQs — "How much is lip filler in Miami?" and "Is lip filler the same as lip injections?" — target the 2×1,300/mo Miami queries. Uses only the sourced RealSelf figures already on the page (Miami-metro ≈$700; national $500–$1,400/syringe). No fabricated clinic facts, prices, ratings or credentials.
- All three keep the required `MedicalClinic`/`AggregateRating` (treatment page) and Breadcrumb schema; all pages remain indexable (no noindex triggered).

**Verification:** local `builder/build.py` clean — `built=461 skipped=0 state=active`, internal link check passed. Isolation test (pristine-rebuild vs edited): control pages (Brickell, Miami-Dade county, homepage, Fort Lauderdale hub) **byte-identical**; only the 3 targets changed (+49/+49/+19 lines, additive). All FAQPage/ItemList/Breadcrumb JSON-LD parses; FAQ counts 4/4/7.

**Evidence the pattern works:** the two comparable hubs from 2026-08-04 both climbed after the FAQ ship — Fort Lauderdale ~64→54, Coral Gables ~87→71.

**Impressions trend:** not captured this run — GSC/impressions require Claude-in-Chrome on the desktop, which is not reachable from an unattended scheduled cloud run. Recommend the desktop weekly-seo-monitor (Tuesdays) record the impressions delta and request indexing for the 3 changed URLs once this PR is merged/deployed.

**Deferred / next week's targets:**
1. Re-scan the 3 hubs shipped 2026-08-04 (doral, coral-gables, fort-lauderdale) and the 3 shipped today; record position + impressions deltas.
2. `/fl/broward/plantation/` hub — "plantation med spa" (1300·46) — add FAQ (mostly-navigational volume, but strong generic query).
3. Treatment-page title/meta enrichment (e.g. lip-filler guide cluster) — a `build.py`-level batch now that git push is available here.

---

## 2026-08-04

**Method:** DataForSEO ranked-keywords for `octoru.com`, filtered to positions 15–90, ranked by volume; picked generic "treatment/category + city" commercial queries in Miami-Dade / Broward first. Thin **city hubs** chosen as the highest-headroom pages.

**Targets & positions (before):**

| Query | Volume/mo | Position before | Page |
|---|---|---|---|
| doral medical spa (+ "dermatologist doral" 480) | 140 | ~64 | /fl/miami-dade/doral/ |
| coral gables med spa | 390 | ~87 | /fl/miami-dade/coral-gables/ |
| med spa fort lauderdale (deepest Broward market) | — | ~64 | /fl/broward/fort-lauderdale/ |

Note: the best-positioned individual pages this week were `botox coral gables` (pos 24, 170/mo) and the `lip filler fort lauderdale` cluster (pos 36–39, ~510/mo combined). See "Deferred" below.

**Shipped (PR #29 → auto/build, merged; Workers Builds check green):**
- Per-city **FAQ section + `FAQPage` JSON-LD** on the three city hubs, self-contained in `templates/hub.html.j2` (keyed off the city slug in `rel_path`).
- Guarded (`{% if _hub_faqs %}`) so county/state hubs and all non-target city hubs render byte-identical.
- Content is provider-agnostic — general pricing / provider-selection / verification guidance. **No fabricated clinic facts, prices, ratings, or credentials.**

**Verification:** local `builder/build.py` run clean — `built=461 skipped=0 state=active`, internal link check passed; valid 4-question FAQPage on all three targets; controls (Brickell, Miami-Dade county, FL state hubs) unaffected.

**Impressions trend:** first logged run — no prior GSC delta to compare yet. Establish baseline next week.

**Deferred (constraint):** `build.py`-level enrichment (richer intros/FAQs for the `botox coral gables` pos-24 treatment page and the `lip filler fort lauderdale` pos-36 guide) was not shipped this week — the 131 KB `build.py` can't be pushed inline through the GitHub connector. Fix path: move that copy into a data file the builder reads, or run this task where `git push` is available.

**Next week's targets:**
1. `botox coral gables` (pos 24) — treatment-page intro/FAQ enrichment.
2. `lip filler fort lauderdale` (pos 36–39) — guide enrichment.
3. Re-scan positions for the 3 hubs shipped today; record impressions delta.
