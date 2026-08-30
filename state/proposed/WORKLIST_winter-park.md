# Winter Park (Orange County) — operator activation worklist

Stage 1 expansion pilot. The build-engine + data changes are done on this branch;
one **hard-gated config edit** remains, which only the operator applies (CLAUDE.md:
"Edit CLAUDE.md, anything in config/ … There is no override"; the prospecting handoff
tags it the same way).

## Required to ship Winter Park (operator, on the PR branch)

Why patches instead of committed changes: this session could not push `builder/build.py`
(the connector rejects a 167 KB file inline, and local git here can neither commit — the
mount `.git` denies `unlink` — nor authenticate a push). So the file changes ship as staged
patches under `state/proposed/`, and only the new data file (`data/prospector/winter-park.json`)
is committed directly. All four patches were verified this session to apply cleanly onto
`auto/build` (3586ba6) **together** and to produce a green `verify_build.sh`
(built=505, skipped=0, links valid, defs=25, canonical=1, state active).

- `build-py-winter-park.patch` — build.py: widened provider-eligibility filter + Orange
  County/Winter Park geo + local context (85 lines, additive).
- `places-json-winter-park.patch` — data/places.json: Winter Park municipality (Orange).
- `striking-log-winter-park.patch` — seo/striking_distance_log.md: this run's entry.
- `activate-winter-park.patch` — **HARD-GATED** config: adds `winter-park` to
  `seed_scope.neighborhoods` (CLAUDE.md: "anything in config/ … There is no override";
  the prospecting handoff tags it the same). Operator only.

```
git checkout seo/winter-park-launch
git apply state/proposed/build-py-winter-park.patch \
          state/proposed/places-json-winter-park.patch \
          state/proposed/striking-log-winter-park.patch \
          state/proposed/activate-winter-park.patch
python3 builder/build.py && bash scripts/verify_build.sh   # expect built=505 skipped=0, green
git add -A && git commit -m "winter-park: apply build-engine + geo + config activation"
git push
# then add the 'auto-deploy' label to the PR -> merges on green -> Cloudflare deploys
```

Until these are applied, `winter-park` is not an active market and the builder emits **zero**
Winter Park pages — the committed data file and the staged patches are all inert without the
apply step above. Do NOT add the `auto-deploy` label before the patches are on the branch, or
the PR auto-merges an inert (no-Winter-Park) build.

## What builds once activated (verified 2026-08-29)

3 verified providers, all confirmed on their own website menus, ratings from the
permitted Google Places API, no published prices (→ request-a-quote), nothing fabricated:

| Provider | Category | Verified treatments |
|---|---|---|
| Reflections Dermatology – Winter Park (4.9, 944) | dermatology | botox, dermal-fillers, coolsculpting, laser-hair-removal |
| Oasis Dermatology (4.7, 587) | dermatology | botox, chemical-peel, microneedling |
| Dr. Kapil Saigal, MD FACS (4.9, 331) | plastic-surgery | botox, dermal-fillers |

Pages that clear the ≥2-verified gate:
- **/fl/orange/winter-park/** — city hub
- **/fl/orange/winter-park/botox/** — 3 providers ✅ (all derm/plastic — this is the widened-filter win)

Held at 1 verified (correct — never padded):
- chemical-peel (Oasis only; Reflections' /treatment/chemical-peels/ page 404s → excluded)
- coolsculpting (Reflections only)
- laser-hair-removal (Reflections only)
- microneedling (Oasis only)

## Optional, separate decision — dermal-fillers

**dermal-fillers/winter-park has 2 verified providers ready** (Reflections + Saigal), but
`dermal-fillers` is not an active med-spa treatment slug in config (the active filler slug
is `lip-filler`). Activating `dermal-fillers` in `seed_scope.categories["med-spa"].treatments`
would turn it on **site-wide**, not just Winter Park — every existing city would begin
attempting dermal-fillers pages. That has a broad blast radius and its own
prospecting/verification need, so it is intentionally NOT bundled into the winter-park
patch. Recommend deciding it on its own pass.

## Omitted providers (integrity)

Spavia Winter Park, The Spa at The Alfond Inn, Massage Envy – Winter Park were API-tagged
chemical-peel but are esthetician/hotel/chain spas whose menus did not confirm a clinical
chemical peel; omitted rather than padding a MedicalClinic directory. Saigal's `morpheus8`
tag was dropped (not on his menu). Reflections' `chemical-peel` tag dropped (page 404).
