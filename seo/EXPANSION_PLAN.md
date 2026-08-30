# Octoru — Expansion Master Plan (Standing Order)

**Read this at the start of every weekly build run.** It is the operating plan for
growing Octoru's ranked footprint. It sits above the weekly striking-distance log
(`seo/striking_distance_log.md`), which records what each run actually did.

Version 2 · 2026-08-30. Supersedes ad-hoc weekly page-picking.

---

## Prime directive

Point every hour of build at **traffic Octoru can realistically put on page one** —
because only page-one traffic becomes relevance, and eventually revenue. Win the
winnable first; size follows.

## Cadence — go as far as possible each run

The old "2–3 pages/week" pace is retired now that deploy is automated and gated.

- **Each run, go as far as you safely can.** The goal is to **conquer a whole
  municipality end-to-end in a single run** where possible — build/complete *all*
  its viable treatment pages, each with the FAQ + schema + internal links (+ Spanish
  where the vertical exists), not a few scattered pages.
- **Depth before breadth:** finish one municipality completely before starting the
  next. If run capacity remains, conquer the next municipality in priority order.
- **Parallelize** clinic research across municipalities to maximize verified pages
  per run.
- **The only limits are integrity and budget — never quality.** A page with fewer
  than 2 verified clinics is **held or rolled up to its parent, never padded**.
  Nothing is fabricated to raise a count. If a run would trip the quality gate or
  the token cap, stop and log — a smaller honest run beats a big thin one that gets
  the domain demoted.

## Operating principles

1. **Winnability over size.** A market qualifies only if its ranking difficulty is
   in Octoru's proven zone (**≈ ≤ 24**; the site already ranks at Miami 15,
   Coral Gables 11). A smaller market we can reach #1 in beats a huge one we'd sit
   at position 60 in.
2. **The municipality is the unit — not the metro.** Octoru wins at
   `/city/` and `/neighborhood/` level, never a single `/metro/` page. In every new
   metro, **find its "Coral Gables"** — the affluent, low-difficulty, clinic-dense
   enclave — and take that before the generic metro head term.
3. **Integrity is the gate.** ≥2 real verified clinics per page; ratings from
   permitted Google APIs only; real treatment menus; prices only where published.
   No scraped review text, no invented ratings/prices/credentials/before-afters.
4. **Earn the next stage.** No geography is pre-committed. Each stage opens only when
   the previous posts real page-one wins. Effort follows proof.

---

## Provider eligibility — widen the supply, keep the bar

For the **non-surgical** treatments (Botox, fillers/lip filler, laser hair removal,
microneedling, HydraFacial, chemical peel, morpheus8, IV therapy, CoolSculpting, etc.),
a listing may come from **any verified business that performs that treatment on its own
published menu** — **not only businesses categorized as "med spa."** Explicitly include:

- **Plastic surgery practices** and **dermatology practices** that offer injectables,
  laser, skin and body treatments. Board-certified injectors are high-authority,
  credible listings, and pulling them in **materially increases verified supply** — so
  more treatment×city pages clear the ≥2-clinic gate and more markets become buildable.

**The bar does not move:** the provider must genuinely list the treatment (verified on
its own website), ratings come from permitted Google APIs, nothing is fabricated, and
prices show only where published. Do not double-count a provider or mislabel its primary
category.

**Keep the verticals distinct:** this rule pulls surgery/derm clinics into the pages for
the **non-surgical** treatments they already offer. The **surgical** vertical itself
(rhinoplasty, tummy tuck, BBL, mommy makeover, facelift, liposuction, breast
augmentation) remains a separate, deferred track — see "Deferred verticals" below.

*Build note: the eligible-provider filter lives in `builder/build.py`; widening it to
admit surgery/derm sources for non-surgical treatments is a build-engine change, made in
a full-access session (not the connector-only cloud run).*

---

## Targeting map — municipality difficulty (DataForSEO, Aug 2026)

Difficulty = chance of reaching the top 10 (0–100). Green ≤17 high-confidence ·
Yellow 18–24 winnable · Orange 25–29 needs authority · Red ≥30 defer.

**Proven / template:** Coral Gables 11, Miami 15 (already ranking/climbing).

**Winnable enclaves to prioritize (rich + low difficulty + clinic-dense):**

| Municipality | Metro | Difficulty |
|---|---|---|
| Aventura | Miami | 0 |
| Boca Raton | Palm Beach | 8 |
| Katy | Houston | 8 |
| Paradise Valley | Phoenix/Scottsdale | 8 |
| Coral Gables | Miami | 11 |
| Buckhead | Atlanta | 12 |
| Winter Park | Orlando | 14 |
| Sugar Land | Houston | 19 |
| Southlake | Dallas–Fort Worth | 21 |

**The key unlock — enclaves flip "defer" metros into "go":** Atlanta metro is hard
(33) but **Buckhead is 12**. Scottsdale is the hardest on the board (34) but
**Paradise Valley, richer and adjacent, is 8**. Enter hard metros through their
winnable wealthy enclave.

**Rich but contested — wealth ≠ winnable, gate on difficulty:** Highland Park 28,
Frisco 26, The Woodlands 46, Plano 54. Defer these despite affluence.

**Metro head terms (reference anchors, not the primary targets):** Dallas 19,
Jacksonville 21, Orlando 22, Houston 23, Tampa 24 · San Antonio 29, Austin 28,
Phoenix 28 · Atlanta 33, Scottsdale 34, El Paso 37. Treatment+city terms
(botox/lip-filler + city) scored ~0 — page-level pages are the easiest of all.

---

## Staged roadmap (results-triggered)

### Stage 0 — Convert South Florida to page one · *now*
Push the already-ranking striking-distance pages (positions 11–40) onto page one —
lead with **botox Coral Gables (pos 24)**, the Coral Gables lip-filler and Fort
Lauderdale lip clusters. Treatment-page + title/meta enrichment; internal links;
request indexing each cycle.
**Trigger →** ≥8 commercial keywords on page 1 AND a clear upward clicks/impressions trend.

### Stage 1 — Finish winnable Florida · *next*
Conquer the untapped FL municipalities in opportunity order. Big metros via their
winnable cores: **Jacksonville, Orlando (→ Winter Park), Tampa (→ South Tampa)**;
then the easy SW-FL wins **Sarasota (11), Fort Myers (15), Naples (17)**, plus PB
enclaves like **Boca Raton (8)**. Full treatment set per municipality, ≥2 verified
clinics each.
**Trigger →** ≥3 of these markets with a hub or treatment page on page 1 + the
clinic-sourcing pass proven repeatable.

### Stage 2 — Texas, opportunity-first · *on Stage 1 trigger*
Enter Texas by winnable enclave, not by size. Lead with **Dallas (19) + Southlake (21)**,
**Houston via Katy (8) + Sugar Land (19)**, and **McAllen (11)** as the Spanish-vertical
flagship (CPC $12, heavily Hispanic — the Spanish pages are a moat there).
Hold **San Antonio (29)** and **Austin (28)** for Stage 2b; defer **El Paso (37)**,
**The Woodlands (46)**, **Plano (54)**.
**Trigger →** ≥2 TX metros reach page 1 → unlock San Antonio + Austin, then evaluate a 2nd state.

### Stage 3 — Opportunistic secondary markets · *data-triggered, quarterly*
Pick each new market from **then-current** difficulty data (re-run the scan), taking
the highest opportunity with clinic supply. Easiest doors today: **Tucson (11),
Buckhead/Atlanta (12), Charlotte (18), Las Vegas (21), Nashville (22)**.
Avoid early: Scottsdale (34), Atlanta metro (33), El Paso (37).
**Trigger →** each quarter, one new market enters only if a winnable slot
(difficulty ≤ 22) with clinic supply exists.

### Stage 4 — Full-state saturation · *the endgame, per state*
Once a state's winnable core is ranking, **complete it.** Full geographic coverage
is a ranking asset in itself: it makes Octoru the topical authority for that state,
which lifts the competitive head terms deferred earlier (metro terms, contested
enclaves). Saturation = every viable municipality built + Spanish across all +
county/state hub graph complete.
- **Bounded by clinic supply, completed by roll-up:** build every locality with ≥2
  verified clinics; roll thinner localities' clinics up to their parent city/county
  page (roll-up logic already exists). Complete coverage of the *viable* map — never
  empty/thin pages for empty towns.
- **Paced, not dumped:** the weekly engine widens the net progressively as authority
  compounds — never a one-shot page-dump (spam risk on a young domain).
**Payoff loop:** completing the state is *how* the hard markets (Tampa/Miami head
terms, Plano, Scottsdale) eventually become winnable.

**Sequence per state:** winnable enclaves → mid-tier municipalities → full saturation
→ lifts the whole state → repeat the arc in the next state.

---

## Integrity guardrails (non-negotiable, every page, every market)

- ≥2 verified clinics per page, or it is held / rolled up — never padded.
- Ratings from permitted Google APIs only; no scraped review text.
- No fabricated clinics, prices, ratings, credentials, or before/after claims.
- Every change passes the build-verify gate before it can reach the live site.
- Quality over volume, always. Faster = more *good* pages + authority, never a burst
  of thin ones.

## Accelerants (run continuously)

- Front-load striking-distance pages (positions 11–30) — fastest wins.
- Build domain authority / backlinks — the real rate-limiter on a young domain
  (~10 referring domains today). Citations, industry lists, owned-property links,
  light digital PR.
- Indexing velocity: request indexing for changed URLs each cycle; IndexNow ping.
- Topical completeness + internal links (hub → treatment → guide) to spread authority.

---

## Deferred — future verticals (do NOT build yet)

- **Surgical / plastic-surgery vertical:** rhinoplasty, tummy tuck, BBL, mommy
  makeover, facelift, liposuction, breast augmentation. Groundwork exists in the
  repo (plastic-surgery templates, `state/plastic_surgery_staged_clinics.json`,
  `builder/PLAN_plastic_surgery_vertical.md`). **Activate only after the med-spa
  vertical is winning** in its markets. Surgical leads are the highest-value of all —
  worth doing right, later, not diluting focus now.

---

*Human-facing proposal mirror: the "Octoru Expansion Plan" artifact. This file is the
machine-followed standing order; keep the two in sync when the plan changes.*
