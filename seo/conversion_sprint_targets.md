# Octoru — Conversion Sprint Target Queue (active worklist)

**Read with `seo/EXPANSION_PLAN.md` v2.1 override.** This is the concrete per-page work
queue for the conversion sprint (now → 2026-12-31). Do NOT launch new markets; work these
pages to page one. Positions are from DataForSEO ranked-keywords + Google Search Console,
2026-09-23 — **re-pull and re-rank at the start of every run** (a page that reaches page 1
graduates off this list; a slipped page is re-prioritized).

## Tier 1 — close + high-demand + commercial (work these first, in order)

| # | Page (relative_url) | Target keyword(s) | Vol/mo | Pos (2026-09-23) |
|---|---|---|---|---|
| 1 | `/fl/broward/pembroke-pines/laser-hair-removal/` | pembroke pines laser hair removal (+ "laser hair removal pembroke pines fl", "…pembroke pines") | ~140 ×3 | 14 / 16 / 21 |
| 2 | `/fl/miami-dade/doral/laser-hair-removal/` | laser hair removal doral fl | 110 | 20 |
| 3 | `/fl/miami-dade/sunny-isles-beach/` | spas in sunny isles beach | 140 | 24 |
| 4 | `/fl/miami-dade/coral-gables/botox/` | botox coral gables | 170 | 30 (slipped from 24) |
| 5 | `/fl/broward/plantation/` | plantation medical spa | 1,300 | 32 |

## Tier 2 — high demand, farther (authority-dependent; do not lead with these)

| Page | Keyword | Demand | Status |
|---|---|---|---|
| `/fl/miami-dade/key-biscayne/botox/` (build/confirm) | botox key biscayne fl | 1,445 GSC impr/mo | ~pos 40+, 0 clicks — biggest single prize once authority improves |
| `/fl/broward/hillsboro-beach/…botox` | hillsboro beach fl botox | 521 GSC impr/mo | deep |

## Per-page playbook (apply ALL, in order, to each Tier-1 page)

1. **Title tag** = exact query + hook, e.g. `Laser Hair Removal in Pembroke Pines, FL — Compare N Verified Clinics & Prices`. Keyword front-loaded.
2. **H1 + 40–60-word intro** naming city + treatment in sentence one; state what the page offers.
3. **Cost block** — "$X–$Y per session/area" from published/sourced figures only (no fabrication). Highest-value sub-intent; most competitor pages lack it.
4. **2–3 page-specific FAQs** via `_PAGE_EXTRA_FAQS` (key `"<treatment>/<city>"`) — visible text + `FAQPage` JSON-LD. Target the exact query + its People-Also-Ask. This is the pattern that moved Fort Lauderdale 64→54, Coral Gables 87→71.
5. **Thicken supply** — add 1–3 more menu-verified clinics (integrity rules unchanged: ≥2 verified, Places-API ratings, no scraped reviews, prices only where published).
6. **Internal links (exact-match anchor)** into the page from: its county hub, the sibling treatment pages in the same city, and the matching `/guide/`.
7. **Freshness + indexing** — bump `last_verified`, redeploy, then request indexing in GSC (URL Inspection) and IndexNow-ping the changed URL.

## Authority (parallel, every run — the real rate-limiter)

- **Disavow the toxic profile.** All 28 referring domains are spam (gambling/fake-news PBNs + link-generator tools, spam score 40–75). Disavow file generated 2026-09-23 (`octoru-disavow.txt`); **operator uploads it in GSC** (hard-gated). Stop whatever produced these.
- **Earn 3–5 real links** — local/business directories, a Bonalta-owned-property link, one light digital-PR mention. The site currently has ZERO legitimate links; even a handful moves a domain this young.

## Ignore (do not spend effort here)

Navigational competitor-brand queries — they don't convert to a directory: *verla aesthetics, tighter lines aesthetics, brickell cosmetic center & spa, dermaspalogy, le spa plastic surgery, dluxe medspa, vio med spa, dr thrower medspa, hass plastic surgery, ideal image hallandale, 305 plastic surgery,* etc. Report them as noise, not wins.

## Measurement + gate

Track **position on the Tier-1 queries** weekly in GSC (not ranked-keyword count). Success =
page-1 commercial rankings + real leads. **Kill criterion (2026-12-31 / ~month 6):** if not
≥1 Tier-1 keyword on page 1 AND ≥1 confirmed inbound lead, pause and reassess.
