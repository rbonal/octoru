# Octoru — Striking-Distance SEO Log

A running log of the weekly striking-distance build. Newest entry on top.

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
