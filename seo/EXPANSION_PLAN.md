# Octoru — Growth Plan (Standing Order)

**Version 3 · 2026-11-27 · approved by the operator (Rolando) in chat on 2026-11-27.**
Supersedes v2 (2026-08-30) and the v2.1 conversion-sprint override (2026-09-22).
Human-facing version: the "Octoru Click Strategy — Page One in Every Category" doc
(https://claude.ai/artifact/Kuadaq6ZfwnGYMhigzGBWk). Read this file at the start of every run.
Reviewed and improved every quarter (see "Quarterly review").

## Prime directive

**Clicks and leads, not pages.** A page earns work only if it can reach page one, and it
gets all the work it needs to get there. Success = commercial keywords in positions 1–10,
non-brand clicks, phone taps / outbound clinic clicks, and verified qualified inquiries.
Ranked-keyword counts, pages built and providers added are NOT success metrics.

## The four pillars

1. **Concentrate on money pages.** The active queue lives in `seo/money_page_queue.md`.
   A money page passes three tests: demand (≥50 searches/mo for a city head term, or ≥200
   for a cost query; navigational clinic-name queries never count), reach (already at
   11–30, or page one holds ≥2 weak directories), supply (≥4 verified providers, or a plan
   to reach 4 within two runs). ≥70% of every weekly run goes to the queue. A page graduates
   after 4 straight weeks at positions 1–5; it is dropped if 8 weeks of full work move it
   <5 positions.
2. **Beat the live top three.** Before working a money page, open its live page one and
   list what the top 3 offer; the Octoru page must offer all of it plus the comparison.
   Money-page standard: ≥4 verified providers; comparison table at the top; each clinic's
   published offer with exact scope (unit, area, inclusions, date checked) and a local
   range computed from those offers; verified credentials (ABPS board certification for
   surgeons, licence type for injectors) with check date; a direct answer in the first
   paragraph; FAQs from the live "People also ask"; true freshness (recheck every 30 days);
   Spanish versions for Miami-Dade/Broward money pages; links to verified clinic profiles.
   Surgery: the cost guide leads. Med-spa: the comparison page leads.
3. **Earn authority on purpose.** See `seo/link_building.md`. Internal links first
   (hubs → money pages with exact-match anchors; learn ↔ money pages), then the verified
   clinic badge, data-led PR, local citations. Never buy links or join link networks.
4. **Win the click and the lead.** Titles/descriptions from the v3 templates (price only
   when published and unit-consistent; rating range; year; count). Quote form must reach
   the approved Bonalta CRM endpoint before any inquiry is called delivered.

## Category roles

- **Plastic surgery: ACTIVE** (replaces "deferred"). Metro cities with demand only (Miami,
  Tampa, Fort Lauderdale, Sarasota, Naples, Coral Gables). Priority: breast augmentation >
  liposuction > BBL > rhinoplasty > tummy tuck / mommy makeover > facelift. Package scope
  recorded and shown. ≥2 verified practices to publish, ≥4 for a money page.
- **Med-spa:** laser hair removal = lead cluster; Botox and lip filler = grow (unit/syringe
  price is the click driver); microneedling, HydraFacial, chemical peel = hold; Morpheus8 =
  Miami only; CoolSculpting = stop prospecting (keep live pages).

## Expansion (second priority)

Allowed only after the week's queue work is done, and only where new pages would start
with ≥4 verified providers and the demand test passes. New municipalities ship as data
(`data/prospector/<market>.json` + `data/places.json`), winnability zone ≈ difficulty ≤24,
enclave-first in new metros. No market is pre-committed.

## Index hygiene

Cost guides are indexed per `data/seo/guide_policy.json` (surgical guides with ≥2 verified
practices + an allow-list of med-spa guides with demand); all others are noindex,follow and
out of the sitemap. /learn/ is being consolidated into 6 deep treatment hubs. Sitemap
`lastmod` = the date the page's data was last verified. (Requires the v3 builder patch:
`state/proposed/2026-11-27-click-strategy-v3.patch`, operator-installed.)

## Integrity guardrails (unchanged, non-negotiable)

≥2 real verified providers per page or held/rolled up, never padded · ratings only from
permitted Google APIs · no scraped review text · every treatment tag confirmed on the
clinic's own menu · prices only where published, with scope; date-limited promos not
recorded as "from" prices · no before/after images without recorded consent · nothing
fabricated · every change passes build-verify before it can go live.

## Measurement

Search Console is the source of truth for impressions, clicks, CTR and position (weekly,
Tuesday desktop task). Analytics events for phone taps, outbound clinic clicks and quote
submissions. CRM for verified qualified inquiries. DataForSEO only for discovery and for
SERP/competitor checks; never report its estimates as clicks.

## Checkpoints

- **2026-12-31 (operator gate):** ≥1 commercial keyword on page one AND ≥1 confirmed inbound
  lead. If missed only because the lead path is not connected, fix the lead path before
  deciding to pause.
- **2027-03-31:** 10 queue pages in positions 1–10 · 300 non-brand clicks/month · 25 real
  referring domains · 10 verified qualified inquiries/month.

## Quarterly review (first business days of Jan, Apr, Jul, Oct)

A scheduled run re-measures every metric above (Search Console when reachable, otherwise
labeled estimates), re-checks the live page one for every queue page, re-ranks the queue,
checks each pillar against results, and updates this file, `seo/money_page_queue.md`,
`seo/link_building.md` and the strategy doc with a dated "What changed this quarter" entry.
Changes to config/, CLAUDE.md, secrets or builder logic are proposed, never applied.
