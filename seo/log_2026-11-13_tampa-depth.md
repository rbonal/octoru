# Expansion run 2026-11-13 — Tampa depth (both verticals)

**Gates:** build_state active; ledger tokens unmetered/under cap; no blocking needs_human item worsened. Standing override (EXPANSION_PLAN v2.1, to 2026-12-31) respected: no new municipality, no places.json change; existing-market depth only.

**Demand (DataForSEO Google Ads volume, Florida, Nov 2026):** botox tampa 720/mo, lip filler tampa 590, breast augmentation tampa 590, rhinoplasty tampa 320, liposuction tampa 260, mommy makeover tampa 140, bbl tampa 110. Tampa had 1-3 providers on most of these pages, so it was the highest-demand existing market to deepen. For comparison, Broward/Palm Beach plastic-surgery terms were 20-90/mo (bbl fort lauderdale 30, breast augmentation fort lauderdale 90, breast augmentation boca raton 70).

**Prospected:** DataForSEO Business Listings (plastic_surgeon / cosmetic_surgeon_clinic, then medical_spa / skin_care_clinic / dermatologist) within ~10-12 km of Tampa. Menus confirmed via on_page_content_parsing (text-only) on each clinic's own site.

**Added (8 providers, data/prospector/tampa-depth-2026-11.json):**
- bŏdze Plastic Surgery and Medical Spa — 4.9/678 — bbl, tummy-tuck, breast-augmentation, liposuction, mommy-makeover, facelift, botox, laser-hair-removal, microneedling, morpheus8
- Castellano Cosmetic Surgery Center — 4.8/467 — breast-augmentation, liposuction, tummy-tuck, mommy-makeover, facelift, botox
- VIVIFY Plastic Surgery — 5.0/326 (PERFECT-AT-VOLUME FLAG) — breast-augmentation, tummy-tuck, liposuction, mommy-makeover, facelift, botox, morpheus8, chemical-peel
- William P. Mack, MD (oculoplastic/facial cosmetic) — 5.0/834 (PERFECT-AT-VOLUME FLAG) — botox, lip-filler, chemical-peel
- ImageLift Tampa — 4.8/400 — facelift, botox
- Joshua A. Halpern, M.D., P.A. — 3.8/371 — bbl, breast-augmentation, tummy-tuck, mommy-makeover, rhinoplasty, facelift, botox, morpheus8
- Sono Bello Tampa — 4.5/562 — liposuction, mommy-makeover (branded "tummy tuck alternative" NOT tagged as tummy-tuck)
- Perfectly Bare Laser — 4.9/1664 — laser-hair-removal (other services only in blog posts, not tagged)

Conservative tagging: generic "fillers" never tagged as lip-filler; nothing from review text. No published prices (request-a-quote). No before/after images.

**Pages:** 1 new page — /fl/hillsborough/tampa/morpheus8/ (3 verified: bŏdze, VIVIFY, Halpern). 13 existing Tampa treatment pages deepened (e.g. breast augmentation 2 -> 6 providers, liposuction 1 -> 5, botox 3 -> 9, rhinoplasty 1 -> 2, lip filler 2 -> 3).
**Held:** hydrafacial@tampa (still 1 verified provider: Cell Renew).

**Not added (stragglers):** Watt Plastic Surgery and Davis Facial Plastic Surgery (site fetch failed even with JS rendering — retry via browser next run; Davis would add rhinoplasty depth); Geoffrey Kwitko MD (oculoplastic eyelid only, no tracked treatment); Florida West Coast Skin & Cancer (medical derm; only a generic "facial rejuvenation" link); Tampa Mohs Surgery (medical only).

**Integrity:** two new perfect-at-volume rows (VIVIFY 5.0/326, Mack 5.0/834) — flagged in _sourcing, not altered; corpus perfect-at-volume share 22.8% -> 22.9% (provenance-gated, no halt).

**Verification (fresh clone of origin/auto/build 5fa1a00 + data file):** build.py built=554 skipped=0 (was 553); link check all valid; verify_build.sh passed; state active. Isolation: only Tampa pages + homepage/advertise counters + sitemap + completeness report changed. tampa/morpheus8 carries MedicalClinic + AggregateRating + FAQPage + canonical + privacy language.

**Next demand target:** Tampa rhinoplasty/hydrafacial depth (retry Davis Facial + Watt via browser; find a 2nd verified HydraFacial provider), then Orlando-area plastic surgery once the 12/31 override lifts (breast augmentation orlando 390/mo).
