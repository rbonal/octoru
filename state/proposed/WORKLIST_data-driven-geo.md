# WORKLIST -- Data-driven geo (make new markets fully automatic)

**Goal:** after this one-time install, a brand-new market ships as **data only** -- a
`data/prospector/<city>.json` + a `data/places.json` entry, both of which the automated
weekly agent CAN push through the GitHub connector. No `build.py` edit, no hard-gated
`config/` edit. It then rides the existing `seo/* -> build-verify -> auto-merge ->
Cloudflare deploy` pipeline with zero clicks.

## Why one local step is unavoidable
`builder/build.py` is 164 KB -- too large to push through the GitHub connector, and the
automated session's token lacks the `workflows`/large-blob path. So this single structural
change to `build.py` must be installed once from a machine with normal push rights. After
that, expansions never touch `build.py` again.

## What the change does (34 lines, additive)
1. Extends `CITY_COUNTY` / `COUNTY_NAMES` / `NEIGHBORHOOD_NAMES` from `data/places.json`.
2. Reads an optional per-place `context` blurb from `data/places.json`.
3. Widens the build scope to any neighborhood that has prospector clinics -- so a new
   market is in-scope the moment its data lands, without editing `config/seed_scope`.

Verified on `auto/build` @3586ba6: patch applies clean; `built=508 skipped=0`; verify green;
**existing pages byte-identical** except site-wide counts + sitemap. Independent of the
rule-#42 widening (PR #43) -- no shared lines, applies in any order.

## One-time install (run once from any checkout with push rights)
```
git fetch origin
git checkout auto/build && git merge --ff-only origin/auto/build

# bring the staged patches + places.json entry
git merge --no-ff origin/refactor/data-driven-geo
# bring the Sarasota data file
git merge --no-ff origin/seo/sarasota-launch

# apply the two patches (build.py can't be pushed from the cloud agent)
git apply state/proposed/data-driven-geo.patch
git apply state/proposed/places-json-sarasota.patch

python3 builder/build.py            # expect: built=508 skipped=0 state=active
bash scripts/verify_build.sh         # expect: all build-verification checks passed

git add -f generated/fl/sarasota
git add builder/build.py data/places.json generated
git commit -m "refactor: data-driven geo (new markets = data only) + Sarasota launch"
git push origin auto/build           # deploys via Cloudflare
```

## After this install
- **Future markets = data only.** The weekly agent opens a `seo/<market>-launch` PR that
  adds `data/prospector/<city>.json` + a `data/places.json` entry. `build-verify` runs; if
  green, `auto-merge` merges it; Cloudflare deploys. You do nothing.
- **Sarasota ships now** with 4 pages (botox, lip-filler, chemical-peel, laser-hair-removal).
  The other two (hydrafacial, microneedling) depend on the rule-#42 provider-eligibility
  widening in **PR #43**; the moment that merges, they build automatically from the same
  Sarasota data -- no new work.
- **OBSOLETE after this:** the earlier `state/proposed/build-py-sarasota.patch` and
  `state/proposed/activate-sarasota.patch` from PR #45. Sarasota's geo now comes from
  `places.json` and its scope from the prospector file, so neither the per-market build.py
  edit nor the hard-gated config edit is needed anymore. Ignore/close those two patches.

## Governance note (read once)
This moves "which geographies are live" from the hard-gated `config/seed_scope.neighborhoods`
to data the agent can push (`places.json` + prospector files). The safety gate is unchanged:
nothing deploys unless `build-verify` is green, and every change still arrives as a PR you
can review or close. The hard-gated `config/` still governs token budget, completeness
thresholds, and categories. If you'd rather keep an explicit human gate on brand-new
geographies, don't install part 3 (the scope widening) -- keep adding the city to
`config/seed_scope.neighborhoods` yourself and the rest still works.
</content>