# Octoru — Striking-Distance SEO Log

A running log of the weekly striking-distance build. Newest entry on top.

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
- 2026-08-18 batch: **flat** across the board — Coral Gables lip-filler ("lip filler in miami" 1300 at 60), Miami Lakes ("florida lakes spa" 720 at 44), Coral Springs ("ideal image coral springs" 590 at 46). Expected: as of the 2026-08-18 handoff the operator's `git push`/deploy and indexing request were still outstanding, so that batch may not be live/indexed yet.

**Impressions trend:** not captured — GSC impressions require Claude-in-Chrome on the desktop, unreachable from an unattended scheduled cloud run (same limitation as 2026-08-18). The Tuesday desktop weekly-seo-monitor should record the impressions delta and request indexing for changed URLs once this PR is merged/deployed.

**Blocked on operator (to realize any ranking movement):** (1) merge PR `seo/striking-2026-08-29` and `git push origin auto/build` (triggers Cloudflare deploy) — the 8/04 and 8/18 striking PRs need to actually be *live and indexed* before positions can move; (2) in Search Console, submit `/sitemap.xml` and request indexing for the changed hub URLs.

**Next week's targets:**
1. Re-scan Plantation / Hollywood / Pembroke Pines and record deltas once deployed + indexed.
2. Confirm whether the 2026-08-18 batch (Coral Gables lip-filler, Miami Lakes, Coral Springs) actually deployed; if still flat after deploy+indexing, revisit angle.
3. Hollywood laser cluster and `/fl/broward/pembroke-pines/` treatment sub-pages — evaluate treatment-page (`_PAGE_EXTRA_FAQS`) enrichment for the transactional laser queries.

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
