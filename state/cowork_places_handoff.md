# Cowork handoff — produce data/prospector/clinics.json from Places (New)

Repo: `/Users/Bonal/Downloads/GlowMiamiDirectoryGoal/glowmap`

Use your working Places MCP (`places_search_text` + `places_details`, Places API New) to produce the rated data file the GlowMap builder needs. The builder cannot see the Places tools in its own session, so you run the API calls and write the file; the builder then runs standalone.

## Input
Read `data/seed_candidates_DRAFT.json` — 14 real clinics with `name`, `address`, `neighborhood` (slug), `phone`, `booking_url`, `treatments`.

## For each candidate
1. `places_search_text` with the clinic's `name` + `address` to find the matching place.
2. `places_details` on that place to read: `rating`, `userRatingCount`, `googleMapsUri`, `formattedAddress`.
3. Build a record with these fields:
   - `slug`, `name`, `neighborhood` (keep the slug from the draft **exactly** — do not reassign), `neighborhood_name`, `address` (draft's; if null, use Places `formattedAddress`), `phone`, `email`, `booking_url`, `treatments` (from draft), `languages`, `featured_tier`
   - `rating`: numeric Places rating
   - `review_count`: `userRatingCount`
   - `rating_source`: `"google_places"`
   - `google_listing_url`: Places `googleMapsUri`
   - `has_real_clinic_data`: `true`, `uses_scraped_review_text`: `false`, `has_before_after`: `false`, `before_after_consent`: `false`

## Critical rules
- Include ONLY the numeric `rating` and `review_count`. **Do NOT copy any review text** — the build's compliance gate forbids scraped review text.
- If a clinic can't be confidently matched or has no rating, **omit it** and report which were dropped.
- Match the field shape in `data/prospector/SCHEMA.md`.

## Output
Write the array of records to `data/prospector/clinics.json` (pretty-printed JSON). Then report how many clinics were written and which (if any) were dropped.
