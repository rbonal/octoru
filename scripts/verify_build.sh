#!/usr/bin/env bash
# Octoru build-verification gate.
# Builds the site and asserts the operator's documented post-merge checks.
# Exit 0 = safe to deploy · non-zero = do NOT merge.
# Run it locally before opening a PR; CI (.github/workflows/build-verify.yml) runs it too.
set -uo pipefail
cd "$(dirname "$0")/.."

log="$(mktemp)"
python3 builder/build.py 2>&1 | tee "$log"

fail=0
note(){ echo "::error::$1"; echo "  FAIL: $1"; fail=1; }

# --- build output ---
grep -Eq 'built=[0-9]+ skipped=0' "$log" || note "build did not finish with skipped=0"
grep -q 'link check: all internal links valid' "$log" || note "internal link check did not pass"
grep -q 'WARN: .*broken internal link' "$log" && note "broken internal links present"
grep -q 'WARN: .*wrong-county link'    "$log" && note "wrong-county links present"
grep -q 'STOP:'          "$log" && note "builder STOPPED before completing (paused/halted/missing input)"
grep -q 'DO NOT PUBLISH' "$log" && note "un-overridden ratings integrity HALT"

# --- regression guard: the cb2a815-class casualties must stay intact ---
defs=$(grep -o 'iv-therapy\|morpheus8\|hydrafacial\|chemical-peel\|dermal-fillers' builder/build.py | wc -l | tr -d ' ')
[ "$defs" = "25" ] || note "treatment definitions in build.py = $defs (expected 25 — a merge may have dropped med-spa treatments)"
canon=$(grep -c 'rel="canonical"' templates/treatment-page.html.j2 || true)
[ "$canon" = "1" ] || note "canonical tag count in treatment-page.html.j2 = $canon (expected 1)"

# --- state file sanity (compliance) ---
state=$(python3 -c "import json;print(json.load(open('state/build_state.json')).get('state','paused'))")
echo "build_state = $state"
[ "$state" = "halted" ] && note "build_state is 'halted' — compliance stop"

rm -f "$log"
if [ "$fail" = "1" ]; then echo "build verification FAILED"; exit 1; fi
echo "all build-verification checks passed"
