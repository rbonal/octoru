# Octoru — Integrations

Two integration types. Use the right one per job:
- **MCP connector** — agent uses it live during a run (research, opening PRs). Configure in Claude Code's MCP settings.
- **API call w/ env creds** — best for scheduled batch reads (the evaluator). Creds in env, never in the repo.

| Job | Service | How | Auto-approved? |
|---|---|---|---|
| Research / listings | Your **prospector pipeline** (already have it) | feeds `build.py` | n/a |
| Live web research | **Exa** (web + code-docs search) | MCP connector | Yes |
| Clinic enrichment | **Google Places API** | API call | Yes (read) |
| Page design | none — pages are **code templates** (`templates/`) | — | n/a |
| Provider ranking | **scipy** (Python lib) | `pip install scipy` | exact Beta-posterior quantile (`scipy.stats.beta.ppf`) for the canonical `rank_providers()`; do NOT substitute a normal approximation |
| Build / version control | **GitHub** | MCP or git CLI | commit-to-branch only |
| Hosting / deploy | **Vercel / Netlify / Cloudflare Pages** | CLI/API | **GATED** |
| Ranking truth | **Google Search Console** | API (service account) | Yes (read) |
| Traffic / behavior | **GA4** (or Contentsquare) — optional | API | Yes (read) |
| Leads + conversion | **Bonalta CRM** | API | Yes (read) |
| Advertisers + revenue | **Bonalta Payments** | API | Yes (read) |
| Alerts + lead routing | **Bonalta Connect** | API | send is **GATED** |

**Must-haves to launch:** GitHub + a host + Search Console, plus your CRM / Payments / Connect by API.
**Optional:** Exa (research), GA4/Contentsquare (deeper signal).
**Don't bother:** a design connector — Canva is the wrong tool for programmatic pages (keep it for marketing/social assets).

**Rules:** read-only scopes where possible; the agent's auto-approved scope never includes reading secrets or sending anything external; research + build connectors are safe to auto-use; anything that ships or sends stays gated.
