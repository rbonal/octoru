#!/usr/bin/env python3
"""
GlowMap evaluator routine. Runs on its own schedule (e.g. weekly), SEPARATE from the builder.
Reads ground truth the builder can't fake, scores it, and sets build_state.

It can set: active | throttled | paused | halted   (all reversible — stopping = stop spending tokens).
It does NOT: deindex, contact advertisers, or wind the project down. Those stay with a human.

Working skeleton — fill the TODO API calls with your real GSC / CRM / billing creds.
Secrets must come from the environment, never be written to disk (hard-gated).
"""
import json, datetime, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config" / "thresholds.json").read_text())
STATE_PATH = ROOT / "state" / "build_state.json"


def fetch_metrics():
    """Pull externally-validated signals. Builder cannot influence these."""
    # TODO: Google Search Console API -> indexed pages, impressions, clicks, manual_action
    # TODO: Bonalta CRM -> qualified_leads, lead_to_consult_rate
    # TODO: Bonalta Payments/billing -> advertiser_count, placement_revenue
    # TODO: run ledger -> tokens_used_this_month
    return {
        "indexed_pages": 0,
        "impressions": 0,
        "qualified_leads_month": 0,
        "manual_action": False,
        "compliance_ok": True,
        "tokens_used": 0,
        "months_since_launch": 0,
    }


def decide(m) -> tuple[str, str]:
    """Return (state, reason). Compliance halts win over everything."""
    if m["manual_action"] or not m["compliance_ok"]:
        return "halted", "compliance tripwire — manual action or failed compliance check"

    th = CONFIG["state_thresholds"]
    mo = m["months_since_launch"]

    if mo >= 3 and m["indexed_pages"] < th["month_3"]["min_indexed_pages"]:
        return "halted_technical", "nothing indexed by month 3 — technical fault, needs human fix"
    if mo >= 9 and m["qualified_leads_month"] < th["month_9"]["min_qualified_leads_per_month"]:
        return "paused", "month-9 gate missed — leads don't justify token spend (reversible; resume anytime)"
    if mo >= 6 and m["qualified_leads_month"] < th["month_6"]["min_leads"]:
        return "throttled", "month-6 lagging — reduce token burn, focus quality"

    return "active", "on trajectory — spend is producing value"


def alert(state, reason):
    # TODO: send via Bonalta Connect per config["alerts"]
    print(f"[evaluator] ALERT [{state}] {reason}")


def main():
    m = fetch_metrics()
    state, reason = decide(m)
    STATE_PATH.write_text(json.dumps({
        "state": state,
        "reason": reason,
        "set_by": "evaluator",
        "metrics": m,
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }, indent=2))
    if state in CONFIG["alerts"]["notify_on"] or state.startswith("halted"):
        alert(state, reason)
    print(f"[evaluator] set build_state={state} :: {reason}")


if __name__ == "__main__":
    main()
