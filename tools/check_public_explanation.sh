#!/bin/sh
# Move 56/60 - public explanation check.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
missing=0
ok() { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; missing=$((missing + 1)); }
contains() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then ok "$label"; else bad "$label"; fi; }
forbid() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then bad "$label"; else ok "$label"; fi; }

current_marker="Roadmap complete through Move 60; Moves 61-70 remain future work"
echo "Public explanation check"
echo "------------------------"
PUB="$ROOT/PUBLIC_EXPLANATION.md"; [ -f "$PUB" ] && ok "PUBLIC_EXPLANATION.md" || bad "PUBLIC_EXPLANATION.md"
if [ -f "$PUB" ]; then
contains "$PUB" "Local v1 Release" "states Local v1 Release"
contains "$PUB" "$current_marker" "has current marker"
contains "$PUB" "does not prove external truth" "states no external truth"
contains "$PUB" "not production-ready" "states not production-ready"
contains "$PUB" "NO_EXTERNAL_FEEDBACK_RECORDED" "does not claim external approval"
fi
echo "------------------------"
if [ "$missing" -eq 0 ]; then echo "PUBLIC_EXPLANATION_CHECK: PASS"; exit 0; fi
echo "PUBLIC_EXPLANATION_CHECK: FAIL ($missing required item(s) missing or inconsistent)"; exit 1
