# Link-building plan (v3, 2026-11-27)

**Baseline (DataForSEO, 2026-11-27):** octoru.com has 34 referring main domains, backlinks
spam score 62 — effectively zero real links. **Key finding:** medspaflorida.com, which holds
5 of the top 7 results for "laser hair removal brickell", has 61 referring domains that are
also almost all spam (casino, link-generator and PBN domains). In this niche the real-link
bar is LOW: 15–25 genuine local/industry links would put Octoru ahead of the directories it
competes with. Target: 15 real referring domains by 2026-12-31 (stretch), 25 by 2027-03-31.

A "real" link = an editorially placed link from a site with its own audience and topical or
local relevance (clinic sites, local media, chambers, associations, health/beauty
publishers). Spam, PBNs, paid links, link exchanges and directory farms never count and are
never pursued.

## What Claude runs by itself (no human step)

| # | Tactic | Cadence | Output |
|---|---|---|---|
| A1 | **Verified clinic profiles + "Verified on Octoru" badge** — one indexable profile per verified clinic with an embeddable badge that links back (v3 builder patch). | once (patch) | ~262 profile pages + badge asset |
| A2 | **Data-led linkable assets** — publish one original dataset per quarter from Octoru's own verified data: Florida Botox Price Index (per-unit prices published by verified clinics; 11 clinics in the first edition, live once the v3 patch is installed), Surgical Price Transparency Report (which practices publish prices and what packages include), Board-Certification Check of listed surgeons. Each as a /learn/ page with methodology, a downloadable CSV and embed code with attribution link. | quarterly | 1 asset/quarter |
| A3 | **Outreach packs** — for every newly verified clinic and every money page, generate a personalized, ready-to-send email (profile URL, badge snippet, what was verified) into `state/outreach/`. | weekly | drafts + tracking sheet |
| A4 | **Link-gap prospecting** — DataForSEO intersection of local competitors (clinic sites, booking platforms, local directories) to find local resource pages, chambers, associations, media that link to them but not to Octoru; scored and added to `state/outreach/prospects.csv`. | monthly | prospect list |
| A5 | **Unlinked-mention reclamation** — find pages mentioning Octoru or its data without a link; draft a polite link request. | monthly | drafts |
| A6 | **Journalist/data-request matching** — watch for local news/health stories on aesthetic prices, BBL safety, med-spa regulation; draft a data-backed pitch with the relevant Octoru dataset. | weekly | drafts |
| A7 | **Internal-link engine** — hubs, learn hubs and clinic profiles link to money pages with exact-match anchors; re-checked each run. | every run | data/template changes |
| A8 | **Backlink hygiene** — monthly pull of new/lost referring domains; spam domains appended to `octoru-disavow.txt`; report real-link count (the KPI). | monthly | updated disavow file + KPI |

## What needs Rolando (hard-gated or account-bound)

- **Send outreach emails** (external recipients): approve each batch, or connect an email
  tool and approve sending; Claude never sends unapproved.
- **Upload the disavow file** in Search Console (first upload pending since 2026-09-23).
- **Create accounts** for citations (chambers, Bing Places-type listings, associations):
  Claude prepares every field; a person creates the account.
- **Install the v3 builder patch** (profiles, badge, titles, guide policy, sitemap).
- **Owned properties** (bonalta.com resource page, YouTube descriptions): Claude drafts the
  copy; publishing needs access/approval.

## Rules

Never buy links, never join exchanges/PBNs, never use comment/forum spam, never offer
rankings or placement in exchange for links (the badge is free and placement is never tied
to linking). Anchor text stays natural (brand or page title). Every outreach states that
listing on Octoru is free and independent of linking.
