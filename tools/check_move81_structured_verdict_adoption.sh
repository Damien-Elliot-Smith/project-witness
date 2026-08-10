#!/bin/sh
# MOVE 81 STRUCTURED-VERDICT ADOPTION GATE.
#
# Move 81 adds an additive structured-verdict output boundary (an adapter)
# around the adopted verification lanes. It changes no adopted verifier, no
# default output, and no verdict behaviour, and creates no Rust PASS path.
#
# Responsibility split (owner-ruled):
#   THIS GATE owns trusted Termux bootstrap, LD_PRELOAD validation, trusted
#   Cargo/Rustc resolution, clean-target removal, the fresh Cargo build,
#   binary version verification, and resolution of the exact absolute paths
#   passed to the adapter (trusted python, freshly built rust binary,
#   inherited python entry, inherited frozen reason map).
#   THE ADAPTER (verify/structured_verdict_v01/adapter.py) executes only what
#   this gate explicitly gives it; it never searches PATH, never builds, and
#   makes no trust claim.
#
# Composition, not duplication: the trusted-execution machinery is the
# ADOPTED Move 79 bootstrap (tools/gate_bootstrap.sh) and build helpers
# (tools/gate_lib.sh), sourced unchanged. The COMPLETE adopted Move 80
# adoption gate (tools/check_move80_corrupted_bundle_adoption.sh) is invoked
# as a child process exactly once; it ALREADY composes and verifies the full
# Move 79 regression, so the Move 79 gate is NOT invoked again here.
#
# Required inputs:
#   REAL_MOVE78=<adopted Move 78 v10 zip>   (forwarded to the Move 80 gate)
#   REAL_705=<Move 70.5 zip>                (forwarded to the Move 80 gate)
#   REAL_MOVE79=<adopted Move 79 v27 zip>   (forwarded to the Move 80 gate)
#   REAL_MOVE80=<adopted Move 80 v07 zip>   (Move 81 baseline immutability
#       source: hash-verified with the trusted sha256sum, safety-inspected,
#       and every inherited candidate file compared DIRECTLY against its
#       member bytes -- a candidate-contained inventory is never trusted)
#   REAL_V20=<path>                          (optional; forwarded)
#
# Final markers on success (exit 0):
#   MOVE_81_BASELINE_IMMUTABILITY: PASS
#   MOVE_81_STRUCTURED_SCHEMA: PASS
#   MOVE_81_CANONICAL_OUTPUT: PASS
#   MOVE_81_MAPPING_FIDELITY: PASS
#   MOVE_81_FAIL_CLOSED: PASS
#   MOVE_81_COMPARISON_INTEGRITY: PASS
#   MOVE_81_DEFAULT_OUTPUT_PRESERVATION: PASS
#   MOVE_80_REGRESSION_GATE: PASS
#   SYSTEM_AGREEMENT_RESULT: FAIL
#   SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED
#   MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: PASS
#
# The inner SYSTEM_AGREEMENT_RESULT: FAIL is the Move 79 instrument (run
# inside the Move 80 child gate) honestly reporting the two adopted
# behavioural divergences; it remains expected.
set -u
export PYTHONDONTWRITEBYTECODE=1

# (0a) CAPTURE the inherited LD_PRELOAD FIRST, with a shell assignment only.
GATE_INHERITED_LD_PRELOAD=${LD_PRELOAD-}
readonly GATE_INHERITED_LD_PRELOAD

# (0b) Sanitize dangerous inherited environment with shell BUILT-INS.
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP LD_PRELOAD LD_LIBRARY_PATH ENV \
      BASH_ENV CDPATH CARGO CARGO_HOME RUSTC RUSTC_WRAPPER \
      RUSTC_WORKSPACE_WRAPPER RUSTFLAGS CARGO_ENCODED_RUSTFLAGS \
      CARGO_BUILD_RUSTC CARGO_BUILD_RUSTC_WRAPPER CARGO_TARGET_DIR \
      2>/dev/null || true

# (1) Argument validation -- built-ins only.
if [ -z "${REAL_MOVE78:-}" ] || [ -z "${REAL_705:-}" ] \
   || [ -z "${REAL_MOVE79:-}" ] || [ -z "${REAL_MOVE80:-}" ]; then
    _missing=""
    [ -z "${REAL_MOVE78:-}" ] && _missing="$_missing REAL_MOVE78"
    [ -z "${REAL_705:-}" ] && _missing="$_missing REAL_705"
    [ -z "${REAL_MOVE79:-}" ] && _missing="$_missing REAL_MOVE79"
    [ -z "${REAL_MOVE80:-}" ] && _missing="$_missing REAL_MOVE80"
    echo "Required input(s) not supplied:$_missing"
    echo "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: USAGE (missing:$_missing)"
    exit 2
fi

# (1b) Missing-preload rejection with built-ins only (Termux host).
if [ -d /data/data/com.termux/files/usr ] && [ -z "$GATE_INHERITED_LD_PRELOAD" ]; then
    echo "the legitimate Termux exec preload (libtermux-exec.so) is absent."
    echo "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: FAIL (missing Termux exec preload)"
    exit 1
fi

# (2) Canonicalise $0 with the LITERAL trusted readlink; derive ROOT from
#     the real path only. NO PATH lookup and NO external dirname/pwd may
#     run before trust is established.
_TRUSTED_READLINK=/data/data/com.termux/files/usr/bin/readlink
if [ ! -x "$_TRUSTED_READLINK" ]; then
    echo "trusted readlink absent at $_TRUSTED_READLINK (this gate runs only on Termux)"
    echo "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
    exit 3
fi
SCRIPT_REAL=$("$_TRUSTED_READLINK" -f -- "$0") || SCRIPT_REAL=""
case "$SCRIPT_REAL" in
    */tools/check_move81_structured_verdict_adoption.sh) : ;;
    *)
        echo "refusing: canonical script path is not the genuine named gate ($SCRIPT_REAL)"
        echo "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: FAIL (untrusted script path)"
        exit 1 ;;
esac
if [ ! -f "$SCRIPT_REAL" ]; then
    echo "refusing: canonical script target is not a regular file"
    echo "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: FAIL (untrusted script path)"
    exit 1
fi
_SCRIPT_DIR=${SCRIPT_REAL%/*}
ROOT=${_SCRIPT_DIR%/*}
cd "$ROOT" || exit 2

# (3) Source ONLY the adopted bootstrap before trust exists.
. "$ROOT/tools/gate_bootstrap.sh"

fail=0
ok(){ printf "  OK    %s\n" "$1"; }
bad(){ printf "  FAIL  %s\n" "$1"; fail=1; }
die(){ echo "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: FAIL ($1)"; exit 1; }

# Warning-clean stderr policy: a child's stderr must be EMPTY. Exit 0 is
# NOT proof. Prints the captured stderr before failing.
gate_require_clean_stderr(){
    _grcs_file=$1; _grcs_label=$2
    if [ -s "$_grcs_file" ]; then
        echo "  $_grcs_label stderr (must be empty):"
        sed 's/^/    /' "$_grcs_file"
        bad "$_grcs_label emitted stderr (exit 0 is not proof of warning-clean)"
        return 1
    fi
    if grep -E -q "ResourceWarning|Exception ignored in:|unclosed file" \
        "$_grcs_file"; then
        echo "  $_grcs_label stderr diagnostics:"
        sed 's/^/    /' "$_grcs_file"
        bad "$_grcs_label emitted a ResourceWarning/unclosed-file diagnostic"
        return 1
    fi
    return 0
}

# Dump COMPLETE focused stdout+stderr (never truncated) with markers.
gate_dump_focused_failure(){
    _gdf_out=$1; _gdf_err=$2; _gdf_rc=$3
    echo "---- BEGIN FOCUSED TEST STDOUT (complete, untruncated) ----"
    cat "$_gdf_out"
    echo "---- END FOCUSED TEST STDOUT ----"
    echo "---- BEGIN FOCUSED TEST STDERR (complete, untruncated) ----"
    cat "$_gdf_err"
    echo "---- END FOCUSED TEST STDERR ----"
    echo "focused-suite exit code: $_gdf_rc"
}

# (4) Establish trust, following the ADOPTED bootstrap protocol exactly:
#     run gate_bootstrap, capture BOOT_RC, classify exit 3 as an honest
#     INCONCLUSIVE (no trusted Termux toolchain) and any other nonzero as a
#     controlled FAIL, then install the cleanup traps BEFORE any further
#     temporary file is created or tracked.
echo ""
echo "BOOTSTRAP: establishing the trusted execution environment"
gate_bootstrap "$GATE_INHERITED_LD_PRELOAD"
BOOT_RC=$?
if [ "$BOOT_RC" -eq 3 ]; then
    echo "  trusted Termux toolchain is not present on this host."
    echo "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
    exit 3
elif [ "$BOOT_RC" -ne 0 ]; then
    if [ "${GATE_PRELOAD_FAIL:-}" = missing ]; then
        echo "  the legitimate Termux exec preload (libtermux-exec.so) is absent."
        die "missing Termux exec preload"
    elif [ "${GATE_PRELOAD_FAIL:-}" = invalid ]; then
        echo "  the inherited LD_PRELOAD is not the sole legitimate Termux exec preload."
        die "untrusted Termux exec preload"
    else
        echo "  refusing to run in an untrusted environment."
        die "untrusted environment"
    fi
fi
# EXIT/HUP/INT/TERM cleanup, temporary CARGO_HOME removal and tracked
# mktemp cleanup all depend on these traps being installed here, before
# anything is tracked.
gate_install_traps

# (5) Source the adopted build helpers (post-bootstrap).
. "$ROOT/tools/gate_lib.sh"

# (6) Prove trusted NESTED execution works before the subprocess-heavy
#     focused suite and the adapter measurements run.
echo ""
echo "NESTED EXEC: verifying trusted nested process execution"
if gate_nested_exec_probe; then
    echo "TERMUX_NESTED_EXEC_CHECK: PASS"
else
    echo "TERMUX_NESTED_EXEC_CHECK: FAIL"
    echo "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: FAIL (nested exec)"
    exit 1
fi

P="$ROOT/verify/structured_verdict_v01"
PACK="$ROOT/verify/corrupted_bundle_pack_v01"

# =========================================================================
# STAGE A -- baseline immutability against the real adopted Move 80 v07 zip.
# =========================================================================
echo "STAGE A: baseline immutability (candidate vs real Move 80 v07 zip)"
M80_ZIP=$("$TRUSTED_READLINK" -f -- "$REAL_MOVE80") || M80_ZIP=""
case "$M80_ZIP" in
    /*) : ;;
    *)  bad "REAL_MOVE80 did not canonicalise to an absolute path"
        echo "MOVE_81_BASELINE_IMMUTABILITY: FAIL"; die "baseline path" ;;
esac
if [ ! -f "$M80_ZIP" ]; then
    bad "REAL_MOVE80 is not a regular file: $M80_ZIP"
    echo "MOVE_81_BASELINE_IMMUTABILITY: FAIL"; die "baseline file"
fi
# Hash-verify the supplied baseline with the TRUSTED sha256sum BEFORE any
# member comparison. A different, byte-modified, or merely renamed ZIP
# cannot become the authority.
_M80_SHA=$("$TRUSTED_SHA256SUM" "$M80_ZIP"); _M80_SHA=${_M80_SHA%% *}
_M80_EXPECT=8c08342efae3b17458e33c6ae54ff42bf79d6759170b46cfbf32ef218d0dd2ad
if [ "$_M80_SHA" != "$_M80_EXPECT" ]; then
    bad "supplied Move 80 zip sha256 $_M80_SHA != adopted $_M80_EXPECT"
    echo "MOVE_81_BASELINE_IMMUTABILITY: FAIL"; die "baseline zip hash"
fi
echo "REAL_MOVE80 verified by trusted sha256sum:"
echo "$_M80_EXPECT"
ok "REAL_MOVE80 verified by trusted sha256sum: $_M80_EXPECT"
_A_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_A_ERR"
_A_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_A_OUT"
"$TRUSTED_PYTHON3" -B "$P/check_move81_inherited.py" \
    --baseline-zip "$M80_ZIP" --root "$ROOT" \
    --expect-sha256 "$_M80_EXPECT" \
    --allowlist "$P/allowlist_move81.json" >"$_A_OUT" 2>"$_A_ERR"
_a_rc=$?
echo "---- BEGIN BASELINE SAFETY + INHERITED-DIFF EVIDENCE ----"
cat "$_A_OUT"
echo "---- END BASELINE SAFETY + INHERITED-DIFF EVIDENCE ----"
if [ -s "$_A_ERR" ]; then
    echo "  baseline checker stderr (must be empty):"
    sed 's/^/    /' "$_A_ERR"
    bad "baseline checker emitted stderr"
    echo "MOVE_81_BASELINE_IMMUTABILITY: FAIL"; die "baseline stderr"
fi
if [ "$_a_rc" -ne 0 ]; then
    bad "candidate does not match the real Move 80 v07 baseline + Move 81 allowlist"
    echo "MOVE_81_BASELINE_IMMUTABILITY: FAIL"; die "baseline immutability"
fi
ok "every inherited file byte-identical to Move 80 v07; additions match the Move 81 allowlist"
BASELINE_IMMUTABILITY=PASS

# =========================================================================
# STAGE B -- gate-owned fresh build of witness-verify (rust/ unchanged).
# =========================================================================
echo "STAGE B: gate-owned fresh Rust build (rust/ unchanged)"
if ! gate_clean_target; then
    bad "could not remove rust/target"; die "target cleanup"
fi
ok "rust/target removed; no stale executable can be reused"
BUILT=$(gate_build_once_production)
if [ $? -ne 0 ] || [ -z "$BUILT" ]; then
    bad "clean build did not produce the executable"; die "build"
fi
RUST_ABS=$("$TRUSTED_READLINK" -f -- "$BUILT") || RUST_ABS=""
case "$RUST_ABS" in
    /*) : ;;
    *)  bad "built binary path did not resolve to an absolute path"
        die "binary path" ;;
esac
if [ "$RUST_ABS" != "$ROOT/rust/target/debug/witness-verify" ]; then
    bad "resolved binary $RUST_ABS is not the freshly built gate target"
    die "binary path"
fi
if [ ! -f "$RUST_ABS" ] || [ ! -x "$RUST_ABS" ]; then
    bad "built binary is not an executable regular file"; die "binary path"
fi
ok "freshly built binary resolved: $RUST_ABS"
_EXPECT_VERSION="0.0.8-step79-diagnostics"
_REPORTED=$("$RUST_ABS" verify /nonexistent 2>/dev/null \
            | "$TRUSTED_PYTHON3" -B tools/read_version.py)
if [ "$_REPORTED" != "$_EXPECT_VERSION" ]; then
    bad "built binary reports version '$_REPORTED', expected '$_EXPECT_VERSION'"
    die "binary version"
fi
ok "built binary reports $_EXPECT_VERSION"

# All Cargo tests (rust/ unchanged; still proven fresh here).
echo "STAGE B2: cargo test (fresh)"
_CT_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_CT_OUT"
_CT_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_CT_ERR"
( cd "$ROOT/rust" && "$TRUSTED_CARGO" test --workspace ) \
    >"$_CT_OUT" 2>"$_CT_ERR"; _ct_rc=$?
if [ "$_ct_rc" -ne 0 ]; then
    echo "  cargo test failed:"; tail -20 "$_CT_OUT" | sed 's/^/    /'
    tail -20 "$_CT_ERR" | sed 's/^/    /'
    bad "cargo test"; die "cargo test"
fi
ok "cargo test passed (fresh build)"

# Resolve the trusted python, inherited python entry, and frozen reason
# map to VALIDATED ABSOLUTE paths through the trusted readlink (post-
# bootstrap). The adapter is handed only these gate-resolved absolute
# paths; it never searches PATH and makes no trust claim of its own.
_PY_ENTRY_RAW="$ROOT/src/12_companion_cli_v031/companion.py"
_REASON_MAP_RAW="$ROOT/verify/agreement_harness_v01/reason_map.json"
_CONTRACT_RAW="$ROOT/verify/agreement_harness_v01/corpus/bundle_cases.json"
PY_ENTRY=$("$TRUSTED_READLINK" -f -- "$_PY_ENTRY_RAW") || PY_ENTRY=""
REASON_MAP=$("$TRUSTED_READLINK" -f -- "$_REASON_MAP_RAW") || REASON_MAP=""
CONTRACT=$("$TRUSTED_READLINK" -f -- "$_CONTRACT_RAW") || CONTRACT=""
TRUSTED_PY=$("$TRUSTED_READLINK" -f -- "$TRUSTED_PYTHON3") || TRUSTED_PY=""
ADAPTER=$("$TRUSTED_READLINK" -f -- "$P/adapter.py") || ADAPTER=""
for _pv in "PY_ENTRY=$PY_ENTRY" "REASON_MAP=$REASON_MAP" \
           "CONTRACT=$CONTRACT" "TRUSTED_PY=$TRUSTED_PY" \
           "ADAPTER=$ADAPTER"; do
    _pval=${_pv#*=}
    case "$_pval" in
        /*) : ;;
        *)  bad "adapter path did not resolve to an absolute path: $_pv"
            die "adapter path" ;;
    esac
    if [ ! -f "$_pval" ]; then
        bad "adapter path is not a regular file: $_pv"; die "adapter path"
    fi
done
if [ ! -x "$TRUSTED_PY" ]; then
    bad "resolved trusted python is not executable"; die "adapter path"
fi
ok "adapter authority paths resolved + validated (python entry, reason map, contract, interpreter, adapter)"

# =========================================================================
# STAGE C -- Move 81 focused suite (stdout-bound, pinned count, clean stderr).
# =========================================================================
echo "STAGE C: Move 81 focused structured-verdict suite"
_MT_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_MT_OUT"
_MT_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_MT_ERR"
( cd "$P" && MOVE81_TEST_SH="$TRUSTED_SH" \
  "$TRUSTED_PYTHON3" -B -W error::ResourceWarning \
  structured_tests.py ) >"$_MT_OUT" 2>"$_MT_ERR"; _mt_rc=$?
if [ "$_mt_rc" -ne 0 ]; then
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused tests failed (exit $_mt_rc)"; die "focused tests"
fi
tail -3 "$_MT_OUT" | sed 's/^/    /'
gate_require_clean_stderr "$_MT_ERR" "focused tests" || {
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    die "focused tests stderr"; }
if grep -q "skipped" "$_MT_OUT"; then
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused tests skipped cases"; die "focused tests skipped"
fi
_EXPECT_N=$("$TRUSTED_PYTHON3" -B -c 'import sys
with open(sys.argv[1]) as h:
    sys.stdout.write(h.read().strip())' "$P/EXPECTED_TEST_COUNT.txt")
if grep -q "^Ran ${_EXPECT_N} tests" "$_MT_OUT"; then
    ok "focused stdout reports exactly Ran ${_EXPECT_N} tests"
else
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused test count is not the pinned ${_EXPECT_N}"; die "focused count"
fi
if ! grep -q "^OK$" "$_MT_OUT"; then
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused stdout lacks the final OK line"; die "focused OK"
fi
for _bad_marker in "FAILED" "errors=" "failures=" "skipped="; do
    if grep -q "$_bad_marker" "$_MT_OUT"; then
        gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
        bad "focused stdout contains forbidden marker: $_bad_marker"
        die "focused forbidden marker"
    fi
done
ok "focused suite PASS (no skips, exact count, stderr empty)"
STRUCTURED_SCHEMA=PASS
FAIL_CLOSED=PASS
COMPARISON_INTEGRITY=PASS

# =========================================================================
# STAGE D -- live determinism + mapping fidelity against the FRESH binary.
# =========================================================================
echo "STAGE D: live adapter determinism + mapping fidelity (fresh binary)"
BUNDLE=$("$TRUSTED_READLINK" -f -- \
    "$ROOT/freeze_record/python_behaviour_freeze_v01/reference_bundle") \
    || BUNDLE=""
case "$BUNDLE" in /*) : ;; *) die "clean bundle path" ;; esac
[ -d "$BUNDLE" ] || die "clean bundle is not a directory"

# Python lane, twice, must be byte-identical and PASS/0.
_D1=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_D1"
_D2=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_D2"
_DE=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_DE"
"$TRUSTED_PY" -B "$ADAPTER" verdict --lane python_bundle \
    --input "$BUNDLE" --reason-map "$REASON_MAP" \
    --python-bin "$TRUSTED_PY" --python-entry "$PY_ENTRY" \
    >"$_D1" 2>"$_DE"; _d1_rc=$?
if [ -s "$_DE" ]; then
    echo "  adapter stderr (must be empty):"; sed 's/^/    /' "$_DE"
    bad "python-lane adapter emitted stderr"; die "adapter stderr"
fi
_DE2=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_DE2"
"$TRUSTED_PY" -B "$ADAPTER" verdict --lane python_bundle \
    --input "$BUNDLE" --reason-map "$REASON_MAP" \
    --python-bin "$TRUSTED_PY" --python-entry "$PY_ENTRY" \
    >"$_D2" 2>"$_DE2"; _d2_rc=$?
# The SECOND deterministic run is held to exactly the same strict stderr
# policy as the first: discarding it could not prove both runs were
# warning-clean.
if [ -s "$_DE2" ]; then
    echo "  adapter stderr, second determinism run (must be empty):"
    sed 's/^/    /' "$_DE2"
    bad "python-lane adapter emitted stderr on the second determinism run"
    die "adapter stderr"
fi
if [ "$_d1_rc" -ne 0 ] || [ "$_d2_rc" -ne 0 ]; then
    bad "python-lane adapter exit not 0 (PASS): $_d1_rc / $_d2_rc"
    die "python lane verdict"
fi
if ! "$TRUSTED_PY" -B -c 'import sys
a=open(sys.argv[1],"rb").read(); b=open(sys.argv[2],"rb").read()
sys.exit(0 if a==b else 1)' "$_D1" "$_D2"; then
    bad "python-lane adapter output not byte-identical across runs"
    die "determinism"
fi
ok "python-lane structured verdict deterministic + PASS/0, stderr empty"

# Rust lane against the FRESH binary on the clean bundle: INCONCLUSIVE/3.
_R1=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_R1"
_RE=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RE"
"$TRUSTED_PY" -B "$ADAPTER" verdict --lane rust_bundle \
    --input "$BUNDLE" --reason-map "$REASON_MAP" \
    --rust-bin "$RUST_ABS" >"$_R1" 2>"$_RE"; _r1_rc=$?
if [ -s "$_RE" ]; then
    echo "  adapter stderr (must be empty):"; sed 's/^/    /' "$_RE"
    bad "rust-lane adapter emitted stderr"; die "adapter stderr"
fi
if [ "$_r1_rc" -ne 3 ]; then
    bad "rust-lane clean bundle expected INCONCLUSIVE/3, got exit $_r1_rc"
    echo "  output:"; sed 's/^/    /' "$_R1"
    die "rust honesty"
fi
if ! grep -q '"verdict":"INCONCLUSIVE"' "$_R1" \
   || grep -q '"verdict":"PASS"' "$_R1"; then
    bad "rust-lane verdict not INCONCLUSIVE (honesty property violated)"
    die "rust honesty"
fi
ok "rust-lane structured verdict INCONCLUSIVE/3 on clean bundle (no PASS path)"

# Live comparison against the frozen authority on the clean_control case:
# both lanes in scope, both match their adopted expected outcomes ->
# AGREEMENT, exit 0, both complete lane records preserved.
_C1=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_C1"
_CE=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_CE"
"$TRUSTED_PY" -B "$ADAPTER" compare --input "$BUNDLE" \
    --reason-map "$REASON_MAP" --python-bin "$TRUSTED_PY" \
    --python-entry "$PY_ENTRY" --rust-bin "$RUST_ABS" \
    --case-id clean_control --comparison-contract "$CONTRACT" \
    >"$_C1" 2>"$_CE"; _c1_rc=$?
if [ -s "$_CE" ]; then
    echo "  compare stderr (must be empty):"; sed 's/^/    /' "$_CE"
    bad "compare emitted stderr"; die "compare stderr"
fi
if [ "$_c1_rc" -ne 0 ]; then
    bad "clean_control comparison expected exit 0, got $_c1_rc"
    sed 's/^/    /' "$_C1"; die "comparison"
fi
if ! grep -q '"comparison_status":"AGREEMENT"' "$_C1"; then
    bad "clean_control comparison_status not AGREEMENT"
    sed 's/^/    /' "$_C1"; die "comparison"
fi
if grep -q '"comparison_status":"PASS"\|"comparison_status":"FAIL"\|"comparison_status":"INCONCLUSIVE"' "$_C1"; then
    bad "comparison_status was labelled with a verdict vocabulary"
    die "comparison"
fi
ok "live comparison authority: clean_control AGREEMENT, exit 0, no verdict-labelled status"
MAPPING_FIDELITY=PASS
CANONICAL_OUTPUT=PASS

# =========================================================================
# STAGE E -- default-output preservation (legacy commands unchanged).
# =========================================================================
echo "STAGE E: legacy default output preservation"
_L1=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_L1"
"$RUST_ABS" verify "$BUNDLE" >"$_L1" 2>/dev/null
if grep -q '"verifier":"witness-verify"\|"verifier": "witness-verify"' "$_L1"; then
    ok "legacy Rust verify default output shape unchanged"
else
    bad "legacy Rust verify default output shape changed"
    sed 's/^/    /' "$_L1"; die "default output"
fi
# Python legacy verify still emits {verify_ok, companion_status, reason}.
_L2=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_L2"
"$TRUSTED_PYTHON3" -B "$PY_ENTRY" verify --run "$BUNDLE" >"$_L2" 2>/dev/null
if "$TRUSTED_PYTHON3" -B -c 'import json,sys
o=json.load(open(sys.argv[1]))
sys.exit(0 if set(o)=={"verify_ok","companion_status","reason"} else 1)' "$_L2"; then
    ok "legacy Python verify default output shape unchanged"
else
    bad "legacy Python verify default output shape changed"; die "default output"
fi
DEFAULT_OUTPUT_PRESERVATION=PASS

# =========================================================================
# STAGE F -- ONE complete Move 80 adoption/regression child gate.
#            (It ALREADY composes and verifies the full Move 79 regression.)
# =========================================================================
echo "STAGE F: complete Move 80 adoption/regression child gate (includes Move 79)"
# The Move 80 gate validates ITS OWN tree against the real Move 79 v27 zip
# and permits only the Move 80 addition set. Running it from the Move 81
# candidate root would therefore see the ten legitimate Move 81 additions
# as undeclared relative to Move 79 and fail -- a gate-composition defect,
# not a real regression. The complete, UNCHANGED Move 80 gate is instead
# run from a private, safely extracted copy of the exact adopted
# REAL_MOVE80 zip. No Move 81 file is copied or overlaid into that tree,
# and the Move 80 gate itself is never weakened, patched or bypassed.
_M80_EXTRACT=$("$TRUSTED_MKTEMP" -d) || die "could not create extraction dir"
gate_track_tmp "$_M80_EXTRACT"
_M80_XOUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M80_XOUT"
_M80_XERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M80_XERR"
# Hash is re-verified and the archive fully safety-inspected (duplicates,
# traversal, absolute paths, backslash ambiguity, symlinks, special files,
# encryption, single canonical root, CRC) BEFORE a single byte is written.
"$TRUSTED_PYTHON3" -B "$P/check_move81_inherited.py" \
    --baseline-zip "$M80_ZIP" --expect-sha256 "$_M80_EXPECT" \
    --extract-to "$_M80_EXTRACT" >"$_M80_XOUT" 2>"$_M80_XERR"
_m80_x_rc=$?
echo "---- BEGIN REAL_MOVE80 VALIDATED EXTRACTION EVIDENCE ----"
cat "$_M80_XOUT"
echo "---- END REAL_MOVE80 VALIDATED EXTRACTION EVIDENCE ----"
if [ -s "$_M80_XERR" ]; then
    echo "  extraction stderr (must be empty):"
    sed 's/^/    /' "$_M80_XERR"
    bad "baseline extraction emitted stderr"; die "move80 extraction"
fi
if [ "$_m80_x_rc" -ne 0 ]; then
    bad "REAL_MOVE80 could not be verified and safely extracted"
    die "move80 extraction"
fi
_M80_ROOT="$_M80_EXTRACT/project-witness-main"
if [ ! -d "$_M80_ROOT" ] \
   || [ ! -f "$_M80_ROOT/tools/check_move80_corrupted_bundle_adoption.sh" ]; then
    bad "extracted Move 80 root is not a complete Move 80 tree"
    die "move80 extraction"
fi
ok "REAL_MOVE80 extracted to a private gate-owned directory"

_M80_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M80_OUT"
# Invoked FROM the extracted Move 80 root, so the Move 80 gate compares the
# genuine adopted Move 80 tree against Move 79 -- exactly as it does when
# run standalone.
( cd "$_M80_ROOT" \
  && REAL_MOVE78="$REAL_MOVE78" REAL_705="$REAL_705" \
     REAL_MOVE79="$REAL_MOVE79" REAL_V20="${REAL_V20:-}" \
     LD_PRELOAD="$GATE_PRELOAD" \
     "$TRUSTED_SH" tools/check_move80_corrupted_bundle_adoption.sh \
) >"$_M80_OUT" 2>&1; _m80_rc=$?
echo "---- BEGIN COMPLETE MOVE 80 CHILD GATE OUTPUT (retained) ----"
cat "$_M80_OUT"
echo "---- END COMPLETE MOVE 80 CHILD GATE OUTPUT ----"
if [ "$_m80_rc" -ne 0 ]; then
    bad "Move 80 child adoption gate failed (exit $_m80_rc)"
    die "move80 regression"
fi
# Require the exact adopted Move 80 markers, including the expected inner
# system-agreement FAIL.
for _need in \
    "MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: PASS" \
    "MOVE_79_REGRESSION_GATE: PASS" \
    "SYSTEM_AGREEMENT_RESULT: FAIL" \
    "SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED"; do
    if ! grep -qF "$_need" "$_M80_OUT"; then
        bad "Move 80 child gate missing expected marker: $_need"
        die "move80 markers"
    fi
done
ok "Move 80 child gate PASS (Move 79 regression included; inner agreement FAIL expected)"
# Prompt removal on the success path; the tracked-item trap also removes it
# on every other exit path (EXIT and HUP/INT/TERM).
rm -rf "$_M80_EXTRACT"
MOVE_80_REGRESSION=PASS

# =========================================================================
# STAGE G -- package hygiene (reuse the adopted checker).
# =========================================================================
echo "STAGE G: package hygiene"
_PH_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_PH_OUT"
if "$TRUSTED_SH" tools/check_package_hygiene.sh >"$_PH_OUT" 2>&1; then
    ok "package hygiene PASS"
else
    cat "$_PH_OUT" | sed 's/^/    /'
    bad "package hygiene"; die "package hygiene"
fi

if [ "$fail" -ne 0 ]; then
    die "one or more checks failed"
fi

# =========================================================================
# FINAL MARKERS
# =========================================================================
echo ""
echo "==========================================================="
echo "MOVE_81_BASELINE_IMMUTABILITY: $BASELINE_IMMUTABILITY"
echo "MOVE_81_STRUCTURED_SCHEMA: $STRUCTURED_SCHEMA"
echo "MOVE_81_CANONICAL_OUTPUT: $CANONICAL_OUTPUT"
echo "MOVE_81_MAPPING_FIDELITY: $MAPPING_FIDELITY"
echo "MOVE_81_FAIL_CLOSED: $FAIL_CLOSED"
echo "MOVE_81_COMPARISON_INTEGRITY: $COMPARISON_INTEGRITY"
echo "MOVE_81_DEFAULT_OUTPUT_PRESERVATION: $DEFAULT_OUTPUT_PRESERVATION"
echo "MOVE_80_REGRESSION_GATE: $MOVE_80_REGRESSION"
echo "SYSTEM_AGREEMENT_RESULT: FAIL"
echo "SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED"
echo "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: PASS"
echo "exit_code: 0"
exit 0
