# Octoru — Deploy Pipeline

Purpose: make shipping content fast **and** safe, so weekly ranking work stops
sitting in un-merged PRs.

## How a change reaches the live site

```
weekly agent          GitHub                              Cloudflare
------------          ------                              ----------
opens PR  ─────────▶  build-verify CI  ──▶  (merge to  ──▶  runs builder/build.py
into auto/build       (build + checks)      auto/build)     serves generated/  ──▶  LIVE
```

- **Cloudflare already auto-deploys.** `wrangler.toml` sets
  `command = "python3 builder/build.py"` and serves `generated/`. Every push to
  `auto/build` rebuilds and deploys — **a merge to `auto/build` IS the deploy.**
  There is no separate deploy button.
- So the only manual step was the **merge click**, and merging was slow because it
  was risky: a bad merge once (cb2a815) silently deleted five treatment definitions
  and every canonical tag, with no automated check to catch it.

## The fix: `scripts/verify_build.sh`

One script builds the site and asserts the operator's documented post-merge checks.
Exit 0 = safe to deploy; non-zero = do not merge. It checks:

- build finishes `skipped=0` and `link check: all internal links valid`
- no broken / wrong-county links, no builder `STOP`, no un-overridden ratings HALT
- **regression guard:** 25 treatment definitions in `build.py` and the canonical tag
  in `treatment-page.html.j2` are intact (exactly the two cb2a815 casualties)
- `build_state` is not `halted`

Run it locally anytime: `bash scripts/verify_build.sh`. The weekly agent runs it
before opening a PR, and CI runs it on the PR — same script, one source of truth.

## One-time install (≈2 minutes)

The two workflow files live in **`ci/workflows/`** instead of `.github/workflows/`
because the agent's GitHub token lacks the `workflows` permission and cannot write
there. Install them once:

1. **Move the workflows into place:**
   ```
   mkdir -p .github/workflows
   git mv ci/workflows/build-verify.yml .github/workflows/build-verify.yml
   git mv ci/workflows/auto-merge.yml   .github/workflows/auto-merge.yml
   git commit -m "ci: install deploy-verification workflows" && git push
   ```
   (Do this from your desktop / any checkout with normal push rights.)

2. **Require the check.** GitHub → **Settings → Branches → Branch protection** for
   `auto/build` → **Require status checks to pass** → select **`build-verify`**.
   Now nothing merges unless the build is green.

3. **Allow auto-merge.** GitHub → **Settings → General** → tick **Allow auto-merge**.

Steps 1–3 give you confident **one-click merges**: open PR → CI goes green → merge →
Cloudflare deploys.

## Optional: fully hands-off

4. **Arm auto-merge.** GitHub → **Settings → Secrets and variables → Actions →
   Variables** → add `ENABLE_AUTO_MERGE = true`. Then any PR the agent labels
   **`auto-deploy`** is set to native auto-merge and ships itself the moment
   `build-verify` passes. Delete the variable to disarm instantly.

Auto-merge only ever fires **after** the required check passes, so the safety gate
governs every deploy. This is the "separate, explicitly-permissioned deploy step"
CLAUDE.md allows — the builder still never merges on its own judgment.

## Confirm Cloudflare (once)

In the Cloudflare dashboard, confirm the Workers/Pages project is connected to
`auto/build` with automatic production deploys on push. The live site already
reflects merged work, so this is almost certainly on — just verify.

## Indexing

The sitemap stamps a fresh `<lastmod>` on every URL each build, and auto-deploy
refreshes it, so Google re-crawls changed pages without manual pushes. Manual
"Request indexing" in Search Console for a few priority URLs stays a nice-to-have
and belongs to the Tuesday desktop weekly-seo-monitor (it needs a logged-in browser,
which a scheduled cloud run doesn't have).
