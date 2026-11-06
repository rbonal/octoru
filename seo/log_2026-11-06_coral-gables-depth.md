# Expansion run 2026-11-06 — Coral Gables plastic-surgery depth

**Gates:** build_state active; token ledger under cap; no blocking needs_human item worsened. Standing override (EXPANSION_PLAN v2.1, until 2026-12-31) respected: no new municipality launched; existing-market depth only.

**Demand (DataForSEO Google Ads volume, FL):** tummy tuck miami 390/mo, bbl miami 260, bbl tampa 170, bbl orlando 70, tummy tuck fort lauderdale 40, bbl fort lauderdale 30. The 34 held med-spa pages are ~10-20 searches/mo each (e.g. morpheus8 fort lauderdale 20, coolsculpting coral gables 10, morpheus8 coral gables 10), so filling them is low value; plastic-surgery depth in the Miami core was prioritized.

**Prospected:** DataForSEO Business Listings (plastic surgeon / clinic categories) around Miami core, Fort Lauderdale and Kendall. Yield was low: category filters return many non-plastic surgeons (orthopedic, bariatric, ob-gyn), which were rejected.

**Added (1 provider):** 305 Plastic Surgery Coral Gables — 4.1 / 2590 reviews (Google API). Menu confirmed on own site: bbl, liposuction, tummy-tuck, breast-augmentation, mommy-makeover. Facelift/rhinoplasty not listed so not tagged. No published prices (request-a-quote). Not a perfect-at-volume row (4.1).

**Pages:** 5 existing Coral Gables plastic-surgery pages gain a provider; 0 new pages; 34 held pages unchanged (all med-spa, one qualifying provider short).

**Not added (geo ambiguity, left for a places.json decision):** Spectrum Aesthetics (51 SW 42nd Ave, Miami 33134), Beautyland Plastic Surgery (1790 SW 27th Ave, Miami 33145), Miami Surgical Center Cosmetics (5733 NW 7th St, Miami 33126), Zuriarrain Plastic Surgery (South Miami 33143, 5.0/325 would trip the perfect-at-volume flag). None map cleanly to an existing place slug; filing them under a guessed neighborhood would misstate location. Menus for these were NOT verified this run.

**Verification (fresh clone of auto/build 127b483 + data file):** build.py built=553 skipped=0; link check all valid; verify_build.sh passed; integrity perfect-at-volume 22.8% (provenance-gated, no halt); coral-gables/bbl page carries MedicalClinic + AggregateRating + FAQPage + BreadcrumbList + canonical.

**Next demand target:** add places.json entries (operator-owned file) for South Miami / Little Havana-type areas so Miami plastic surgeons can be filed accurately, then verify menus for Spectrum, Beautyland, Miami Surgical Center. After 12/31 override ends: Tampa/Orlando/Naples plastic-surgery depth (bbl tampa 170/mo).
