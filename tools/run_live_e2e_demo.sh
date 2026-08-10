#!/bin/sh
# Live end-to-end run of the core pipeline via the Companion CLI.
# Drives Coordinator -> Sentinel -> Histor-lite -> Aletheia -> Bridge -> ODIN
# -> importers -> Case Bundle v0.2, with Atlas validation.
# Stdlib only; no network. Expected result: COMPANION_COMPLETED + verify_ok: true
#
# Usage:  sh tools/run_live_e2e_demo.sh
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
S="$ROOT/src"

WORK=$(mktemp -d)
OUT=$(mktemp -d)
EV="$WORK/evidence.txt"
echo "Sample evidence for a live Project Witness end-to-end run." > "$EV"

echo "Running Companion create-evidence-case (live chain)..."
python3 "$S/12_companion_cli_v031/companion.py" create-evidence-case \
  --case-id case_demo_001 \
  --evidence-id evidence_demo_001 \
  --evidence-file "$EV" \
  --allowed-root "$WORK" \
  --case-directory-name case_demo_001 \
  --coordinator-root     "$S/11_coordinator_workflow_v032" \
  --atlas-registry-root  "$S/09_atlas_registry" \
  --sentinel-root        "$S/01_sentinel_core" \
  --histor-lite-root     "$S/02_histor_lite" \
  --aletheia-root        "$S/03_aletheia_evidence_bundle" \
  --bridge-root          "$S/04_aletheia_odin_bridge" \
  --odin-root            "$S/05_odin_claim_reasoner" \
  --histor-aletheia-root "$S/06_histor_aletheia_importer" \
  --histor-odin-root     "$S/07_histor_odin_importer" \
  --case-bundle-v02-root "$S/08_case_bundle_v02" \
  --out "$OUT"

echo ""
echo "Verifying the produced output..."
python3 "$S/12_companion_cli_v031/companion.py" verify --run "$OUT"

echo ""
echo "Output tree written to: $OUT"
# strip bytecode the run created (project convention)
find "$ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$ROOT" -type f -name '*.pyc' -delete 2>/dev/null || true
