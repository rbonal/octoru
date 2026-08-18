# Worklist — unlock held pages & close the pricing gap
Generated 2026-08-18 by the builder from `data/prospector/clinics.json`.
Two independent jobs. Job A ships pages; Job B makes the pages worth ranking.

## Job A — one clinic short
Each city below has exactly ONE qualifying clinic for that treatment and needs a second to clear `min_listings=2`. One rated, phoned, addressed clinic ships one whole page.

### botox — 2 pages (live now)
- **dania-beach** — has `AlluraMD Aesthetics + Wellness`; find 1 more
- **midtown** — has `Skin Local`; find 1 more

### lip-filler — 6 pages (live now)
- **coconut-creek** — has `Helios Med Spa`; find 1 more
- **dania-beach** — has `AlluraMD Aesthetics + Wellness`; find 1 more
- **doral** — has `Facial Mania Med Spa (Doral)`; find 1 more
- **midtown** — has `Skin Local`; find 1 more
- **miramar** — has `BloomHaus MedSpa`; find 1 more
- **sunny-isles-beach** — has `Rejuvenation Medical Aesthetics & Spa`; find 1 more

### coolsculpting — 10 pages (live now)
- **boynton-beach** — has `AlluraMD Aesthetics (Boynton Beach)`; find 1 more
- **coral-gables** — has `Facial Mania Med Spa (Coral Gables)`; find 1 more
- **doral** — has `Facial Mania Med Spa (Doral)`; find 1 more
- **kendall** — has `Facial Mania Med Spa (Kendall)`; find 1 more
- **oakland-park** — has `BeWell MedSpa`; find 1 more
- **palm-beach-gardens** — has `VIO Med Spa (Palm Beach Gardens)`; find 1 more
- **parkland** — has `4Ever Young Parkland`; find 1 more
- **pembroke-pines** — has `Danik MedSpa`; find 1 more
- **south-beach** — has `LaserAway (Miami - South Beach)`; find 1 more
- **weston** — has `GreeneMD`; find 1 more

### laser-hair-removal — 10 pages (live now)
- **boca-raton** — has `Cosmetica Med Spa`; find 1 more
- **davie** — has `Icon MD Medical Spa & Laser Center`; find 1 more
- **hallandale-beach** — has `VIP Aesthetic Center`; find 1 more
- **key-biscayne** — has `My 1 Med Spa`; find 1 more
- **midtown** — has `Skin Local`; find 1 more
- **north-miami** — has `Verla Aesthetics`; find 1 more
- **plantation** — has `Sage Wellness and Medspa`; find 1 more
- **surfside** — has `Savou Med Spa (Surfside)`; find 1 more
- **wellington** — has `Wellington Rejuvenation Center`; find 1 more
- **weston** — has `GreeneMD`; find 1 more

### microneedling — 5 pages (live now)
- **bal-harbour** — has `Savou Med Spa (Bal Harbour)`; find 1 more
- **coconut-creek** — has `Helios Med Spa`; find 1 more
- **hallandale-beach** — has `Estetika Med Spa`; find 1 more
- **midtown** — has `Skin Local`; find 1 more
- **wellington** — has `Wellington Rejuvenation Center`; find 1 more

### morpheus8 — 7 pages (needs config activation first)
- **coral-gables** — has `Med Aesthetics Miami (Coral Gables)`; find 1 more
- **fort-lauderdale** — has `Amaira Med Spa & Surgical`; find 1 more
- **oakland-park** — has `VIO Med Spa (Oakland Park)`; find 1 more
- **palm-beach-gardens** — has `VIO Med Spa (Palm Beach Gardens)`; find 1 more
- **parkland** — has `4Ever Young Parkland`; find 1 more
- **plantation** — has `4Ever Young Plantation`; find 1 more
- **weston** — has `4Ever Young Weston`; find 1 more

**Total: 40 pages unlockable, one clinic each.**

City clusters worth prospecting first (appear across the most treatments):
- **midtown** — unlocks 4 pages
- **weston** — unlocks 3 pages
- **dania-beach** — unlocks 2 pages
- **doral** — unlocks 2 pages
- **coconut-creek** — unlocks 2 pages
- **coral-gables** — unlocks 2 pages
- **oakland-park** — unlocks 2 pages
- **parkland** — unlocks 2 pages
- **palm-beach-gardens** — unlocks 2 pages
- **plantation** — unlocks 2 pages

## Job B — the pricing gap
`price_empty_state_listings=1643 / 1648`. Almost every listing renders "request a quote", and every page falls back to the generic `a_no_prices` FAQ instead of the data-backed `a_prices` variant. This is the single biggest differentiator the directory is not using.

| treatment | priced / qualifying |
|---|---|
| botox | 5 / 117 |
| lip-filler | 0 / 96 |
| coolsculpting | 0 / 16 |
| laser-hair-removal | 0 / 81 |
| microneedling | 0 / 105 |
| hydrafacial | 2 / 13 |
| chemical-peel | 0 / 13 |
| dermal-fillers | 0 / 10 |
| iv-therapy | 0 / 8 |
| morpheus8 | 0 / 13 |

### Highest-yield clinics to price
Each already lists these treatments but publishes no starting price. Source order per CLAUDE.md: Places API -> clinic's own website -> clinic-claimed. Never impute a number to a clinic that didn't report one.

- **Brickell Cosmetic Center** (brickell) — 7 missing: lip-filler, laser-hair-removal, microneedling, hydrafacial, chemical-peel, dermal-fillers, morpheus8
- **Facial Mania Med Spa (Coral Gables)** (coral-gables) — 7 missing: botox, lip-filler, coolsculpting, laser-hair-removal, microneedling, chemical-peel, dermal-fillers
- **Amaira Med Spa & Surgical** (fort-lauderdale) — 7 missing: botox, lip-filler, microneedling, hydrafacial, chemical-peel, dermal-fillers, morpheus8
- **Med Aesthetics Miami (Aventura)** (aventura) — 7 missing: botox, lip-filler, laser-hair-removal, microneedling, hydrafacial, chemical-peel, morpheus8
- **Facial Mania Med Spa (Delray Beach)** (delray-beach) — 7 missing: botox, lip-filler, coolsculpting, laser-hair-removal, microneedling, chemical-peel, dermal-fillers
- **Delray Laser and Medical Spa** (delray-beach) — 7 missing: botox, lip-filler, coolsculpting, laser-hair-removal, microneedling, hydrafacial, chemical-peel
- **Amaira Med Spa (Delray Beach)** (delray-beach) — 7 missing: botox, lip-filler, microneedling, hydrafacial, chemical-peel, dermal-fillers, morpheus8
- **4Ever Young Aventura** (aventura) — 6 missing: botox, lip-filler, microneedling, hydrafacial, chemical-peel, morpheus8
- **Facial Mania Med Spa (Doral)** (doral) — 6 missing: botox, lip-filler, coolsculpting, laser-hair-removal, microneedling, iv-therapy
- **4Ever Young Parkland** (parkland) — 6 missing: botox, lip-filler, coolsculpting, microneedling, iv-therapy, morpheus8
- **VIO Med Spa (Palm Beach Gardens)** (palm-beach-gardens) — 6 missing: botox, lip-filler, coolsculpting, laser-hair-removal, microneedling, morpheus8
- **Med Aesthetics Miami (Coral Gables)** (coral-gables) — 5 missing: laser-hair-removal, microneedling, hydrafacial, chemical-peel, morpheus8
- **Dermacare MD (Brickell)** (brickell) — 5 missing: botox, lip-filler, laser-hair-removal, microneedling, morpheus8
- **Ideal Image (Las Olas)** (fort-lauderdale) — 5 missing: botox, lip-filler, coolsculpting, laser-hair-removal, microneedling
- **Miami Lakes Med Spa** (miami-lakes) — 5 missing: botox, lip-filler, laser-hair-removal, microneedling, iv-therapy
- **L'Atelier Aesthetics** (miami-lakes) — 5 missing: botox, lip-filler, laser-hair-removal, microneedling, iv-therapy
- **Facial Mania Med Spa (Kendall)** (kendall) — 5 missing: botox, lip-filler, coolsculpting, laser-hair-removal, microneedling
- **GreeneMD** (weston) — 5 missing: botox, lip-filler, coolsculpting, laser-hair-removal, microneedling
- **4Ever Young Plantation** (plantation) — 5 missing: botox, lip-filler, microneedling, iv-therapy, morpheus8
- **BeWell MedSpa** (oakland-park) — 5 missing: botox, lip-filler, coolsculpting, laser-hair-removal, microneedling

## Constraints
- Ratings must come from a permitted API. No scraped Google/Yelp review text.
- A clinic needs name, address, phone, rating and treatments to qualify.
- A missing price renders as "request a quote" — never a guess.
- Open integrity flag: 31% of providers rated >=4.95. Do not add more implausibly-perfect ratings.
