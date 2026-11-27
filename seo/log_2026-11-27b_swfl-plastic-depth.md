# 2026-11-27 (run 2) — Expansion engine: Sarasota + Naples plastic-surgery depth

**Mode:** second batch of the 11/27 run (operator said "go" after PR #68 deployed). Depth only under the EXPANSION_PLAN v2.1 override: `sarasota` and `naples` are existing places; no places.json, build.py or config change. Data: new `data/prospector/swfl-plastic-depth-2026-11.json` plus surgical tags on 2 existing records in `data/prospector/sarasota.json`.

**Demand (DataForSEO Google Ads, Florida, 12-mo avg):** Sarasota: breast augmentation 110 · tummy tuck 50 · liposuction 50 · rhinoplasty 40. Naples: breast augmentation 90 · rhinoplasty 50 · tummy tuck 30 · liposuction 30. Neither city had a single surgical treatment page before this run. For comparison, bbl fort lauderdale (30) / bbl boca raton (20) were lower, so the FTL/Boca BBL one-short pages were not prioritised.

**SERP (breast augmentation sarasota, Sarasota location):** local pack = Sarasota Plastic Surgery Center, Florida Plastic Surgery (Hamwi), Sarasota Surgical Arts; organic top results are a parked for-sale domain and Sarasota Surgical Arts blog archive pages. No directory or comparison page ranks in the top 10. **Gap Octoru fills:** one page comparing every Sarasota practice that lists the procedure on its own menu, with permitted-API ratings and only first-party prices with stated scope. Primary URLs: /fl/sarasota/sarasota/{breast-augmentation,tummy-tuck,liposuction,mommy-makeover,facelift}/ and /fl/collier/naples/{breast-augmentation,tummy-tuck,liposuction,mommy-makeover,facelift,rhinoplasty}/.

**Providers added (8 new) — category plastic-surgery, procedures confirmed on each practice's own menu (text-only fetch):**
| Practice | City | Tags | Rating (API) |
|---|---|---|---|
| Sarasota Surgical Arts (Dr. Sessa) | Sarasota | facelift, breast-aug, tummy-tuck, lipo, mommy-makeover (bbl + rhinoplasty confirmed but HELD, see below) | 4.7 / 606 |
| Holcomb Kreithen Plastic Surgery | Sarasota | breast-aug, facelift, lipo, mommy-makeover, tummy-tuck | 4.9 / 233 |
| West Coast Plastic Surgery (Dr. Lambiris) | Sarasota | breast-aug, tummy-tuck, mommy-makeover, lipo, facelift, botox, lip-filler | 5.0 / 177 **flag** |
| Naples Aesthetic Institute (Dr. Kiran Gill) | Naples | facelift, breast-aug, tummy-tuck, mommy-makeover, lipo, botox, LHR | 4.9 / 238 |
| Naples Aesthetics (Dr. Kent Hasen) | Naples | breast-aug, facelift, mommy-makeover, tummy-tuck, lipo, rhinoplasty, botox | 4.7 / 231 |
| Naples Cosmetic Surgery Center (Dr. Turk) | Naples | rhinoplasty, breast-aug, mommy-makeover, tummy-tuck, botox | 4.9 / 130 |
| Peña Plastic Surgery | Naples | facelift, rhinoplasty, breast-aug, tummy-tuck, lipo, mommy-makeover, botox, LHR | 4.9 / 123 |
| Burchhardt Facial Plastic Surgery | Naples | facelift, rhinoplasty, botox | 5.0 / 57 |

**Existing records re-tagged (surgical vertical now active; previously "surgical intentionally NOT tagged — vertical deferred"):** Sarasota Plastic Surgery Center & Med Spa (+ facelift, tummy-tuck, mommy-makeover, breast-augmentation) and Florida Plastic Surgery / Dr. Hamwi (+ breast-augmentation, mommy-makeover, tummy-tuck, liposuction), each confirmed on the practice's procedure menu and recorded in a new `surgical_menu_confirmed` note. Both already rank in the Sarasota local pack for breast augmentation.

**Published offer recorded (exact scope):** Holcomb Kreithen breast augmentation "starts at approximately $8500" — basis recorded as starting-at-approximately, with the clinic's own caveat that anesthesia/facility fees, implant choice and combined procedures change the price. Not recorded: Naples CSC holiday Botox $16/unit (date-limited). Everything else → Request a quote.

**Conservative non-tags:** Sciton "BBL" laser (West Coast) ≠ Brazilian butt lift; SPSC "Excisional Butt Lift" ≠ BBL; HK rhinoplasty/botox (testimonials only); Turk facelift/liposuction (no menu page; neck/brow lift only); Turk + Peña lip augmentation (method not confirmed); Hasen CoolSculpting (operator coolsculpting decision pending — not prospected); Gill lip filler (only inside the general filler copy).

**Pages built vs held:**
- New (11): Sarasota breast-augmentation (5), tummy-tuck (5), mommy-makeover (5), liposuction (4), facelift (4); Naples breast-augmentation (4), tummy-tuck (4), mommy-makeover (4), facelift (4), rhinoplasty (4), liposuction (3) — each with a guide.
- Deepened: Naples botox and laser-hair-removal; Sarasota botox and lip-filler.
- **Held (2): bbl@sarasota and rhinoplasty@sarasota** — only Sarasota Surgical Arts verified. config/thresholds.json allows single-provider plastic-surgery pages, but this run's rule is ≥2 or held, so the two tags are recorded in `confirmed_not_listed` and the `_sourcing` note and NOT published. Add them when a second Sarasota provider is verified. bbl@naples: no verified provider.

**Verification (fresh clone of origin/auto/build 6621f65 = after PR #68, clean `generated/` incl. ignored files):** built 567 → 578, skipped=0, all internal links valid, verify_build.sh PASS, state active, sitemap 775 → 797 (11 pages + 11 guides). Isolation: only the 11 new dirs plus additive cross-links/hub cards on Sarasota/Collier and nearby pages. New pages carry MedicalClinic + AggregateRating + FAQPage schema, canonical, privacy language, indexable. Integrity: row flags 53 → 54 (West Coast PS 5.0/177 flagged on-record); share 23.3%, provenance-gated, no halt. Note for future runs: an earlier local build left stale ignored files in generated/ that briefly caused a false broken-link failure; always `git clean -fdx generated` before the isolation build.

**Measurement:** nonbrand clicks, tel: clicks and verified qualified inquiries tracked separately; Bonalta Connect inquiry delivery still UNVERIFIED (form has no endpoint). Request indexing for the 11 new URLs after deploy.

**Next demand target:** second Sarasota provider for rhinoplasty / BBL (would release the two held pages); morpheus8@miami second provider; Winter Park plastic-surgery depth.
