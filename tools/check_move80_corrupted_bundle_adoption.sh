#!/bin/sh
# MOVE 80 CORRUPTED BUNDLE ADOPTION GATE.
#
# Responsibility split (ruled at adoption review):
#   THIS GATE owns trusted Termux bootstrap, LD_PRELOAD validation, trusted
#   Cargo/Rustc resolution, clean-target removal, the fresh Cargo build,
#   source/provenance binding, binary version verification, stale-executable
#   rejection, and resolution of the final ABSOLUTE built-binary path.
#   THE FOCUSED RUNNER (verify/corrupted_bundle_pack_v01/run_move80.py) only
#   executes the exact binary this gate supplies through --rust-bin and
#   evaluates fixture results. It never searches PATH, never builds, and
#   makes no trust claim.
#
# Composition, not duplication: the trusted-execution machinery is the
# ADOPTED Move 79 bootstrap (tools/gate_bootstrap.sh) and build helpers
# (tools/gate_lib.sh), sourced unchanged. The complete adopted Move 79
# regression gate (tools/check_move79_instrument_adoption.sh) is invoked as
# a child process, never copied.
#
# Required inputs:
#   REAL_MOVE78=<adopted Move 78 v10 zip>   (forwarded to the Move 79 gate)
#   REAL_705=<Move 70.5 zip>                (forwarded to the Move 79 gate)
#   REAL_MOVE79=<adopted Move 79 v27 zip>   (baseline immutability source:
#       hash-verified with the trusted sha256sum, safety-inspected, and
#       every inherited candidate file compared DIRECTLY against its
#       member bytes -- a candidate-contained inventory is never trusted)
#   REAL_V20=<path>                          (optional)
#
# Final markers on success (exit 0):
#   MOVE_80_BASELINE_IMMUTABILITY: PASS
#   MOVE_80_FIXTURE_REPRODUCIBILITY: PASS
#   MOVE_80_REQUIRED_CASES: 8/8 PASS
#   MOVE_80_NEGATIVE_DETECTION: PASS
#   MOVE_80_ORDER_INDEPENDENCE: PASS
#   MOVE_79_REGRESSION_GATE: PASS
#   SYSTEM_AGREEMENT_RESULT: FAIL
#   SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED
#   MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: PASS
#
# MOVE_80_REQUIRED_CASES: 8/8 PASS means the verifiers produced the DECLARED
# expected outcomes for all eight fixtures. It does NOT mean the corrupted
# bundles verified successfully. The inner SYSTEM_AGREEMENT_RESULT: FAIL is
# the Move 79 instrument honestly reporting the two adopted behavioural
# divergences; it remains expected.
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

# (1) Argument validation — built-ins only.
if [ -z "${REAL_MOVE78:-}" ] || [ -z "${REAL_705:-}" ] || [ -z "${REAL_MOVE79:-}" ]; then
    _missing=""
    [ -z "${REAL_MOVE78:-}" ] && _missing="$_missing REAL_MOVE78"
    [ -z "${REAL_705:-}" ]    && _missing="$_missing REAL_705"
    [ -z "${REAL_MOVE79:-}" ] && _missing="$_missing REAL_MOVE79"
    echo "Required input(s) not supplied:$_missing"
    echo "MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: USAGE (missing:$_missing)"
    exit 2
fi

# (1b) Missing-preload rejection with built-ins only (Termux host).
if [ -d /data/data/com.termux/files/usr ] && [ -z "$GATE_INHERITED_LD_PRELOAD" ]; then
    echo "the legitimate Termux exec preload (libtermux-exec.so) is absent."
    echo "MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: FAIL (missing Termux exec preload)"
    exit 1
fi

# (2) Canonicalise $0 with the LITERAL trusted readlink; derive ROOT from
#     the real path only.
_TRUSTED_READLINK=/data/data/com.termux/files/usr/bin/readlink
if [ ! -x "$_TRUSTED_READLINK" ]; then
    echo "trusted readlink absent at $_TRUSTED_READLINK (this gate runs only on Termux)"
    echo "MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
    exit 3
fi
SCRIPT_REAL=$("$_TRUSTED_READLINK" -f -- "$0") || SCRIPT_REAL=""
case "$SCRIPT_REAL" in
    */tools/check_move80_corrupted_bundle_adoption.sh) : ;;
    *)
        echo "refusing: canonical script path is not the genuine named gate ($SCRIPT_REAL)"
        echo "MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: FAIL (untrusted script path)"
        exit 1 ;;
esac
if [ ! -f "$SCRIPT_REAL" ]; then
    echo "refusing: canonical script target is not a regular file"
    echo "MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: FAIL (untrusted script path)"
    exit 1
fi
_SCRIPT_DIR=${SCRIPT_REAL%/*}
ROOT=${_SCRIPT_DIR%/*}
cd "$ROOT" || exit 2

# (3) Source ONLY the adopted bootstrap before trust exists.
. "$ROOT/tools/gate_bootstrap.sh"
P="verify/corrupted_bundle_pack_v01"
fail=0
ok(){ printf "  OK    %s\n" "$1"; }
bad(){ printf "  FAIL  %s\n" "$1"; fail=1; }
die(){ echo "MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: FAIL ($1)"; exit 1; }

# Warning-clean stderr policy (B2): a child's stderr must be EMPTY. Exit 0
# is NOT proof of warning-cleanliness. The captured stderr is printed
# before failing so the first-run transcript preserves the cause. Any
# bytes at all, or the named diagnostic substrings, fail the check.
# Returns 0 (clean) or 1 (dirty; caller should die).
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

# Dump the COMPLETE focused-test stdout and stderr (never truncated) with
# explicit markers, then report the exact exit code. Used on any failing
# focused run so the adoption transcript preserves the full test name and
# traceback without a separate diagnostic run.
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

echo "==========================================================="
echo " MOVE 80 CORRUPTED BUNDLE ADOPTION GATE"
echo "==========================================================="
echo ""
echo "BOOTSTRAP: establishing the trusted execution environment"
gate_bootstrap "$GATE_INHERITED_LD_PRELOAD"
BOOT_RC=$?
if [ "$BOOT_RC" -eq 3 ]; then
    echo "  trusted Termux toolchain is not present on this host."
    echo "MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
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
gate_install_traps
. "$ROOT/tools/gate_lib.sh"
ok "trusted bootstrap complete; adopted build helpers sourced"

# -------------------------------------------------------------------------
# (A) BASELINE IMMUTABILITY: adopted artifact pins + inherited-tree diff.
# -------------------------------------------------------------------------
echo ""
echo "STAGE A: baseline immutability"
_IMM=$("$TRUSTED_SH" tools/check_adopted_immutable.sh 2>&1); _imm_rc=$?
printf '%s\n' "$_IMM" | tail -2 | sed 's/^/    /'
if [ "$_imm_rc" -ne 0 ]; then
    bad "adopted artifact pins"
else
    ok "adopted artifacts byte-identical"
fi
M79_ZIP=$("$TRUSTED_READLINK" -f -- "$REAL_MOVE79") || M79_ZIP=""
case "$M79_ZIP" in
    /*) : ;;
    *)  bad "REAL_MOVE79 did not canonicalise to an absolute path"
        echo "MOVE_80_BASELINE_IMMUTABILITY: FAIL"
        die "baseline zip path" ;;
esac
if [ ! -f "$M79_ZIP" ]; then
    bad "REAL_MOVE79 is not a regular file: $M79_ZIP"
    echo "MOVE_80_BASELINE_IMMUTABILITY: FAIL"
    die "baseline zip path"
fi
_M79_SHA=$("$TRUSTED_SHA256SUM" "$M79_ZIP"); _M79_SHA=${_M79_SHA%% *}
_M79_EXPECT=4a95767a3f68ca812c1d543894b65183b82d56f3f8f56e9af61b82c19de1f26b
if [ "$_M79_SHA" != "$_M79_EXPECT" ]; then
    bad "supplied Move 79 zip sha256 $_M79_SHA != adopted $_M79_EXPECT"
    echo "MOVE_80_BASELINE_IMMUTABILITY: FAIL"
    die "baseline zip hash"
fi
ok "REAL_MOVE79 verified by trusted sha256sum: $_M79_EXPECT"
_LIVE_REPORT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_LIVE_REPORT"
_DIFF_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_DIFF_ERR"
"$TRUSTED_PYTHON3" -B "$P/check_inherited_vs_zip.py" \
    --baseline-zip "$M79_ZIP" --report "$_LIVE_REPORT" \
    >/dev/null 2>"$_DIFF_ERR"; _diff_rc=$?
if [ -s "$_DIFF_ERR" ]; then
    echo "  inherited-diff checker stderr (must be empty):"
    sed 's/^/    /' "$_DIFF_ERR"
    bad "inherited-diff checker emitted stderr"
    die "inherited-diff stderr"
fi
if [ "$_diff_rc" -ne 0 ]; then
    bad "inherited-tree comparison against the real v27 zip bytes"
    die "inherited-tree comparison"
fi
echo "---- BEGIN LIVE REAL-V27 INHERITED-DIFF REPORT ----"
cat "$_LIVE_REPORT"
echo "---- END LIVE REAL-V27 INHERITED-DIFF REPORT ----"
# The committed report must be byte-identical to this live comparison, so
# a stale or tampered committed report cannot pass review. Byte-compare
# via the trusted python (cmp/diff are not resolved trusted commands).
if "$TRUSTED_PYTHON3" -B -c 'import sys
with open(sys.argv[1],"rb") as a, open(sys.argv[2],"rb") as b:
    sys.exit(0 if a.read()==b.read() else 1)' \
    "$_LIVE_REPORT" "$P/MOVE_80_ALLOWLIST_DIFF_REPORT.txt"; then
    ok "committed diff report is byte-identical to the live real-v27 comparison"
else
    echo "  committed diff report differs from the live comparison above"
    bad "committed diff report does not match the live real-v27 comparison"
    die "committed diff report mismatch"
fi
if [ "$fail" -ne 0 ]; then
    echo "MOVE_80_BASELINE_IMMUTABILITY: FAIL"
    die "baseline immutability"
fi
BASELINE_IMMUTABILITY=PASS

# -------------------------------------------------------------------------
# (B) MOVE 80 FOCUSED TESTS (warning-clean, controlled executables only).
# -------------------------------------------------------------------------
echo ""
echo "STAGE B: Move 80 focused tests"
_MT_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_MT_OUT"
_MT_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_MT_ERR"
( cd "$P" && M80_BASELINE_ZIP="$M79_ZIP" \
  "$TRUSTED_PYTHON3" -B -W error::ResourceWarning \
  move80_tests.py ) >"$_MT_OUT" 2>"$_MT_ERR"; _mt_rc=$?
# On ANY focused-suite failure, preserve the COMPLETE stdout and stderr
# (test name + traceback included) in the transcript -- never truncated --
# before failing the adoption gate.
if [ "$_mt_rc" -ne 0 ]; then
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused tests failed (exit $_mt_rc)"
    die "focused tests"
fi
tail -3 "$_MT_OUT" | sed 's/^/    /'
gate_require_clean_stderr "$_MT_ERR" "focused tests" || {
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    die "focused tests stderr"
}
if grep -q "skipped" "$_MT_OUT"; then
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused tests skipped cases (the gate requires the full suite)"
    die "focused tests skipped"
fi
# Ordinary unittest reporting is on stdout (the runner streams there), so
# the success accounting must be present there and no failure/error/skip
# markers may appear. The exact test count is pinned in a committed
# marker so a shrunk or partial suite is rejected.
_EXPECT_N=$("$TRUSTED_PYTHON3" -B -c 'import sys
with open(sys.argv[1]) as h:
    sys.stdout.write(h.read().strip())' \
    "$P/EXPECTED_TEST_COUNT.txt")
# Documentation truth-state: the focused-test count stated in the
# packaged README must equal the pinned count. Parse it with the trusted
# interpreter (exactly one match required); fail on drift. This catches a
# stale doc claim even if the suite itself is later modified incorrectly.
_README_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_README_ERR"
_README_N=$("$TRUSTED_PYTHON3" -B -c 'import re, sys
with open(sys.argv[1], encoding="utf-8") as h:
    text = h.read()
m = re.findall(r"focused tests \((\d+)\)", text)
if len(m) != 1:
    sys.stderr.write("README focused-test count not stated exactly once "
                     "(found %d)\n" % len(m)); sys.exit(1)
sys.stdout.write(m[0])' "$P/README.md" 2>"$_README_ERR") || {
    bad "README focused-test count parse failed"
    [ -s "$_README_ERR" ] && sed 's/^/    /' "$_README_ERR"
    die "README count parse"
}
if [ "$_README_N" != "$_EXPECT_N" ]; then
    bad "README focused-test count $_README_N != pinned $_EXPECT_N"
    die "README count drift"
fi
ok "README focused-test count agrees with the pinned count ($_EXPECT_N)"
if grep -q "^Ran ${_EXPECT_N} tests" "$_MT_OUT"; then
    ok "focused stdout reports exactly Ran ${_EXPECT_N} tests"
else
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused test count is not the pinned ${_EXPECT_N}"
    die "focused test count"
fi
if ! grep -q "^OK$" "$_MT_OUT"; then
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused stdout lacks the final OK line"
    die "focused OK"
fi
for _bad_marker in "FAILED" "errors=" "failures=" "skipped="; do
    if grep -q "$_bad_marker" "$_MT_OUT"; then
        gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
        bad "focused stdout contains forbidden marker: $_bad_marker"
        die "focused forbidden marker"
    fi
done
ok "focused test suite PASS (no skips, stdout success accounting exact, stderr empty)"

# Documentation truth-state (B2): derive the FAIL-lane count DIRECTLY from
# the declared matrix in expected_results.json and require the README and
# the machine-readable _meaning_of_case_pass to agree with it (seven of
# eight; only M80-CLEAN-001 has no FAIL lane). Fails if any of the three
# disagree, so a future prose/matrix drift cannot hide.
_SEVEN_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_SEVEN_ERR"
"$TRUSTED_PYTHON3" -B -c 'import json, sys
here = sys.argv[1]
with open(here + "/expected_results.json", encoding="utf-8") as h:
    doc = json.load(h)
cases = doc["cases"]
if len(cases) != 8:
    sys.stderr.write("expected exactly 8 cases, got %d\n" % len(cases))
    sys.exit(1)
fail = set()
for cid, case in cases.items():
    lanes = [v for k, v in case.items()
             if k.endswith("_expected") and isinstance(v, dict)]
    if any(l.get("verdict") == "FAIL" for l in lanes):
        fail.add(cid)
n = len(fail)
if n != 7 or (set(cases) - fail) != {"M80-CLEAN-001"}:
    sys.stderr.write("declared matrix does not show seven-of-eight "
                     "FAIL-lane fixtures (got %d; non-FAIL=%r)\n"
                     % (n, sorted(set(cases) - fail)))
    sys.exit(1)
with open(here + "/README.md", encoding="utf-8") as h:
    readme = h.read()
meaning = doc["_meaning_of_case_pass"]
seven = "seven of the eight fixtures"
six = "six of the eight fixtures"
for label, text in (("README", readme), ("_meaning_of_case_pass", meaning)):
    if seven not in text:
        sys.stderr.write("%s lacks the seven-of-eight statement\n" % label)
        sys.exit(1)
    if six in text:
        sys.stderr.write("%s still has the obsolete six-of-eight "
                         "statement\n" % label)
        sys.exit(1)
sys.stdout.write(str(n))' "$P" >/dev/null 2>"$_SEVEN_ERR" || {
    bad "declared-matrix seven-of-eight truth-state check failed"
    [ -s "$_SEVEN_ERR" ] && sed 's/^/    /' "$_SEVEN_ERR"
    die "seven-of-eight truth-state"
}
ok "declared matrix, README and _meaning_of_case_pass agree: seven of eight fixtures have a FAIL lane"

echo "STAGE B2: Move 80 fixture integrity (warning-clean, separated streams)"
_IC_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_IC_OUT"
_IC_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_IC_ERR"
# Two independent fresh generation directories under a tracked tmp root.
# generate_fixtures.py refuses to write into an existing fixture, so we
# hand it fresh child paths it creates itself.
_IC_ROOT=$("$TRUSTED_MKTEMP" -d); gate_track_tmp "$_IC_ROOT"
_IC_A="$_IC_ROOT/gen_a"
_IC_B="$_IC_ROOT/gen_b"
"$TRUSTED_PYTHON3" -B "$P/generate_fixtures.py" --out "$_IC_A" >/dev/null
"$TRUSTED_PYTHON3" -B "$P/generate_fixtures.py" --out "$_IC_B" >/dev/null
"$TRUSTED_PYTHON3" -B -W error::ResourceWarning "$P/integrity_check.py" \
    --gen-a "$_IC_A" --gen-b "$_IC_B" >"$_IC_OUT" 2>"$_IC_ERR"; _ic_rc=$?
tail -3 "$_IC_OUT" | sed 's/^/    /'
gate_require_clean_stderr "$_IC_ERR" "integrity check" || die "integrity stderr"
if [ "$_ic_rc" -ne 0 ]; then
    bad "fixture integrity"
    die "fixture integrity"
fi
ok "fixture integrity PASS (warning-clean, stderr empty)"

# -------------------------------------------------------------------------
# (C) FIXTURE GENERATION x2 + INTEGRITY (reproducibility, mutations, pins).
# -------------------------------------------------------------------------
echo ""
echo "STAGE C: deterministic fixture generation and integrity"
GEN_A=$("$TRUSTED_MKTEMP" -d); gate_track_tmp "$GEN_A"
GEN_B=$("$TRUSTED_MKTEMP" -d); gate_track_tmp "$GEN_B"
_GA=$("$TRUSTED_PYTHON3" -B "$P/generate_fixtures.py" --out "$GEN_A" 2>&1) \
    || { printf '%s\n' "$_GA" | tail -3; bad "generation A"; die "fixture generation"; }
_GB=$("$TRUSTED_PYTHON3" -B "$P/generate_fixtures.py" --out "$GEN_B" 2>&1) \
    || { printf '%s\n' "$_GB" | tail -3; bad "generation B"; die "fixture generation"; }
ok "two independent generations produced"
_IC=$("$TRUSTED_PYTHON3" -B "$P/integrity_check.py" \
      --gen-a "$GEN_A" --gen-b "$GEN_B" 2>&1); _ic_rc=$?
printf '%s\n' "$_IC" | tail -4 | sed 's/^/    /'
if [ "$_ic_rc" -ne 0 ]; then
    echo "MOVE_80_FIXTURE_REPRODUCIBILITY: FAIL"
    die "fixture integrity"
fi
FIXTURE_REPRODUCIBILITY=PASS
ok "fixture integrity PASS (seed unchanged; declared mutations only; byte-identical generations; pins reproducible)"

# -------------------------------------------------------------------------
# (D) MOVE 79 REGRESSION: invoke the complete adopted gate as a child.
# -------------------------------------------------------------------------
echo ""
echo "STAGE D: complete adopted Move 79 regression gate (child process)"
_M79_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M79_OUT"
REAL_MOVE78="$REAL_MOVE78" REAL_705="$REAL_705" \
    REAL_V20="${REAL_V20:-}" LD_PRELOAD="$GATE_PRELOAD" \
    "$TRUSTED_SH" tools/check_move79_instrument_adoption.sh \
    >"$_M79_OUT" 2>&1
_m79_rc=$?
echo "---- BEGIN COMPLETE MOVE 79 CHILD GATE OUTPUT (retained) ----"
cat "$_M79_OUT"
echo "---- END COMPLETE MOVE 79 CHILD GATE OUTPUT ----"
echo "  declared divergence expectation (reprinted from adopted gate bytes):"
grep -F "EXPECT_DIV_IDS" tools/check_move79_instrument_adoption.sh | sed 's/^/    /'
_EV=$("$TRUSTED_PYTHON3" -B "$P/check_move79_evidence.py" \
      --child-output "$_M79_OUT" --child-exit "$_m79_rc" 2>&1); _ev_rc=$?
printf '%s\n' "$_EV" | sed 's/^/  /'
if [ "$_ev_rc" -ne 0 ]; then
    echo "MOVE_79_REGRESSION_GATE: FAIL (evidence incomplete or exit $_m79_rc)"
    die "Move 79 regression evidence"
fi
MOVE_79_REGRESSION=PASS

# -------------------------------------------------------------------------
# (E) FRESH BUILD OWNED BY THIS GATE: clean target, build with the trusted
#     cargo resolved once at bootstrap, verify version, resolve ABSOLUTE
#     path, reject anything stale or foreign.
# -------------------------------------------------------------------------
echo ""
echo "STAGE E: gate-owned fresh build of witness-verify"
if ! gate_clean_target; then
    bad "could not remove rust/target"
    die "target cleanup"
fi
ok "rust/target removed; no stale executable can be reused"
BUILT=$(gate_build_once_production)
if [ $? -ne 0 ] || [ -z "$BUILT" ]; then
    bad "clean build did not produce the executable"
    die "build"
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
    bad "built binary is not an executable regular file"
    die "binary path"
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
BIN_SHA=$("$TRUSTED_SHA256SUM" "$RUST_ABS")
BIN_SHA=${BIN_SHA%% *}
ok "built binary sha256 $BIN_SHA"

# -------------------------------------------------------------------------
# (F) FOCUSED RUNNER: three fresh processes (original/reversed/shuffled);
#     empty stderr; identical canonical stdout; exact binary binding.
# -------------------------------------------------------------------------
echo ""
echo "STAGE F: focused runner, three orders, every stderr must be empty"
_HASHES=""
REQUIRED_CASES=""
NEGATIVE_DETECTION=""
for _ORDER in original reversed shuffled; do
    _OUTF=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_OUTF"
    _ERRF=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_ERRF"
    "$TRUSTED_PYTHON3" -B "$P/run_move80.py" \
        --rust-bin "$RUST_ABS" --fixtures "$GEN_A" --order "$_ORDER" \
        >"$_OUTF" 2>"$_ERRF"
    _rrc=$?
    if ! gate_measurement_stderr_clean "$_ERRF"; then
        bad "$_ORDER: runner produced stderr"
        continue
    fi
    if [ "$_rrc" -ne 0 ]; then
        bad "$_ORDER: runner exit $_rrc (expected 0)"
        tail -1 "$_OUTF" | cut -c1-400 | sed 's/^/    /'
        continue
    fi
    _SUMMARY=$("$TRUSTED_PYTHON3" -B -c "
import json,sys
try:
    with open('$_OUTF') as handle: doc = json.load(handle)
    print(doc['overall_status'], doc['required_cases'],
          doc['negative_detection'], doc['rust_bin_sha256'])
except Exception:
    print('UNPARSEABLE')")
    if [ "$_SUMMARY" = "UNPARSEABLE" ]; then
        bad "$_ORDER: runner output unparseable"
        continue
    fi
    _STATUS=${_SUMMARY%% *}; _REST=${_SUMMARY#* }
    _CASES=${_REST%% *};     _REST=${_REST#* }
    _NEG=${_REST%% *}
    _RSHA=${_REST#* }
    if [ "$_STATUS" != "PASS" ] || [ "$_CASES" != "8/8" ]; then
        bad "$_ORDER: overall $_STATUS cases $_CASES"
        continue
    fi
    if [ "$_NEG" != "PASS" ]; then
        bad "$_ORDER: negative detection $_NEG"
        continue
    fi
    if [ "$_RSHA" != "$BIN_SHA" ]; then
        bad "$_ORDER: runner executed a binary other than the gate-built one"
        continue
    fi
    _H=$("$TRUSTED_SHA256SUM" "$_OUTF"); _H=${_H%% *}
    _HASHES="$_HASHES $_ORDER:$_H"
    REQUIRED_CASES="$_CASES"
    NEGATIVE_DETECTION="$_NEG"
    ok "$_ORDER: PASS 8/8, empty stderr, exact gate-built binary"
done
if [ "$fail" -ne 0 ]; then
    die "focused runner"
fi
set -- $_HASHES
if [ "$#" -ne 3 ]; then
    bad "expected three order results, got $#"
    die "order independence"
fi
_H1=${1#*:}; _H2=${2#*:}; _H3=${3#*:}
if [ "$_H1" = "$_H2" ] && [ "$_H1" = "$_H3" ]; then
    ok "three orders byte-identical canonical output ($_H1)"
    ORDER_INDEPENDENCE=PASS
else
    bad "order outputs differ:$_HASHES"
    die "order independence"
fi

# -------------------------------------------------------------------------
# FINAL MARKERS
# -------------------------------------------------------------------------
echo ""
echo "==========================================================="
echo "MOVE_80_BASELINE_IMMUTABILITY: $BASELINE_IMMUTABILITY"
echo "MOVE_80_FIXTURE_REPRODUCIBILITY: $FIXTURE_REPRODUCIBILITY"
echo "MOVE_80_REQUIRED_CASES: $REQUIRED_CASES PASS"
echo "MOVE_80_NEGATIVE_DETECTION: $NEGATIVE_DETECTION"
echo "MOVE_80_ORDER_INDEPENDENCE: $ORDER_INDEPENDENCE"
echo "MOVE_79_REGRESSION_GATE: $MOVE_79_REGRESSION"
echo "SYSTEM_AGREEMENT_RESULT: FAIL"
echo "SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED"
echo "MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: PASS"
echo "exit_code: 0"
exit 0
