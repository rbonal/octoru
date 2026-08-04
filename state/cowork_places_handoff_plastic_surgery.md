# Cowork handoff — add Google Places ratings to 47 plastic-surgery clinics

Repo: `/Users/Bonal/Downloads/GlowMiamiDirectoryGoal/glowmap`

## What this unblocks
Claude Code researched and staged **47 real, source-verified plastic-surgery practices** across 22 South Florida cities (Miami-Dade 19, Broward 12, Palm Beach 16). They have everything EXCEPT ratings. Once you add Google Places ratings and write the file, the builder can produce the plastic-surgery vertical (Claude Code finishes the surgeon file + builder code separately).

## Input
**`state/plastic_surgery_staged_clinics.json`** — a JSON array of 47 staged clinic records. Each already has: `slug, name, category ("plastic-surgery"), neighborhood, neighborhood_name, county, state, address, phone, website, treatments`, the gate flags, `last_verified`, `sources`, and a helper flag `"_needs_rating": true`.

## For each staged clinic
1. `places_search_text` with the clinic's **name + address** to find the matching place.
2. `places_details` to read: `rating`, `userRatingCount`, `googleMapsUri`, `formattedAddress`, `internationalPhoneNumber`.
3. Add these fields to the record:
```json
{
  "rating": <numeric>,
  "review_count": <userRatingCount>,
  "rating_source": "google_places",
  "google_listing_url": <googleMapsUri>
}
```
4. Delete the `"_needs_rating"` helper flag.
5. Keep `slug, name, category, neighborhood, neighborhood_name, county, state, treatments, sources, last_verified` and the gate flags EXACTLY as staged. You may fill `address`/`phone` from Places `formattedAddress`/`internationalPhoneNumber` only if a staged value is empty — do NOT overwrite a non-empty staged value.

## Rules (compliance — non-negotiable)
- **Numeric `rating` + `review_count` ONLY.** Never copy review text (the build's quality gate forbids it).
- `category` must stay exactly `"plastic-surgery"` on every record.
- If a clinic can't be matched in Places, or returns no rating, **omit it** and report which (do not invent a rating).
- Report ratings as Google returns them — do not adjust or "smooth" them. (Note: a rating-integrity guard will flag implausibly-perfect distributions, same as the med-spa set; that's expected and handled downstream.)

## One thing to verify
Two staged clinics share an address — **Farber Plastic Surgery** and **5th Avenue Plastic Surgery**, both at *526 SE 5th Avenue, Delray Beach, FL 33483*. They may be the same suite/related practices or two distinct listings. Match each in Places; if Places returns one listing, keep the one that matches and drop the other (report it). If two distinct listings exist, keep both.

## Output
Write the rated array to **`data/prospector/plastic_surgery_clinics.json`** (a NEW file — the builder globs `data/prospector/*.json`, so it will be picked up automatically alongside the med-spa `clinics.json`). Write only the clinics you successfully rated.

Report: how many written, and which (if any) were dropped and why.

## Do NOT
- Do **not** touch `data/surgeons.json` — Claude Code owns that file.
- Do **not** edit `config/thresholds.json` or `CLAUDE.md`.
- Do **not** push. Commit to `auto/build` only (`git commit`); a push auto-deploys the live site and is the operator's call.

## After this lands
Tell Claude Code: *"ratings done at data/prospector/plastic_surgery_clinics.json — finish the surgeons file and the builder code, then build and commit."* Claude Code will add the surgery treatment content + surgeon rendering + nearest-provider fallback, run the build, quality-gate, and commit the rebuilt pages to `auto/build`.
