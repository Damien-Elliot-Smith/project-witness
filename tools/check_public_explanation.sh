#!/bin/sh
# Move 56/60 - public explanation check.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
missing=0
ok() { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; missing=$((missing + 1)); }
contains() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then ok "$label"; else bad "$label"; fi; }
forbid() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then bad "$label"; else ok "$label"; fi; }

# Move 70.5: marker updated to the Roadmap One completion state.
# The authoritative current-state checker is tools/check_current_release_state.sh.
current_marker="Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack."
echo "Public explanation check"
echo "------------------------"
PUB="$ROOT/PUBLIC_EXPLANATION.md"; [ -f "$PUB" ] && ok "PUBLIC_EXPLANATION.md" || bad "PUBLIC_EXPLANATION.md"
if [ -f "$PUB" ]; then
contains "$PUB" "local review/demo stack" "states local review/demo stack boundary"
contains "$PUB" "$current_marker" "has current marker"
contains "$PUB" "does not prove external truth" "states no external truth"
contains "$PUB" "not production-ready" "states not production-ready"
contains "$PUB" "NO_EXTERNAL_FEEDBACK_RECORDED" "does not claim external approval"
fi
echo "------------------------"
if [ "$missing" -eq 0 ]; then echo "PUBLIC_EXPLANATION_CHECK: PASS"; exit 0; fi
echo "PUBLIC_EXPLANATION_CHECK: FAIL ($missing required item(s) missing or inconsistent)"; exit 1
