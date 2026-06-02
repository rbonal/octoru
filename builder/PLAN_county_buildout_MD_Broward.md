# County Build-Out — Miami-Dade (34) + Broward (31), complete municipality lists

**Goal:** cover every municipality that has real med-spa density. Tiny/industrial towns with
no providers get **NO page** (quality gate: better none than empty). Status is operator-owned
in `seed_scope.geo`; the builder builds only `active` markets with ≥ completeness threshold.

Legend: ✅ done (staged) · 🎯 target (prospect) · ⚪ low/none (skip unless a real provider shows) ·
Note: City of **Miami** and **Miami Beach** are split into search-relevant neighborhoods.

## Miami-Dade — 34 municipalities (+ key neighborhoods/CDPs)
| Municipality / area | Status |
|---|---|
| Miami → Brickell | ✅ |
| Miami → Coconut Grove | ✅ |
| Miami → Wynwood/Midtown | 🎯 |
| Miami → Downtown | 🎯 |
| Miami Beach → South Beach | ✅ |
| Miami Beach → Mid/North Beach | 🎯 |
| Coral Gables | ✅ |
| Aventura | ✅ |
| Doral | ✅ |
| Kendall (CDP) | ✅ |
| Miami Lakes | ✅ |
| Hialeah | 🎯 |
| Homestead | 🎯 |
| Pinecrest | 🎯 |
| Sunny Isles Beach | 🎯 |
| North Miami | 🎯 |
| North Miami Beach | 🎯 |
| Miami Gardens | 🎯 |
| Cutler Bay | 🎯 |
| Palmetto Bay | 🎯 |
| South Miami | 🎯 |
| Sweetwater | 🎯 |
| Key Biscayne | 🎯 |
| Bal Harbour | 🎯 |
| Surfside | 🎯 |
| Bay Harbor Islands | 🎯 |
| Miami Shores | 🎯 |
| Miami Springs | 🎯 |
| Hialeah Gardens | ⚪ |
| Florida City | ⚪ |
| Opa-locka | ⚪ |
| North Bay Village | ⚪ |
| El Portal · Biscayne Park · Medley · Virginia Gardens · West Miami · Golden Beach · Indian Creek | ⚪ (tiny/industrial — likely no med spas → no page) |

## Broward — 31 municipalities
| Municipality | Status |
|---|---|
| Fort Lauderdale | ✅ |
| Hollywood | ✅ |
| Weston | ✅ |
| Pembroke Pines | ✅ |
| Coral Springs | 🎯 |
| Plantation | 🎯 |
| Pompano Beach | 🎯 |
| Davie | 🎯 |
| Miramar | 🎯 |
| Sunrise | 🎯 |
| Tamarac | 🎯 |
| Coconut Creek | 🎯 |
| Deerfield Beach | 🎯 |
| Dania Beach | 🎯 |
| Hallandale Beach | 🎯 |
| Lauderhill | 🎯 |
| Margate | 🎯 |
| Oakland Park | 🎯 |
| Wilton Manors | 🎯 |
| Parkland | 🎯 |
| Cooper City | 🎯 |
| Lighthouse Point | 🎯 |
| Lauderdale-by-the-Sea | 🎯 |
| North Lauderdale | ⚪ |
| Lauderdale Lakes | ⚪ |
| Dania Beach (covered) | — |
| Southwest Ranches | ⚪ (rural) |
| Hillsboro Beach · Sea Ranch Lakes · Lazy Lake · Pembroke Park · West Park | ⚪ (tiny → no page) |

## Scale & cadence (honest)
- **~22 target cities remain in Miami-Dade, ~20 in Broward** = ~40 more markets to prospect. That's
  **many batches** (each market = ~1 search + a few fetches), not one pass.
- The **~20 tiny/⚪ towns get no page** unless a real provider surfaces — that's correct, not a gap.
- Every staged market still needs the **ratings pass + config activation** to ship. Recommend
  interleaving: finish a batch of cities → one ratings pass + config flip → ship → repeat.

## The complete geo tree (operator copies to config seed_scope.geo; builder builds only `active`)
Encode all 🎯/✅ cities under `fl.counties.{miami-dade,broward}.cities` with `status:"planned"`
until each has data; flip to `"active"` once a city clears completeness with rated clinics.
