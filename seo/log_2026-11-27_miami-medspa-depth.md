# 2026-11-27 — Expansion engine: Miami (city) med-spa depth

**Mode:** depth-only under EXPANSION_PLAN v2.1 override (no new municipality; `miami` already exists in data/places.json). No places.json, build.py or config change. Gates: build_state active; no 2026-11 ledger usage against the 5M cap; needs_human items are non-blocking (lead form endpoint + coolsculpting decision — this run does not touch either; no coolsculpting prospecting).

**Why Miami med-spa (demand, DataForSEO Google Ads, Florida, 12-mo avg / KD):** laser hair removal miami 1,000 (KD 0) · botox miami 880 (KD 9) · lip filler miami 880 (KD 0) · microneedling miami 480 (KD 0) · hydrafacial miami 260 (KD 0) · morpheus8 miami 140 (KD 0) · chemical peel miami 90 (KD 0). Highest unbuilt demand in the footprint: before this run Miami proper had **zero** in-city providers for LHR, microneedling, HydraFacial, chemical peel and Morpheus8, and only 2 for botox / lip filler (both plastic-surgery practices from 11/20).

**SERP check (hydrafacial miami, Miami location):** local pack (LUX MedSpa Brickell, LumiVita Brickell, Dolce) + AI overview, then the hydrafacial.com provider finder (#1 organic), single-clinic pages, and Yelp's "Top 10 Best Hydrafacial in Miami" list. Directories rank → winnable. **Gap Octoru fills:** a multi-provider comparison of clinics whose treatment is confirmed on their own menu, with permitted-API ratings and only first-party published prices with basis (no review-text lists, no brand finder bias). Primary URLs: /fl/miami-dade/miami/{laser-hair-removal,microneedling,hydrafacial,chemical-peel}/ (new) and /fl/miami-dade/miami/{botox,lip-filler}/ (refreshed, same intent — not duplicated).

**Prospecting:** DataForSEO Business Listings (Google Maps source), categories medical spa / dermatologist / skin care clinic / laser hair removal / plastic surgeon, 5 km around 25.80,-80.195, top 50 by review volume. Excluded Brickell zips (33129/33130/33131 — already Brickell) and Midtown-convention addresses; text-only menu fetch (DataForSEO on_page_content_parsing) for each candidate.

**Providers added (6; data/prospector/miami-medspa-depth-2026-11.json):**
| Practice | Area | Category | Tags (menu-confirmed) | Rating (API) |
|---|---|---|---|---|
| Zeugma MedSpa | Edgewater | med-spa | botox, hydrafacial, microneedling, chemical-peel | 4.9 / 291 |
| NuYou Medical Aesthetics | Downtown | med-spa | botox, lip-filler, dermal-fillers, microneedling, chemical-peel, hydrafacial | 5.0 / 504 **flag** |
| Elda Silva Studio & MedSpa | Edgewater | med-spa | botox, dermal-fillers, morpheus8 | 5.0 / 675 **flag** |
| Barba Dermatology | Upper East Side | dermatology (rule #42) | botox, lip-filler, dermal-fillers | 4.8 / 379 |
| Designer Aesthetics (Dr. Jarrett Schanzer) | Upper East Side | med-spa | botox, lip-filler, dermal-fillers, microneedling, chemical-peel, laser-hair-removal, iv-therapy | 5.0 / 325 **flag** |
| Skn Elements | Little River | med-spa | laser-hair-removal, microneedling | 4.9 / 237 |

**Published offers recorded (exact scope, first-party, checked 2026-11-27):** Zeugma Botox $13 per unit (Botox; APRN; new-client 20% discount not applied) · Zeugma HydraFacial Signature $250 per session, regular single-visit price (membership/intro excluded). Zeugma's November microneedling promos (end Nov 30) deliberately not recorded. Everything else renders Request a quote. No offers grouped (only one priced provider per treatment).

**Conservative non-tags / exclusions:** Elda Silva lip filler (no lip offer on menu); Barba LHR + peels (offered by affiliated Barba Skin Clinic, separate site/phone, location unconfirmed); Skn Elements botox (testimonial only); Zeugma Vivace ≠ morpheus8. Excluded candidates: Feel The Heal (primary business is a colonic/wellness spa — HydraFacial on menu, but would mislabel category), Design Dermatology/Goldman Dermatology ("injectables, lasers" only, no specific menu), White Coat Beauty (no specific menu on page fetched), Elite Styles (site not parseable), Latitude Dermatology (site is an alliance directory), Randy Lindgren MD (fillers only — no buildable page; skipped to avoid an extra perfect-at-volume row with no page benefit).

**Pages built vs held:**
- New (4): /fl/miami-dade/miami/laser-hair-removal/ (2), /microneedling/ (4), /hydrafacial/ (2), /chemical-peel/ (3) + guides.
- Deepened (2): /fl/miami-dade/miami/botox/ 2 → 7 providers, /lip-filler/ 2 → 5.
- Held (1): morpheus8@miami — 1 verified in-city provider (Elda Silva); never padded. iv-therapy / dermal-fillers tags are recorded but those treatments are not in build scope.

**Verification (fresh clone of origin/auto/build a4869ea + data file):** built 563 → 567, skipped=0, all internal links valid, verify_build.sh PASS, state active. Sitemap 767 → 775 URLs (4 pages + 4 guides). Isolation: diff vs clean rebuild of a4869ea = the 4 new dirs + additive "in Miami" sibling links on nearby Miami-Dade treatment pages/guides/hubs; no removals. New pages carry MedicalClinic + AggregateRating + FAQPage schema, canonical (https://octoru.com/fl/miami-dade/miami/<t>/), privacy language, indexable. Integrity: perfect-at-volume share 22.7% → 23.3%, row flags 50 → 53 (provenance-gated, no halt; all three new flags recorded on the rows).

**Measurement note:** nonbrand clicks, direct clinic contact (tel:) clicks and verified qualified inquiries are tracked separately; Bonalta Connect inquiry delivery remains UNVERIFIED (treatment-page form has no endpoint — see needs_human monthly-review-2026-11-16). Request indexing for the 6 Miami URLs after deploy (Tuesday desktop SEO task).

**Next demand target:** morpheus8 miami (140/mo) needs one more verified in-city provider; then Fort Lauderdale / Boca BBL depth (both one-short at 1 provider) and Naples/Sarasota plastic-surgery depth (breast augmentation 90–110/mo, zero surgical providers today).
