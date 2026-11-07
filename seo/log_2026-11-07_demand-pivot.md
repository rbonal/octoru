# 2026-11-07 — Demand pivot (monthly review)

**Decision (operator):** remove nothing; work topics with real traffic. CoolSculpting/Morpheus8 pages stay as-is; no new prospecting for them (FL volume: coolsculpting miami 390 -> 90/mo Jan->Sep; morpheus8 miami 50-110).

**Demand (DataForSEO, FL):** lip filler miami ~1,000; laser hair removal miami ~1,000; botox miami 720-1,000; med spa miami ~500-900; botox fort lauderdale ~260-390. GLP-1 terms small/falling (excluded: compliance risk).

**Shipped (templates only, additive FAQ + FAQPage schema, provider-agnostic, no invented facts/prices):**
- Hub FAQs: deerfield-beach, weston, hallandale-beach, palm-beach-gardens (hubs rank for "med spa <city>"-type terms, e.g. plantation medical spa 1300).
- Page FAQs: botox/coral-gables (170/mo, pos 30), botox/wellington (260, pos 39), laser-hair-removal/pembroke-pines (140, pos 21).

**Verification:** build.py built=553 skipped=0; verify_build.sh passed; exactly 7 generated pages differ from baseline; FAQPage JSON-LD parses on all 7.

**Next:** re-scan positions after deploy + GSC request-indexing for the 7 URLs; then plastic-surgery depth (tummy tuck miami 390, bbl miami 260).
