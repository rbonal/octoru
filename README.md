# Octoru — Auto-Mode Runbook

How to run this as an autonomous Claude Code goal with auto-approved code, **without**
auto mode becoming the thing that causes a mistake.

## Loading into Claude Code

1. Unzip and `git init` the folder (or drop it into a new repo). `CLAUDE.md` is the agent's operating law — Claude Code reads it automatically.
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and fill creds. **`.env` is gitignored — keep it that way.**
4. Sanity check it runs: `python builder/build.py` → writes a page into `generated/`. (Uses `data/sample_clinic.json` until you wire the real data source — the one `TODO` in `build.py`.)
5. Read `INTEGRATIONS.md`, connect the must-haves (GitHub + host + Search Console).
6. Launch builder + evaluator as routines with the **scoped permissions** below.

Files: `CLAUDE.md` (goal/law) · `config/thresholds.json` (human-owned) · `builder/` + `evaluator/` (routines) · `templates/` + `assets/` (the brand-faithful page) · `data/` (schema) · `state/` (flags + ledger).

> Note: this scaffold is handed to you to run on **your** Claude Code / infrastructure.
> The autonomous agent is your Claude Code instance, not the chat assistant that wrote this.

---

## The two routines

| Routine | What it does | Cadence | Auto-approve? |
|---|---|---|---|
| `builder/build.py` | Regenerates changed pages, commits to `auto/build` branch | Frequent (e.g. on data change / hourly) | Yes — build loop only |
| `evaluator/evaluate.py` | Reads GSC/CRM/billing, sets `build_state`, alerts | Weekly | Yes — it only writes state + alerts |

Keep them as **separate** routines so the thing that judges success can't be edited by the
thing being judged.

---

## Permission scoping (this is what makes auto mode safe)

Run auto-approve **scoped**, not blanket. In Claude Code, allow the reversible build loop and
deny the irreversible/sensitive actions so they require explicit human action:

**Allow (auto-approved):**
- edit/write within `builder/` and generated output
- `python builder/build.py`, tests, linters
- `git add`, `git commit` on branch `auto/build`

**Deny / require explicit approval (do NOT put on the allowlist):**
- `git push`, merge to `main`, any deploy/publish command
- any read of env secrets / credential files
- edits to `CLAUDE.md` or `config/**`
- any network send to advertisers / patients / external endpoints
- `rm`, permission/ACL changes

Do **not** launch with a blanket "skip all permissions" flag. The whole point is that publish,
secrets, and config stay outside the auto-approved set. `CLAUDE.md` restates these as law for
the agent; the permission scope enforces them at the tool level. Belt and suspenders.

---

## The token budget = your "stop spending" backstop

`config/thresholds.json → monthly_token_cap` is the hard floor. The builder refuses to run
once the month's ledger hits it, regardless of state. Set it to your real budget before
launching. This is what makes it safe to leave running unattended: even if everything else
misbehaves, spend cannot run away.

---

## The deploy boundary

The builder only ever commits to `auto/build`. Going live is a **separate, explicitly-
permissioned step** — a human merge, or a deploy job that runs *only* when `build_state` is
`active`/`throttled` AND the compliance check passed. Never wire deploy into the auto-approved
build loop. In a medical-marketing vertical, the live publish is the one action you don't let
an unattended agent take on its own.

---

## First-run checklist

1. Fill the `TODO`s: data source in `build.py`, the API calls in `evaluate.py`.
2. Put GSC / CRM / billing credentials in the **environment**, never in the repo.
3. Set `monthly_token_cap` to your real budget.
4. Confirm `config/seed_scope` is narrow (Phase 1). Don't widen it manually — the evaluator
   raises scope as cohorts prove out.
5. Launch builder + evaluator as routines with the scoped permissions above.
6. Watch `state/build_state.json`, `state/run_ledger.json`, and `state/needs_human.json`
   for the first few cycles before trusting it unattended.

---

## What the agent will surface to you (and you should expect)

- `state/needs_human.json` — anything ambiguous or hard-gated it refused to guess on.
- Alerts via Connect on `throttled` / `paused` / `halted` / budget-80% / needs-human.
- A pending merge on `auto/build` when a build is ready to go live — your call to ship.

Everything reversible runs itself. Everything you can't undo waits for you.
