#!/bin/sh
# Adopted historical artifacts are FROZEN. Rewriting an adopted record to
# satisfy a current checker is falsification of history (Move 79 did exactly
# that to CHANGELOG_MOVE_78.md). This makes that class impossible.
# All hashing lives in a context-managed, testable Python helper.
set -u
export PYTHONDONTWRITEBYTECODE=1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2
python3 -B -W error::ResourceWarning - <<'PYEOF'
import sys
sys.path.insert(0, "verify/agreement_harness_v01")
from pin_check import verify_pins, load_pins

pins_path = "tools/adopted_artifact_pins.json"
problems = verify_pins(pins_path)
if problems:
    for rel, why in problems:
        print("  FAIL  adopted artifact %s: %s" % (rel, why))
    print("ADOPTED_IMMUTABLE_CHECK: FAIL")
    print("  Restore the adopted bytes. Never rewrite history to pass a check.")
    sys.exit(1)
print("  OK    %d adopted artifacts byte-identical" % len(load_pins(pins_path)))
print("ADOPTED_IMMUTABLE_CHECK: PASS")
PYEOF
