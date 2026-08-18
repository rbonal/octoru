# Octoru — Striking-Distance SEO Log

A running log of the weekly striking-distance build. Newest entry on top.

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
