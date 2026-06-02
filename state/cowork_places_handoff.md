# Cowork handoff — rate 5 specific clinics → merge into data/prospector/clinics.json

Repo: `/Users/Bonal/Downloads/GlowMiamiDirectoryGoal/glowmap`

## What this unblocks
5 staged clinics need Google Places ratings before they can ship. Once rated and merged:
- **North Palm Beach** unlocks 4 held treatment pages (botox, lip-filler, LHR, microneedling)
- **Royal Palm Beach** unlocks its last held page (laser-hair-removal)

## The 5 clinics to rate

| Name | Neighborhood slug | Address | Phone |
|---|---|---|---|
| North Palm Beach Aesthetics | north-palm-beach | 700 US Hwy 1, Suite D, North Palm Beach, FL 33408 | +1 561-231-0193 |
| Body Details (North Palm Beach) | north-palm-beach | 4290 Professional Center Dr, Suite 301, North Palm Beach, FL 33410 | +1 561-320-7868 |
| Cosmetic Skin & Laser Center (NPB) | north-palm-beach | 11924 US Hwy 1, Suite 101, North Palm Beach, FL 33408 | +1 561-624-7300 |
| Flawless Med Spa (Royal Palm Beach) | royal-palm-beach | 1112 Royal Palm Beach Blvd, Royal Palm Beach, FL 33411 | +1 561-440-1112 |
| Palm Beach Laser & Aesthetic (RPB) | royal-palm-beach | 10397 Southern Blvd, Royal Palm Beach, FL 33411 | +1 754-253-2320 |

## For each clinic

1. `places_search_text` with the clinic's name + address to find the matching place.
2. `places_details` to read: `rating`, `userRatingCount`, `googleMapsUri`, `formattedAddress`, `internationalPhoneNumber`.

## Build a record with ALL fields from the existing staging record PLUS

```json
{
  "rating": <numeric>,
  "review_count": <userRatingCount>,
  "rating_source": "google_places",
  "google_listing_url": <googleMapsUri>,
  "has_real_clinic_data": true,
  "uses_scraped_review_text": false,
  "has_before_after": false,
  "before_after_consent": false
}
```

Keep `neighborhood`, `county` (`palm-beach`), `state` (`fl`), `address`, `phone` EXACTLY as in the table above. If Places returns a better `formattedAddress` or `internationalPhoneNumber`, you may fill null fields but do NOT override existing non-null values.

## Rules
- **Numeric `rating` + `review_count` ONLY** — no review text (compliance gate forbids it).
- If a clinic can't be matched or has no rating, omit it and report which.

## Output
**Append** the 5 rated records to `data/prospector/clinics.json` (it currently has 141 records).
Do NOT replace or truncate existing records. Write the full updated array (141 + up to 5 = up to 146).

Report how many were written and which (if any) were dropped.

After this, the builder runs standalone:
```
python3 builder/build.py
```
and commits the rebuilt pages to auto/build.
