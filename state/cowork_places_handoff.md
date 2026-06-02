# Cowork handoff — rate the FULL staged set → data/prospector/clinics.json

Repo: `/Users/Bonal/Downloads/GlowMiamiDirectoryGoal/glowmap`

The builder cannot call Places in its own session, so YOU (Cowork) produce the rated file.

## Input
Read `data/seed_candidates_DRAFT.json` → `candidates` (currently ~76 real clinics across
Miami-Dade, Broward, and Palm Beach; each has name, address, neighborhood=city slug, and most
have `county` + `state`). These are verified clinic identities; they need permitted-API ratings.

## For each candidate
1. `places_search_text` with name + address → match the place.
2. `places_details` → `rating`, `userRatingCount`, `googleMapsUri`, `formattedAddress`.
3. Emit a record carrying ALL existing fields PLUS:
   - `rating` (numeric), `review_count` = userRatingCount, `rating_source` = "google_places",
     `google_listing_url` = googleMapsUri, and `has_real_clinic_data` true,
     `uses_scraped_review_text` false, `has_before_after` false, `before_after_consent` false.
   - Keep `neighborhood` (city slug), `county`, `state` EXACTLY as staged — they drive the
     /{state}/{county}/{city}/{treatment}/ URLs.
   - If `address` or `phone` is null in the draft, fill from Places `formattedAddress` /
     `internationalPhoneNumber` where available.

## Rules
- Numeric `rating` + `review_count` ONLY. **No review text** (compliance gate forbids scraped text).
- If a clinic can't be matched or has no rating, omit it and report which.
- Match `data/prospector/SCHEMA.md`.

## Output
Write the full array to `data/prospector/clinics.json` (pretty JSON). Report count written + dropped.
Then the builder runs standalone: build → quality-gate every page → commit live pages to auto/build.
