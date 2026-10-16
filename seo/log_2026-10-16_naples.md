## 2026-10-16 — Expansion engine: Naples (Collier) launch

**Gates:** build_state active; token ledger under cap; no blocking needs_human item worsened.

**Demand (DataForSEO, staged 2026-09-11):** botox naples 480/mo KD 14; laser hair removal naples 260/mo KD 1; medical spa naples fl 260/mo KD 17; lip filler naples 110/mo. All KD <= 24 (winnable zone). 2026-10-16 spot check of Tampa/Orlando volumes: med spa tampa 1000/mo, med spa orlando 880/mo, botox orlando 1000/mo, tummy tuck orlando 260/mo -> next candidates.

**Shipped (data only):** data/prospector/naples.json (5 providers, menu-confirmed on own sites 2026-09-11: 2 dermatology, 3 med-spa; rule 42) + data/places.json Naples/Collier entry. Pages: /fl/collier/, /fl/collier/naples/, and 6 treatment pages (botox, lip-filler, microneedling, chemical-peel, hydrafacial, laser-hair-removal).

**Held:** coolsculpting, morpheus8, dermal-fillers etc. (<2 verified in-city providers); plastic-surgery vertical for Naples not yet prospected.

**Integrity:** ratings Google Places API only; no scraped review text; no prices (request-a-quote); no before/after. Flagged perfect-at-volume: Naples Vision of Beauty 5.0/285, Revital 5.0/375 (real data, standing override).

**Verification:** fresh worktree of origin/auto/build e47fc24 + data: built=540 skipped=0, verify_build.sh PASS, links valid, 25 defs, canonical present, state active. Naples treatment pages carry MedicalClinic + AggregateRating + FAQPage + canonical + privacy/consent language.

**Next target:** Orlando/Tampa med-spa and Orlando tummy-tuck (plastic-surgery) prospecting; Naples plastic-surgery clinics. Fold this entry into seo/striking_distance_log.md at next convenience.
