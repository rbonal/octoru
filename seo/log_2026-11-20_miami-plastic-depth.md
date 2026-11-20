# 2026-11-20 — Expansion engine: Miami (city) plastic-surgery depth

**Mode:** depth-only under EXPANSION_PLAN v2.1 override (no new municipality; `miami` already exists in data/places.json as the parent of brickell/midtown/coconut-grove/kendall). No places.json, build.py or config change.

**Demand (DataForSEO Google Ads, Florida, 12-mo avg):** breast augmentation miami 880 · rhinoplasty miami 590 · liposuction miami 480 · tummy tuck miami 390. For comparison the Broward/Palm Beach equivalents are 20–90/mo; morpheus8 city terms are 0–20/mo (Miami 140), so morpheus8 one-short pages were not prioritised.

**SERP check (breast augmentation miami, Miami location):** local pack (CG Cosmetic, Nathan Clinic, Miami Plastic Surgery) + single-practice pages + two directory/list pages (MedicalTourism.com, Yelp). Gap Octoru fills: a multi-provider comparison of practices whose procedure is confirmed on their own site, with ratings from a permitted API and honest request-a-quote pricing. Before this run, Miami proper had **zero** in-city plastic-surgery providers in Octoru (Miami pages fell back to nearest-provider lists).

**Providers added (7; every tag confirmed on the clinic's own procedure menu; ratings/address/phone from DataForSEO Business Listings):**
| Practice | Place | Tags | Rating |
|---|---|---|---|
| The Nathan Clinic | miami | bbl, tummy-tuck, breast-aug, lipo, rhinoplasty, mommy-makeover, facelift, botox, lip-filler | 5.0 / 418 (**perfect-at-volume flag**) |
| Gallagher Plastic Surgery | miami | tummy-tuck, breast-aug, lipo, mommy-makeover | 4.4 / 163 |
| The Maercks Institute | miami | all 7 surgical | 4.2 / 112 |
| DRG Cosmetic Surgery (Gershenbaum) | miami | tummy-tuck, breast-aug, lipo, rhinoplasty, mommy-makeover, facelift | 4.6 / 176 |
| Aestira Plastic Surgery | miami | tummy-tuck, breast-aug, lipo, rhinoplasty, facelift | 4.8 / 21 |
| Face Miami (Kallman) | miami | rhinoplasty, facelift, breast-aug, botox, lip-filler | 4.9 / 29 |
| Enso Plastic Surgery | brickell | tummy-tuck, rhinoplasty | 4.9 / 51 |

Conservative non-tags: Gallagher "BBL reduction" ≠ bbl; Gershenbaum buttock implants ≠ bbl; Aestira botox (testimonials only); Enso fat-transfer-to-breast and facelift (testimonial only); generic "injectables" not tagged.

**Pages:** 9 new indexable treatment pages under /fl/miami-dade/miami/ — bbl (2), tummy-tuck (5), breast-augmentation (6), liposuction (5), rhinoplasty (5), mommy-makeover (4), facelift (5), botox (2), lip-filler (2) — plus their guides; /fl/miami-dade/brickell/rhinoplasty/ now has 2 in-city providers. Held: none new (every new page has ≥2 verified providers). Nearest-provider fallback lists on neighbouring Miami-Dade pages re-rank to include the closer Miami practices (expected).

**Verification:** fresh clone of auto/build 3e30b64 + data file: built 554→563 skipped=0, all internal links valid, verify_build.sh PASS, state active. New pages carry MedicalClinic + AggregateRating + FAQPage + BreadcrumbList + ItemList schema, canonical, privacy language. Integrity share 22.7% (provenance-gated, no halt).

**Also this run:** PR #65 (Tampa depth) had been blocked for a week by a stuck "Workers Builds" GitHub check (Cloudflare deploy itself succeeded). Updated the PR branch from auto/build to re-trigger checks after verifying #65+#66 builds green locally (554, skipped=0); pipeline auto-merged it 2026-11-20 13:16 UTC.

**Next demand target:** Miami (city) med-spa depth (botox/lip-filler pages have only 2 providers) and Fort Lauderdale/Boca breast-augmentation + liposuction depth (70–90/mo each).
