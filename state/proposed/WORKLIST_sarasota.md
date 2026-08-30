# WORKLIST — Sarasota, FL launch (Stage-1 New Ground)

Prepared by the autonomous Expansion Engine on 2026-08-30. **Nothing here is deployed.**
This branch (`seo/sarasota-launch`) carries the new data file. Every change to an EXISTING
file is a `git apply`-able patch below. `config/thresholds.json` is HARD-GATED (operator only).

## What ships in this run
- **New data** (already on this branch): `data/prospector/sarasota.json` — 10 menu-verified
  in-city Sarasota clinics (ratings via google_places_api).
- **Patches** (under `state/proposed/`, apply in order):
  1. `build-py-sarasota.patch` — adds the rule-#42 provider-eligibility widening
     (`_eligible_for_category`) **and** Sarasota geo (CITY_COUNTY / COUNTY_NAMES /
     NEIGHBORHOOD_CONTEXT). build.py is too large to push inline via the connector.
  2. `places-json-sarasota.patch` — adds the `sarasota` municipality (27.3364, -82.5307).
  3. `activate-sarasota.patch` — **HARD-GATED config.** Adds `"sarasota"` to
     `seed_scope.neighborhoods`. Operator applies by hand.
  4. `striking-log-sarasota.patch` — appends the 2026-08-30 log entry.

## Exact sequence (run from repo root on `auto/build`)
```
git fetch origin
git checkout auto/build && git merge --ff-only origin/auto/build

git apply state/proposed/build-py-sarasota.patch
git apply state/proposed/places-json-sarasota.patch
git apply state/proposed/activate-sarasota.patch      # hard-gated config — your call
git apply state/proposed/striking-log-sarasota.patch

# merge the data branch (or cherry-pick the single data file)
git merge --no-ff origin/seo/sarasota-launch     # brings data/prospector/sarasota.json

python3 builder/build.py                          # expect: built=510 skipped=0 state=active
bash scripts/verify_build.sh                       # expect: all build-verification checks passed

# generated/ is .gitignore'd but force-tracked. New Sarasota pages must be force-added:
git add -f generated/fl/sarasota
git add builder/build.py data/places.json config/thresholds.json seo/striking_distance_log.md generated
git commit -m "feat(sarasota): launch Sarasota, FL — 6 treatment pages, 10 verified providers"
git push origin auto/build                         # THIS may trigger the Cloudflare deploy
```

## Verify after applying (sanity greps)
- `grep -c "_eligible_for_category" builder/build.py` → **3**
- `grep -c '"sarasota"' builder/build.py` → **>=4**
- `grep -c 'rel="canonical"' templates/treatment-page.html.j2` → **1** (must not be 0)
- Build prints `built=510 skipped=0` and `link check: all internal links valid`.
- `find generated/fl/sarasota -name index.html | grep -v guide` → 6 treatment pages + 2 hubs.
- `coolsculpting × sarasota` is intentionally **HELD** (1 provider < min 2) — not a bug.

## IMPORTANT — interaction with Winter Park PR #43
PR #43 (Winter Park) also introduces the rule-#42 widening in build.py. If you merge #43
FIRST, `build-py-sarasota.patch` will conflict on the widening block. Then either:
- apply it with `git apply --3way state/proposed/build-py-sarasota.patch` and keep a SINGLE
  `_eligible_for_category` / `NONSURGICAL_SOURCE_CATEGORIES` definition, **or**
- drop the widening hunk from the patch and keep only the Sarasota geo hunks
  (NEIGHBORHOOD_CONTEXT / CITY_COUNTY / COUNTY_NAMES) — those apply cleanly regardless.
The Sarasota geo and the two `_eligible_for_category` call-site swaps are the only build.py
changes that are strictly Sarasota-specific.

## Hard gates (builder did NOT do these — operator only)
- Merge to `auto/build`, push, or trigger any deploy.
- Edit `config/` directly (staged as a patch instead).
- Add the `auto-deploy` label.
- Request Search Console indexing — only AFTER the URLs are live post-deploy.
