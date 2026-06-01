#!/usr/bin/env python3
"""
GlowMap builder routine.
Runs under Claude Code auto mode. Obeys build_state + token budget.
Renders pages from data + template; builds to a branch; NEVER deploys.
(Publish is hard-gated — see CLAUDE.md.)

Runnable skeleton. The only TODO is your real data source.
  pip install -r requirements.txt
  python builder/build.py
"""
import json, sys, datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config" / "thresholds.json").read_text())
STATE_PATH = ROOT / "state" / "build_state.json"
LEDGER_PATH = ROOT / "state" / "run_ledger.json"
GENERATED = ROOT / "generated"

env = Environment(
    loader=FileSystemLoader(str(ROOT / "templates")),
    autoescape=select_autoescape(["html", "j2"]),
)


def load_state():
    try:                                            # fail safe: any problem => paused
        return json.loads(STATE_PATH.read_text()).get("state", "paused")
    except Exception:
        return "paused"


def month_tokens_used():
    try:
        ledger = json.loads(LEDGER_PATH.read_text())
        return ledger.get(datetime.date.today().strftime("%Y-%m"), {}).get("tokens", 0)
    except Exception:
        return 0


def stop(reason):
    print(f"[builder] STOP: {reason}")
    sys.exit(0)


def quality_gate(page) -> bool:
    """ALL must hold or the page is skipped. Never lower the gate to hit a count."""
    flags = page.get("page_flags", {})
    if not (flags.get("has_consent_form") and flags.get("has_schema_markup")):
        return False
    for c in page.get("clinics", []):
        if not c.get("has_real_clinic_data"):
            return False
        if c.get("uses_scraped_review_text"):
            return False
        if c.get("has_before_after") and not c.get("before_after_consent"):
            return False
    return True


def fetch_pages():
    """TODO: pull from your prospector pipeline for config['seed_scope'].
    Returns a list of page dicts shaped like data/sample_clinic.json.
    The sample is loaded here only so the skeleton runs end-to-end."""
    return [json.loads((ROOT / "data" / "sample_clinic.json").read_text())]


def render(page):
    page.setdefault("last_updated", datetime.date.today().isoformat())
    html = env.get_template("treatment-page.html.j2").render(**page)
    slug = f"{page['treatment']['slug']}-{page['neighborhood']['slug']}"
    out = GENERATED / f"{slug}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def main():
    state = load_state()
    if state in ("paused", "halted", "halted_technical"):
        stop(f"build_state is '{state}' — not building.")
    if month_tokens_used() >= CONFIG["monthly_token_cap"]:
        stop(f"monthly token cap reached ({CONFIG['monthly_token_cap']}).")

    throttle = (state == "throttled")
    built, skipped = 0, 0
    for page in fetch_pages():
        if throttle and built >= 10:
            break
        if quality_gate(page):
            out = render(page)
            built += 1
            print(f"[builder] built {out.name}")
        else:
            skipped += 1
            print(f"[builder] skipped (failed quality gate): "
                  f"{page.get('treatment', {}).get('slug')}-{page.get('neighborhood', {}).get('slug')}")

    # TODO (auto-approved): git add + commit to branch 'auto/build'
    # DO NOT merge to main. DO NOT deploy. (hard-gated in CLAUDE.md)
    print(f"[builder] done. built={built} skipped={skipped} state={state}")


if __name__ == "__main__":
    main()
