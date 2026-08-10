#!/bin/sh
# MOVE 84 TAMPER-AND-DETECT DEMO ADOPTION GATE.
#
# Move 84 produces ONE target-specific standalone witness-verify executable
# for the ACTUAL native Android/Termux AArch64 target detected during this
# run, together with a machine-readable build-provenance record. It changes
# no verifier behaviour, adds no verification capability, creates no Rust
# PASS path, and touches neither rust/ nor any frozen Python source.
#
# No prebuilt executable is packaged in the candidate. The release binary
# and its provenance record are GENERATED here and published only after
# every substantive check has passed.
#
# Linux x86_64, Linux AArch64 and Windows x86_64 remain
# NOT_CURRENTLY_ESTABLISHABLE. This gate never cross-builds and never
# describes an Android binary with Linux-target language.
#
# Required inputs (all explicit, all absolute):
#   MOVE84_CANDIDATE_ZIP     the candidate archive this tree came from
#   MOVE84_CANDIDATE_SHA256  its externally supplied expected SHA-256
#   MOVE84_OUTPUT_DIR        pre-created, empty, not a symlink, outside the
#                            extracted candidate source root
#   REAL_MOVE83              adopted Move 83 v13 zip -- the SOLE Move 84
#                            development baseline, and the complete
#                            adoption/regression child gate rerun here
#   REAL_MOVE81              adopted Move 81 v08 zip (a DEPENDENCY the
#                            Move 83 child gate requires in turn, not the
#                            Move 84 baseline)
#   REAL_MOVE80 REAL_MOVE79 REAL_MOVE78 REAL_705
#                            adopted dependencies forwarded to the child
#
# Final markers on success (exit 0):
#   MOVE_84_CANDIDATE_IDENTITY: PASS
#   MOVE_84_BASELINE_IMMUTABILITY: PASS
#   MOVE_84_TARGET_DETECTION: PASS
#   MOVE_84_CLEAN_RELEASE_BUILD: PASS
#   MOVE_84_BINARY_INSPECTION: PASS
#   MOVE_84_STANDALONE_EXECUTION: PASS
#   MOVE_84_CONTROLLED_BEHAVIOUR: PASS
#   MOVE_84_DEBUG_RELEASE_EQUIVALENCE: PASS
#   MOVE_84_PROVENANCE: PASS
#   MOVE_83_REGRESSION_GATE: PASS   (the complete adopted Move 83 v13
#                                    child gate; its retained transcript
#                                    also carries genuine inherited
#                                    MOVE_82_* markers of its own child)
#   SYSTEM_AGREEMENT_RESULT: FAIL
#   SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED
#   MOVE_84_DEMO_ADOPTION_GATE: PASS
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
_missing=""
[ -z "${MOVE84_CANDIDATE_ZIP:-}" ] && _missing="$_missing MOVE84_CANDIDATE_ZIP"
[ -z "${MOVE84_CANDIDATE_SHA256:-}" ] && _missing="$_missing MOVE84_CANDIDATE_SHA256"
[ -z "${MOVE84_OUTPUT_DIR:-}" ] && _missing="$_missing MOVE84_OUTPUT_DIR"
[ -z "${REAL_MOVE83:-}" ] && _missing="$_missing REAL_MOVE83"
[ -z "${REAL_MOVE81:-}" ] && _missing="$_missing REAL_MOVE81"
[ -z "${REAL_MOVE80:-}" ] && _missing="$_missing REAL_MOVE80"
[ -z "${REAL_MOVE79:-}" ] && _missing="$_missing REAL_MOVE79"
[ -z "${REAL_MOVE78:-}" ] && _missing="$_missing REAL_MOVE78"
[ -z "${REAL_705:-}" ] && _missing="$_missing REAL_705"
if [ -n "$_missing" ]; then
    echo "Required input(s) not supplied:$_missing"
    echo "MOVE_84_DEMO_ADOPTION_GATE: USAGE (missing:$_missing)"
    exit 2
fi

# (1c) Every supplied path must be ABSOLUTE AS SUPPLIED, before any
#      canonicalisation. Canonicalising first would let a relative path be
#      silently promoted to an absolute one and accepted.
for _pv in "MOVE84_CANDIDATE_ZIP=$MOVE84_CANDIDATE_ZIP" \
           "MOVE84_OUTPUT_DIR=$MOVE84_OUTPUT_DIR" \
           "REAL_MOVE83=$REAL_MOVE83" "REAL_MOVE81=$REAL_MOVE81" "REAL_MOVE80=$REAL_MOVE80" \
           "REAL_MOVE79=$REAL_MOVE79" "REAL_MOVE78=$REAL_MOVE78" \
           "REAL_705=$REAL_705"; do
    _pval=${_pv#*=}
    case "$_pval" in
        /*) : ;;
        *)  echo "refusing: supplied path is not absolute: $_pv"
            echo "MOVE_84_DEMO_ADOPTION_GATE: FAIL (relative path)"
            exit 1 ;;
    esac
done

# (1b) Missing-preload rejection with built-ins only (Termux host).
if [ -d /data/data/com.termux/files/usr ] && [ -z "$GATE_INHERITED_LD_PRELOAD" ]; then
    echo "the legitimate Termux exec preload (libtermux-exec.so) is absent."
    echo "MOVE_84_DEMO_ADOPTION_GATE: FAIL (missing Termux exec preload)"
    exit 1
fi

# (2) Canonicalise $0 with the LITERAL trusted readlink. No PATH lookup and
#     no external dirname/pwd may run before trust is established.
_TRUSTED_READLINK=/data/data/com.termux/files/usr/bin/readlink
if [ ! -x "$_TRUSTED_READLINK" ]; then
    echo "trusted readlink absent at $_TRUSTED_READLINK (this gate runs only on Termux)"
    echo "MOVE_84_DEMO_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
    exit 3
fi
SCRIPT_REAL=$("$_TRUSTED_READLINK" -f -- "$0") || SCRIPT_REAL=""
case "$SCRIPT_REAL" in
    */tools/check_move84_demo_adoption.sh) : ;;
    *)
        echo "refusing: canonical script path is not the genuine named gate ($SCRIPT_REAL)"
        echo "MOVE_84_DEMO_ADOPTION_GATE: FAIL (untrusted script path)"
        exit 1 ;;
esac
if [ ! -f "$SCRIPT_REAL" ]; then
    echo "refusing: canonical script target is not a regular file"
    echo "MOVE_84_DEMO_ADOPTION_GATE: FAIL (untrusted script path)"
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
die(){ echo "MOVE_84_DEMO_ADOPTION_GATE: FAIL ($1)"; exit 1; }

gate_require_clean_stderr(){
    _grcs_file=$1; _grcs_label=$2
    if [ -s "$_grcs_file" ]; then
        echo "  $_grcs_label stderr (must be empty):"
        sed 's/^/    /' "$_grcs_file"
        bad "$_grcs_label emitted stderr"
        return 1
    fi
    return 0
}

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

# (4) Bootstrap protocol, exactly as adopted.
echo ""
echo "BOOTSTRAP: establishing the trusted execution environment"
gate_bootstrap "$GATE_INHERITED_LD_PRELOAD"
BOOT_RC=$?
if [ "$BOOT_RC" -eq 3 ]; then
    echo "  trusted Termux toolchain is not present on this host."
    echo "MOVE_84_DEMO_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
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

echo ""
echo "NESTED EXEC: verifying trusted nested process execution"
if gate_nested_exec_probe; then
    echo "TERMUX_NESTED_EXEC_CHECK: PASS"
else
    echo "TERMUX_NESTED_EXEC_CHECK: FAIL"
    echo "MOVE_84_DEMO_ADOPTION_GATE: FAIL (nested exec)"
    exit 1
fi

P="$ROOT/verify/demo_v01"
# The focused-result validator, the report schema and the Rust source
# sanity checker are ADOPTED Move 83 files, inherited byte-identical.
# They are reused at their real adopted paths; copying them here would
# duplicate reviewed code and let the copies drift.
PR="$ROOT/verify/report_v01"
# ONE active transcript identity, defined once and referenced everywhere,
# so the provenance record can never name a superseded candidate. Move 84
# v02 shipped provenance naming MOVE_84_V01_TERMUX_GATE.txt because this
# value was carried forward unchanged when the candidate was rebuilt.
MOVE84_TRANSCRIPT_NAME="MOVE_84_V07_TERMUX_GATE.txt"
# The build, inspection, provenance and equivalence helpers are ADOPTED
# Move 83 files, inherited byte-identical in this candidate. They are
# reused at their real adopted paths: copying them into demo_v01/ would
# duplicate reviewed code and invite the two copies to drift.
PB="$ROOT/verify/portable_build_v01"
TRUSTED_PY=$("$TRUSTED_READLINK" -f -- "$TRUSTED_PYTHON3") || TRUSTED_PY=""

# =========================================================================
# PRE-FLIGHT: every local production helper this gate invokes must already
# exist in the reviewed candidate. A helper is never created during the
# run. Each is required to be a regular file (never a symlink) inside the
# verified candidate tree.
# =========================================================================
_require_helper() {
    _rh_path=$1
    case "$_rh_path" in
        "$ROOT"/*) : ;;
        *) bad "helper is outside the verified candidate tree: $_rh_path"
           die "helper outside tree" ;;
    esac
    if [ -L "$_rh_path" ]; then
        bad "helper is a symlink: $_rh_path"; die "helper symlink"
    fi
    if [ ! -f "$_rh_path" ]; then
        bad "required production helper is missing from the candidate: $_rh_path"
        die "helper missing"
    fi
}
for _h in \
    "$PR/rust_source_check.py" \
    "$PR/check_focused_result.py" \
    "$P/demo_tests.py" \
    "$P/check_move84_inherited.py" \
    "$P/allowlist_move84.json" \
    "$P/EXPECTED_TEST_COUNT.txt" \
    "$PB/build_binary.py" \
    "$PB/inspect_binary.py" \
    "$PB/provenance.py" \
    "$PB/equivalence.py" \
    "$ROOT/tools/read_version.py" \
    "$ROOT/tools/check_package_hygiene.sh" \
    "$ROOT/verify/corrupted_bundle_pack_v01/generate_fixtures.py" \
    "$ROOT/verify/corrupted_bundle_pack_v01/integrity_check.py" \
    "$ROOT/verify/corrupted_bundle_pack_v01/expected_results.json" \
    "$ROOT/verify/corrupted_bundle_pack_v01/fixture_manifest.json" \
    "$ROOT/verify/agreement_harness_v01/reason_map.json" \
    "$ROOT/verify/structured_verdict_v01/adapter.py" \
; do
    _require_helper "$_h"
done
ok "every production helper this gate invokes is present in the candidate"

# Cheap syntax sanity on the Rust sources BEFORE the long build. This is
# NOT a compiler and does not establish buildability -- cargo build and
# cargo test below do that. It exists because a prior candidate shipped a
# string constant that terminated early, leaving English prose outside any
# literal, and every Python check passed.
_RSC_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RSC_OUT"
_RSC_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RSC_ERR"
"$TRUSTED_PYTHON3" -B "$PR/rust_source_check.py" \
    --source "$ROOT/rust/witness-verify/src/report.rs" \
    --source "$ROOT/rust/witness-verify/src/main.rs" \
    >"$_RSC_OUT" 2>"$_RSC_ERR"
_rsc_rc=$?
cat "$_RSC_OUT"
if [ -s "$_RSC_ERR" ]; then
    sed 's/^/    /' "$_RSC_ERR"
    bad "Rust source sanity check emitted stderr"
    die "rust source sanity stderr"
fi
if [ "$_rsc_rc" -ne 0 ]; then
    bad "Rust source sanity check failed"; die "rust source sanity"
fi
ok "Rust sources pass the syntax sanity check (buildability is established by cargo below)"
case "$TRUSTED_PY" in /*) : ;; *) die "trusted python path" ;; esac

# =========================================================================
# STAGE A -- candidate identity. The candidate may NOT declare its own hash.
# =========================================================================
echo ""
echo "STAGE A: candidate identity (externally supplied hash)"
CAND_ZIP=$("$TRUSTED_READLINK" -f -- "$MOVE84_CANDIDATE_ZIP") || CAND_ZIP=""
case "$CAND_ZIP" in /*) : ;; *) die "MOVE84_CANDIDATE_ZIP path" ;; esac
[ -f "$CAND_ZIP" ] || die "MOVE84_CANDIDATE_ZIP is not a regular file"
_CAND_SHA=$("$TRUSTED_SHA256SUM" "$CAND_ZIP"); _CAND_SHA=${_CAND_SHA%% *}
if [ "$_CAND_SHA" != "$MOVE84_CANDIDATE_SHA256" ]; then
    bad "candidate sha256 $_CAND_SHA != supplied $MOVE84_CANDIDATE_SHA256"
    echo "MOVE_84_CANDIDATE_IDENTITY: FAIL"
    die "candidate identity"
fi
echo "MOVE84_CANDIDATE_ZIP verified by trusted sha256sum:"
echo "$_CAND_SHA"
ok "candidate identity verified against the externally supplied hash"

# The live tree must be byte-identical to the verified archive in BOTH
# directions. Hash-verifying the archive while path-checking the tree
# would let a modified allowlisted file through, binding the generated
# binary to reviewed NAMES rather than reviewed BYTES.
_SB_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_SB_OUT"
_SB_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_SB_ERR"
"$TRUSTED_PYTHON3" -B "$P/check_move84_inherited.py" \
    --baseline-zip "$CAND_ZIP" --verify-tree-matches-zip "$ROOT" \
    >"$_SB_OUT" 2>"$_SB_ERR"
_sb_rc=$?
cat "$_SB_OUT"
if [ -s "$_SB_ERR" ]; then
    sed 's/^/    /' "$_SB_ERR"
    bad "source-binding checker emitted stderr"; die "source binding"
fi
if [ "$_sb_rc" -ne 0 ]; then
    bad "live tree is not byte-identical to the verified candidate archive"
    echo "MOVE_84_CANDIDATE_IDENTITY: FAIL"; die "source binding"
fi
ok "live tree bound byte-for-byte to the verified candidate archive"
CANDIDATE_IDENTITY=PASS

# Output-directory contract.
OUT_DIR=$("$TRUSTED_READLINK" -f -- "$MOVE84_OUTPUT_DIR") || OUT_DIR=""
case "$OUT_DIR" in /*) : ;; *) die "MOVE84_OUTPUT_DIR path" ;; esac
RUN_DIR=${CAND_ZIP%/*}
# The output-directory rules live in a factored production helper so they
# are executable and directly testable, rather than asserted by reading
# this script's source.
_OD_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_OD_OUT"
_OD_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_OD_ERR"
"$TRUSTED_PYTHON3" -B "$P/check_move84_inherited.py" \
    --check-output-dir "$MOVE84_OUTPUT_DIR" --run-dir "$RUN_DIR" \
    --candidate-root "$ROOT" >"$_OD_OUT" 2>"$_OD_ERR"
_od_rc=$?
cat "$_OD_OUT"
if [ -s "$_OD_ERR" ]; then
    sed 's/^/    /' "$_OD_ERR"; bad "output-dir checker emitted stderr"
    die "output dir"
fi
if [ "$_od_rc" -ne 0 ]; then
    bad "MOVE84_OUTPUT_DIR does not satisfy the output-directory contract"
    die "output dir"
fi
ok "output directory is absolute, empty, not a symlink, outside the source root"

# Private staging area. Nothing is published until every check passes.
STAGE_DIR=$("$TRUSTED_MKTEMP" -d) || die "could not create staging dir"
gate_track_tmp "$STAGE_DIR"
ok "private staging directory established"

# =========================================================================
# STAGE B -- baseline immutability against the real adopted Move 83 v13.
# =========================================================================
echo ""
echo "STAGE B: baseline immutability (candidate vs real adopted Move 83 v13 zip)"
M83_ZIP=$("$TRUSTED_READLINK" -f -- "$REAL_MOVE83") || M83_ZIP=""
case "$M83_ZIP" in /*) : ;; *) die "REAL_MOVE83 path" ;; esac
[ -f "$M83_ZIP" ] || die "REAL_MOVE83 is not a regular file"
_M83_SHA=$("$TRUSTED_SHA256SUM" "$M83_ZIP"); _M83_SHA=${_M83_SHA%% *}
_M83_EXPECT=aa06feb870ec3d72ff7c942fe8c0752efff313cbbdab6e280302dba288975a6c
if [ "$_M83_SHA" != "$_M83_EXPECT" ]; then
    bad "supplied Move 83 v13 zip sha256 $_M83_SHA != adopted $_M83_EXPECT"
    echo "MOVE_84_BASELINE_IMMUTABILITY: FAIL"; die "baseline zip hash"
fi
echo "REAL_MOVE83 verified by trusted sha256sum:"
echo "$_M83_EXPECT"
_B_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_B_OUT"
_B_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_B_ERR"
"$TRUSTED_PYTHON3" -B "$P/check_move84_inherited.py" \
    --baseline-zip "$M83_ZIP" --root "$ROOT" \
    --expect-sha256 "$_M83_EXPECT" \
    --allowlist "$P/allowlist_move84.json" >"$_B_OUT" 2>"$_B_ERR"
_b_rc=$?
echo "---- BEGIN BASELINE SAFETY + INHERITED-DIFF EVIDENCE ----"
cat "$_B_OUT"
echo "---- END BASELINE SAFETY + INHERITED-DIFF EVIDENCE ----"
if [ -s "$_B_ERR" ]; then
    sed 's/^/    /' "$_B_ERR"
    bad "baseline checker emitted stderr"
    echo "MOVE_84_BASELINE_IMMUTABILITY: FAIL"; die "baseline stderr"
fi
if [ "$_b_rc" -ne 0 ]; then
    bad "candidate does not match the adopted Move 83 v13 baseline + allowlist"
    echo "MOVE_84_BASELINE_IMMUTABILITY: FAIL"; die "baseline immutability"
fi
ok "every inherited file byte-identical; additions match the Move 84 allowlist"
BASELINE_IMMUTABILITY=PASS

# =========================================================================
# STAGE C -- target detection. Detected, never assumed.
# =========================================================================
echo ""
echo "STAGE C: target detection"
TRUSTED_RUSTC=$("$TRUSTED_READLINK" -f -- \
    "$TRUSTED_TERMUX_PREFIX/bin/rustc") || TRUSTED_RUSTC=""
case "$TRUSTED_RUSTC" in /*) : ;; *) die "trusted rustc path" ;; esac
[ -x "$TRUSTED_RUSTC" ] || die "trusted rustc is not executable"
# rustc is not parsed through an unchecked pipeline: its status and stderr
# are captured and checked independently before the host line is read.
_RV_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RV_OUT"
_RV_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RV_ERR"
"$TRUSTED_RUSTC" -vV >"$_RV_OUT" 2>"$_RV_ERR"
_rv_rc=$?
if [ -s "$_RV_ERR" ]; then
    sed 's/^/    /' "$_RV_ERR"
    bad "rustc emitted stderr during target detection"
    die "target detection stderr"
fi
[ "$_rv_rc" -eq 0 ] || die "rustc -vV failed"
_RUSTC_HOST=$(sed -n 's/^host: //p' "$_RV_OUT")
[ -n "$_RUSTC_HOST" ] || die "rustc did not report a host triple"
_UN_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_UN_OUT"
_UN_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_UN_ERR"
uname -m >"$_UN_OUT" 2>"$_UN_ERR"
if [ -s "$_UN_ERR" ]; then
    sed 's/^/    /' "$_UN_ERR"
    bad "uname emitted stderr during platform detection"
    die "platform detection stderr"
fi
_PLATFORM_MACHINE=$(cat "$_UN_OUT")
[ -n "$_PLATFORM_MACHINE" ] || die "could not detect platform machine"
echo "  detected rustc host triple : $_RUSTC_HOST"
echo "  detected platform machine  : $_PLATFORM_MACHINE"
case "$_RUSTC_HOST" in
    *-linux-android) : ;;
    *)  bad "detected host triple is not an Android target: $_RUSTC_HOST"
        echo "MOVE_84_TARGET_DETECTION: FAIL"
        die "target detection" ;;
esac
ok "native Android/Termux target detected"
TARGET_DETECTION=PASS

# =========================================================================
# STAGE D -- clean release build (and a debug build for equivalence only).
# =========================================================================
echo ""
echo "STAGE D: clean release build"
if ! gate_clean_target; then
    bad "could not remove rust/target"; die "target cleanup"
fi
ok "rust/target removed; no stale artefact can be reused"
_BLD_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_BLD_OUT"
_BLD_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_BLD_ERR"
"$TRUSTED_PYTHON3" -B "$PB/build_binary.py" \
    --cargo "$TRUSTED_CARGO" --rustc "$TRUSTED_RUSTC" \
    --manifest-dir "$ROOT/rust" --profile release \
    --require-clean-target >"$_BLD_OUT" 2>"$_BLD_ERR"
if [ $? -ne 0 ] || [ -s "$_BLD_ERR" ]; then
    cat "$_BLD_OUT"; sed 's/^/    /' "$_BLD_ERR"
    bad "release build failed"; echo "MOVE_84_CLEAN_RELEASE_BUILD: FAIL"
    die "release build"
fi
cat "$_BLD_OUT"
RELEASE_BIN="$ROOT/rust/target/release/witness-verify"
[ -x "$RELEASE_BIN" ] || die "release binary missing"
ok "fresh release binary built from a clean tree"

# Debug build, used ONLY for behavioural equivalence. Never preserved and
# never advertised as the portable artefact.
_DBG_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_DBG_OUT"
_DBG_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_DBG_ERR"
"$TRUSTED_PYTHON3" -B "$PB/build_binary.py" \
    --cargo "$TRUSTED_CARGO" --rustc "$TRUSTED_RUSTC" \
    --manifest-dir "$ROOT/rust" --profile dev >"$_DBG_OUT" 2>"$_DBG_ERR"
_dbg_rc=$?
cat "$_DBG_OUT"
if [ -s "$_DBG_ERR" ]; then
    sed 's/^/    /' "$_DBG_ERR"
    bad "debug build emitted stderr"; die "debug build stderr"
fi
if [ "$_dbg_rc" -ne 0 ]; then
    bad "debug build failed"; die "debug build"
fi
DEBUG_BIN="$ROOT/rust/target/debug/witness-verify"
[ -x "$DEBUG_BIN" ] || die "debug binary missing"
ok "fresh debug binary built for equivalence testing only"

# BASELINE BYTE AUTHORITY. Correctness must not rest on two newly built
# candidate binaries agreeing, so the adopted Move 83 v13 verifier is
# freshly built from a private extracted copy of the adopted archive and
# its exact stdout/stderr/exit becomes the authority every candidate
# profile must match.
_BASE_EXTRACT=$("$TRUSTED_MKTEMP" -d) || die "could not create baseline dir"
gate_track_tmp "$_BASE_EXTRACT"
_BX_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_BX_OUT"
_BX_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_BX_ERR"
"$TRUSTED_PYTHON3" -B "$P/check_move84_inherited.py" \
    --baseline-zip "$M83_ZIP" --expect-sha256 "$_M83_EXPECT" \
    --extract-to "$_BASE_EXTRACT" >"$_BX_OUT" 2>"$_BX_ERR"
if [ $? -ne 0 ] || [ -s "$_BX_ERR" ]; then
    cat "$_BX_OUT"; sed 's/^/    /' "$_BX_ERR"
    bad "could not extract the adopted baseline for the byte authority"
    die "baseline authority"
fi
_BASE_ROOT="$_BASE_EXTRACT/project-witness-main"
[ -d "$_BASE_ROOT/rust" ] || die "extracted baseline has no rust workspace"
_BA_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_BA_OUT"
_BA_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_BA_ERR"
"$TRUSTED_PYTHON3" -B "$PB/build_binary.py" \
    --cargo "$TRUSTED_CARGO" --rustc "$TRUSTED_RUSTC" \
    --manifest-dir "$_BASE_ROOT/rust" --profile dev \
    --require-clean-target >"$_BA_OUT" 2>"$_BA_ERR"
if [ $? -ne 0 ] || [ -s "$_BA_ERR" ]; then
    cat "$_BA_OUT"; sed 's/^/    /' "$_BA_ERR"
    bad "adopted baseline verifier build failed or emitted stderr"
    die "baseline authority"
fi
BASELINE_BIN="$_BASE_ROOT/rust/target/debug/witness-verify"
[ -x "$BASELINE_BIN" ] || die "baseline verifier missing"
ok "adopted Move 83 v13 baseline verifier freshly built as the byte authority"

_EXPECT_VERSION="0.0.8-step79-diagnostics"
_VER_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_VER_OUT"
_VER_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_VER_ERR"
"$RELEASE_BIN" verify /nonexistent >"$_VER_OUT" 2>"$_VER_ERR"
if [ -s "$_VER_ERR" ]; then
    sed 's/^/    /' "$_VER_ERR"
    bad "release binary emitted stderr during version probing"
    die "version probe stderr"
fi
_REPORTED=$("$TRUSTED_PYTHON3" -B tools/read_version.py <"$_VER_OUT")
if [ "$_REPORTED" != "$_EXPECT_VERSION" ]; then
    bad "release binary reports version '$_REPORTED', expected '$_EXPECT_VERSION'"
    die "binary version"
fi
ok "release binary reports $_EXPECT_VERSION"

# The Rust unit suite is executed, not inferred from a Python source-shape
# test. stdout, stderr and exit status are preserved separately.
_CT_TOUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_CT_TOUT"
_CT_TERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_CT_TERR"
( cd "$ROOT/rust" && "$TRUSTED_CARGO" test -q ) \
    >"$_CT_TOUT" 2>"$_CT_TERR"; _ct_trc=$?
echo "---- BEGIN CARGO TEST STDOUT ----"
cat "$_CT_TOUT"
echo "---- END CARGO TEST STDOUT ----"
echo "---- BEGIN CARGO TEST STDERR ----"
cat "$_CT_TERR"
echo "---- END CARGO TEST STDERR ----"
if [ "$_ct_trc" -ne 0 ]; then
    bad "cargo test failed (exit $_ct_trc)"; die "cargo test"
fi
if grep -qE "^(error|warning)" "$_CT_TERR"; then
    bad "cargo test stderr contains an error or warning"
    die "cargo test stderr"
fi
if grep -q "FAILED" "$_CT_TOUT"; then
    bad "cargo test reported a failure"; die "cargo test"
fi
if ! grep -q "test result: ok" "$_CT_TOUT"; then
    bad "cargo test did not report a successful result line"
    die "cargo test accounting"
fi
if grep -qE "test result: ok\. 0 passed" "$_CT_TOUT"; then
    bad "cargo test ran no tests"; die "cargo test accounting"
fi
ok "Rust unit suite executed and passed after the clean build"
CLEAN_RELEASE_BUILD=PASS

# =========================================================================
# STAGE E -- binary inspection from the binary's own headers.
# =========================================================================
echo ""
echo "STAGE E: binary inspection (parsed from the executable itself)"
_INS_JSON="$STAGE_DIR/inspect.json"
_INS_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_INS_OUT"
_INS_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_INS_ERR"
"$TRUSTED_PYTHON3" -B "$PB/inspect_binary.py" --binary "$RELEASE_BIN" \
    --json-out "$_INS_JSON" \
    --rustc-host "$_RUSTC_HOST" --platform-machine "$_PLATFORM_MACHINE" \
    >"$_INS_OUT" 2>"$_INS_ERR"
_ins_rc=$?
cat "$_INS_OUT"
if [ -s "$_INS_ERR" ]; then
    sed 's/^/    /' "$_INS_ERR"; bad "inspector emitted stderr"
    die "binary inspection"
fi
if [ "$_ins_rc" -ne 0 ]; then
    bad "binary inspection failed or disagreed with the detected target"
    echo "MOVE_84_BINARY_INSPECTION: FAIL"; die "binary inspection"
fi
echo "---- BEGIN BINARY INSPECTION RECORD ----"
cat "$_INS_JSON"
echo "---- END BINARY INSPECTION RECORD ----"
ok "ELF class, endianness, type, architecture, interpreter and DT_NEEDED established"
BINARY_INSPECTION=PASS

# =========================================================================
# STAGE F -- standalone execution outside the source tree, empty PATH.
# =========================================================================
echo ""
echo "STAGE F: standalone execution"
BUNDLE="$ROOT/freeze_record/python_behaviour_freeze_v01/reference_bundle"
[ -d "$BUNDLE" ] || die "clean reference bundle missing"
_STD_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_STD_OUT"
_STD_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_STD_ERR"
"$TRUSTED_PYTHON3" -B "$PB/equivalence.py" --mode standalone \
    --release-bin "$RELEASE_BIN" --workdir "$STAGE_DIR/standalone" \
    --input "$BUNDLE" \
    --expect-verdict INCONCLUSIVE \
    --expect-reason-code RECEIPT_CHAIN_HASHES_RECOMPUTED \
    --expect-exit-code 3 >"$_STD_OUT" 2>"$_STD_ERR"
_std_rc=$?
cat "$_STD_OUT"
if [ -s "$_STD_ERR" ]; then
    sed 's/^/    /' "$_STD_ERR"; bad "standalone harness emitted stderr"
    die "standalone"
fi
if [ "$_std_rc" -ne 0 ]; then
    bad "standalone execution did not meet the adopted expectation"
    echo "MOVE_84_STANDALONE_EXECUTION: FAIL"; die "standalone"
fi
ok "release binary met the adopted clean-bundle expectation outside the source tree with an empty PATH"
STANDALONE_EXECUTION=PASS

# =========================================================================
# STAGE G -- controlled behaviour + debug/release equivalence.
# =========================================================================
echo ""
echo "STAGE G: controlled behaviour and debug/release equivalence"
_FIX_DIR="$STAGE_DIR/fixtures"
_FIX_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_FIX_OUT"
_FIX_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_FIX_ERR"
"$TRUSTED_PYTHON3" -B verify/corrupted_bundle_pack_v01/generate_fixtures.py \
    --out "$_FIX_DIR" >"$_FIX_OUT" 2>"$_FIX_ERR"
if [ $? -ne 0 ]; then
    cat "$_FIX_OUT"; sed 's/^/    /' "$_FIX_ERR"
    die "could not generate the adopted Move 80 fixtures"
fi
if [ -s "$_FIX_ERR" ]; then
    sed 's/^/    /' "$_FIX_ERR"
    bad "fixture generation emitted stderr"; die "fixture generation stderr"
fi
ok "adopted Move 80 fixtures generated into the private staging area"

# B9: run the ADOPTED Move 80 integrity checks against THIS exact fixture
# output directory, before either binary executes. The later child gate
# validates a DIFFERENT fixture generation, so relying on it alone would
# leave this generation unverified.
_FI_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_FI_OUT"
_FI_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_FI_ERR"
# The adopted checker compares two INDEPENDENT generations, so a second
# set is generated here; that also proves deterministic regeneration.
_FIX_DIR_B="$STAGE_DIR/fixtures_b"
_FGB_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_FGB_ERR"
_FGB_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_FGB_OUT"
"$TRUSTED_PYTHON3" -B verify/corrupted_bundle_pack_v01/generate_fixtures.py \
    --out "$_FIX_DIR_B" >"$_FGB_OUT" 2>"$_FGB_ERR"
_fgb_rc=$?
if [ -s "$_FGB_ERR" ]; then
    sed 's/^/    /' "$_FGB_ERR"
    bad "second Move 80 fixture generation emitted stderr"
    die "fixture generation stderr"
fi
if [ "$_fgb_rc" -ne 0 ]; then
    cat "$_FGB_OUT"
    bad "second Move 80 fixture generation failed (exit $_fgb_rc)"
    die "fixture generation"
fi
"$TRUSTED_PYTHON3" -B -W error::ResourceWarning \
    verify/corrupted_bundle_pack_v01/integrity_check.py \
    --gen-a "$_FIX_DIR" --gen-b "$_FIX_DIR_B" >"$_FI_OUT" 2>"$_FI_ERR"
_fi_rc=$?
echo "---- BEGIN MOVE 80 FIXTURE INTEGRITY EVIDENCE ----"
cat "$_FI_OUT"
echo "---- END MOVE 80 FIXTURE INTEGRITY EVIDENCE ----"
if [ -s "$_FI_ERR" ]; then
    sed 's/^/    /' "$_FI_ERR"
    bad "Move 80 fixture integrity check emitted stderr"
    die "fixture integrity"
fi
if [ "$_fi_rc" -ne 0 ]; then
    bad "the generated Move 80 fixtures did not match their adopted hashes"
    die "fixture integrity"
fi
ok "this exact Move 80 fixture generation matches the adopted hashes and expectations"

_EDGE_DIR="$STAGE_DIR/edge"
_EDGE_MANIFEST="$STAGE_DIR/edge_manifest.json"
_EDG_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_EDG_OUT"
_EDG_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_EDG_ERR"
"$TRUSTED_PYTHON3" -B "$PB/equivalence.py" --mode make-edge-fixtures \
    --outdir "$_EDGE_DIR" --clean-bundle "$BUNDLE" \
    --json-out "$_EDGE_MANIFEST" >"$_EDG_OUT" 2>"$_EDG_ERR"
if [ $? -ne 0 ] || [ -s "$_EDG_ERR" ]; then
    cat "$_EDG_OUT"; sed 's/^/    /' "$_EDG_ERR"
    bad "hostile edge-fixture generation failed or emitted stderr"
    die "edge fixtures"
fi
cat "$_EDG_OUT"
ok "hostile numeric/length edge fixtures built from a real frozen bundle"

# real_v20 is the INHERITED adopted archive in the candidate tree. Move 79
# is a different artifact and must never be substituted for it.
_REAL_V20="$ROOT/releases/roadmap_one_complete/move_70_final/Project_Witness_WORKING_STACK_v20_MOVE_70.zip"
if [ ! -f "$_REAL_V20" ]; then
    bad "the inherited v20 archive is missing"; die "real_v20"
fi
_ARCH_DIR="$STAGE_DIR/archives"
_HARNESS="$ROOT/verify/agreement_harness_v01"
_RMAP="$_HARNESS/reason_map.json"
_EQ_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_EQ_OUT"
_EQ_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_EQ_ERR"
# The COMPLETE adopted corpus: the clean frozen bundle, all eight Move 80
# fixtures and all 70 adopted archive cases (67 built by the adopted
# builder after its corpus pins are verified, plus the three real supplied
# artifacts). Every case runs through candidate release, candidate debug,
# the adopted baseline authority, and the staged standalone binary.
"$TRUSTED_PYTHON3" -B "$PB/equivalence.py" --mode full-corpus \
    --release-bin "$RELEASE_BIN" --debug-bin "$DEBUG_BIN" \
    --baseline-bin "$BASELINE_BIN" \
    --expected-results "$ROOT/verify/corrupted_bundle_pack_v01/expected_results.json" \
    --fixture-manifest "$ROOT/verify/corrupted_bundle_pack_v01/fixture_manifest.json" \
    --fixtures-dir "$_FIX_DIR" --clean-bundle "$BUNDLE" \
    --harness-dir "$_HARNESS" --archives-dir "$_ARCH_DIR" \
    --reason-map "$_RMAP" \
    --real-705 "$REAL_705" --real-move78 "$REAL_MOVE78" \
    --real-v20 "$_REAL_V20" \
    --standalone-dir "$STAGE_DIR/standalone_corpus" \
    >"$_EQ_OUT" 2>"$_EQ_ERR"
_eq_rc=$?
echo "---- BEGIN COMPLETE CORPUS EVIDENCE ----"
cat "$_EQ_OUT"
echo "---- END COMPLETE CORPUS EVIDENCE ----"
if [ -s "$_EQ_ERR" ]; then
    sed 's/^/    /' "$_EQ_ERR"; bad "corpus harness emitted stderr"
    die "controlled behaviour"
fi
if [ "$_eq_rc" -ne 0 ]; then
    bad "the complete corpus did not match the adopted expectations, the baseline authority, or across profiles"
    echo "MOVE_84_CONTROLLED_BEHAVIOUR: FAIL"
    die "controlled behaviour"
fi
ok "every adopted case matched its expectation, the baseline authority, both profiles and the staged standalone binary"

# Move 81 adapter equivalence across every applicable case.
_AD_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_AD_OUT"
_AD_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_AD_ERR"
"$TRUSTED_PYTHON3" -B "$PB/equivalence.py" --mode adapter-equivalence \
    --release-bin "$RELEASE_BIN" --debug-bin "$DEBUG_BIN" \
    --adapter "$ROOT/verify/structured_verdict_v01/adapter.py" \
    --baseline-bin "$BASELINE_BIN" \
    --python-bin "$TRUSTED_PY" --reason-map "$_RMAP" \
    --expected-results "$ROOT/verify/corrupted_bundle_pack_v01/expected_results.json" \
    --fixture-manifest "$ROOT/verify/corrupted_bundle_pack_v01/fixture_manifest.json" \
    --fixtures-dir "$_FIX_DIR" --clean-bundle "$BUNDLE" \
    --harness-dir "$_HARNESS" --archives-dir "$_ARCH_DIR" \
    --real-705 "$REAL_705" --real-move78 "$REAL_MOVE78" \
    --real-v20 "$_REAL_V20" \
    >"$_AD_OUT" 2>"$_AD_ERR"
_ad_rc=$?
echo "---- BEGIN MOVE 81 ADAPTER EQUIVALENCE EVIDENCE ----"
cat "$_AD_OUT"
echo "---- END MOVE 81 ADAPTER EQUIVALENCE EVIDENCE ----"
if [ -s "$_AD_ERR" ]; then
    sed 's/^/    /' "$_AD_ERR"; bad "adapter harness emitted stderr"
    die "adapter equivalence"
fi
if [ "$_ad_rc" -ne 0 ]; then
    bad "Move 81 adapter records were not byte-identical across profiles"
    echo "MOVE_84_DEBUG_RELEASE_EQUIVALENCE: FAIL"
    die "adapter equivalence"
fi
ok "both profiles produced byte-identical canonical structured records; no Rust PASS"

# Hostile edge fixtures: exact declared stage per fixture.
_EDQ_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_EDQ_OUT"
_EDQ_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_EDQ_ERR"
"$TRUSTED_PYTHON3" -B "$PB/equivalence.py" --mode edge-equivalence \
    --release-bin "$RELEASE_BIN" --debug-bin "$DEBUG_BIN" \
    --baseline-bin "$BASELINE_BIN" --reason-map "$_RMAP" \
    --edge-manifest "$_EDGE_MANIFEST" \
    --json-out "$STAGE_DIR/edge_pinned.json" \
    >"$_EDQ_OUT" 2>"$_EDQ_ERR"
_edq_rc=$?
cat "$_EDQ_OUT"
if [ -s "$_EDQ_ERR" ]; then
    sed 's/^/    /' "$_EDQ_ERR"; bad "edge harness emitted stderr"
    die "edge equivalence"
fi
if [ "$_edq_rc" -ne 0 ]; then
    bad "hostile edge fixtures diverged or were answered at the wrong stage"
    echo "MOVE_84_DEBUG_RELEASE_EQUIVALENCE: FAIL"
    die "edge equivalence"
fi
ok "every hostile edge fixture was answered at its declared stage and both profiles agreed"

# Adopted USAGE contract, executed rather than assumed.
_US_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_US_OUT"
_US_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_US_ERR"
"$TRUSTED_PYTHON3" -B "$PB/equivalence.py" --mode usage-contract \
    --release-bin "$RELEASE_BIN" --debug-bin "$DEBUG_BIN" \
    --baseline-bin "$BASELINE_BIN" \
    --standalone-dir "$STAGE_DIR/standalone_usage" \
    >"$_US_OUT" 2>"$_US_ERR"
_us_rc=$?
cat "$_US_OUT"
if [ -s "$_US_ERR" ]; then
    sed 's/^/    /' "$_US_ERR"; bad "usage harness emitted stderr"
    die "usage contract"
fi
if [ "$_us_rc" -ne 0 ]; then
    bad "usage behaviour differs across profiles or from the adopted baseline"
    echo "MOVE_84_CONTROLLED_BEHAVIOUR: FAIL"
    die "usage contract"
fi
ok "adopted usage behaviour reproduced by both profiles, the baseline authority and the staged standalone binary"

# =========================================================================
# MOVE 84 DEMONSTRATION STAGES. Exercised on the freshly
# built release binary, every report is validated, and every report is
# cross-checked against the ADOPTED legacy verdict line for the same input
# so a report can never contradict the evaluation it claims to describe.
# =========================================================================
echo ""
echo "STAGE D: tamper-and-detect demonstration"
_DEMO_DIR="$STAGE_DIR/demo"
mkdir -p "$_DEMO_DIR" || die "could not create demo staging dir"
_FX_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_FX_OUT"
_FX_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_FX_ERR"
"$TRUSTED_PYTHON3" -B "$P/build_demo_fixtures.py" \
    --source "$ROOT/freeze_record/python_behaviour_freeze_v01/reference_bundle" \
    --outdir "$_DEMO_DIR/fixtures" \
    --manifest-out "$_DEMO_DIR/fixtures.json" \
    >"$_FX_OUT" 2>"$_FX_ERR"
_fx_rc=$?
cat "$_FX_OUT"
if [ -s "$_FX_ERR" ]; then
    sed 's/^/    /' "$_FX_ERR"; bad "demo fixture construction emitted stderr"
    die "demo fixtures stderr"
fi
[ "$_fx_rc" -eq 0 ] || { bad "demo fixture construction failed"; die "demo fixtures"; }
ok "demo fixtures built deterministically from the frozen reference bundle"

# AUTHORITY. The expectations for every demonstrated Rust behaviour are
# established by executing the verifier built from the privately
# extracted, hash-verified ADOPTED Move 83 v13 artifact -- never declared
# by the candidate.
AUTHORITY_BIN="$BASELINE_BIN"
[ -x "$AUTHORITY_BIN" ] || die "adopted authority verifier missing"
_AU_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_AU_OUT"
_AU_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_AU_ERR"
"$TRUSTED_PYTHON3" -B "$P/demo.py" --mode establish \
    --verifier "$AUTHORITY_BIN" --python-bin "$TRUSTED_PY" \
    --companion "$ROOT/src/12_companion_cli_v031/companion.py" \
    --fixtures "$_DEMO_DIR/fixtures.json" \
    --expectations-out "$_DEMO_DIR/expectations.json" \
    >"$_AU_OUT" 2>"$_AU_ERR"
_au_rc=$?
cat "$_AU_OUT"
if [ -s "$_AU_ERR" ]; then
    sed 's/^/    /' "$_AU_ERR"; bad "demo authority emitted stderr"
    die "demo authority stderr"
fi
[ "$_au_rc" -eq 0 ] || { bad "the adopted authority did not satisfy the demonstration invariants"; die "demo authority"; }
ok "demonstration expectations established from the ADOPTED Move 83 v13 verifier"

_DM_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_DM_OUT"
_DM_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_DM_ERR"
"$TRUSTED_PYTHON3" -B "$P/demo.py" --mode demonstrate \
    --verifier "$RELEASE_BIN" --python-bin "$TRUSTED_PY" \
    --companion "$ROOT/src/12_companion_cli_v031/companion.py" \
    --fixtures "$_DEMO_DIR/fixtures.json" \
    --expectations "$_DEMO_DIR/expectations.json" \
    --transcript-out "$_DEMO_DIR/transcript_1.txt" \
    >"$_DM_OUT" 2>"$_DM_ERR"
_dm_rc=$?
echo "---- BEGIN DEMONSTRATION TRANSCRIPT ----"
cat "$_DEMO_DIR/transcript_1.txt"
echo "---- END DEMONSTRATION TRANSCRIPT ----"
if [ -s "$_DM_ERR" ]; then
    sed 's/^/    /' "$_DM_ERR"; bad "demonstration emitted stderr"
    die "demo stderr"
fi
if [ "$_dm_rc" -ne 0 ]; then
    cat "$_DM_OUT"; bad "the demonstration did not reproduce the adopted authority"
    echo "MOVE_84_DEMO_OUTPUT: FAIL"; die "demo"
fi
ok "every demonstrated observation reproduced the adopted authority exactly"

# Determinism: a second run over unchanged inputs must be byte-identical.
"$TRUSTED_PYTHON3" -B "$P/demo.py" --mode demonstrate \
    --verifier "$RELEASE_BIN" --python-bin "$TRUSTED_PY" \
    --companion "$ROOT/src/12_companion_cli_v031/companion.py" \
    --fixtures "$_DEMO_DIR/fixtures.json" \
    --expectations "$_DEMO_DIR/expectations.json" \
    --transcript-out "$_DEMO_DIR/transcript_2.txt" \
    >/dev/null 2>"$_DM_ERR"
if [ -s "$_DM_ERR" ]; then
    sed 's/^/    /' "$_DM_ERR"; bad "second demonstration emitted stderr"
    die "demo stderr"
fi
if ! "$TRUSTED_PYTHON3" -B -c 'import sys
a=open(sys.argv[1],"rb").read(); b=open(sys.argv[2],"rb").read()
sys.exit(0 if a==b and a else 1)' "$_DEMO_DIR/transcript_1.txt" "$_DEMO_DIR/transcript_2.txt"; then
    bad "demo transcript is not deterministic across two runs"
    echo "MOVE_84_DEMO_OUTPUT: FAIL"; die "demo determinism"
fi
ok "demonstration transcript is byte-identical across two runs"

# The DEBUG profile must reproduce the same demonstration.
"$TRUSTED_PYTHON3" -B "$P/demo.py" --mode demonstrate \
    --verifier "$DEBUG_BIN" --python-bin "$TRUSTED_PY" \
    --companion "$ROOT/src/12_companion_cli_v031/companion.py" \
    --fixtures "$_DEMO_DIR/fixtures.json" \
    --expectations "$_DEMO_DIR/expectations.json" \
    --transcript-out "$_DEMO_DIR/transcript_debug.txt" \
    >/dev/null 2>"$_DM_ERR"
_dbg_dm=$?
if [ -s "$_DM_ERR" ]; then
    sed 's/^/    /' "$_DM_ERR"; bad "debug demonstration emitted stderr"
    die "demo stderr"
fi
[ "$_dbg_dm" -eq 0 ] || { bad "the debug profile did not reproduce the demonstration"; die "demo debug"; }
ok "the debug profile reproduced the demonstration"
DEMO_OUTPUT=PASS

# Adopted USAGE contract, executed rather than assumed.
_US_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_US_OUT"
_US_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_US_ERR"
"$TRUSTED_PYTHON3" -B "$PB/equivalence.py" --mode usage-contract \
    --release-bin "$RELEASE_BIN" --debug-bin "$DEBUG_BIN" \
    --baseline-bin "$BASELINE_BIN" \
    --standalone-dir "$STAGE_DIR/standalone_usage" \
    >"$_US_OUT" 2>"$_US_ERR"
_us_rc=$?
cat "$_US_OUT"
if [ -s "$_US_ERR" ]; then
    sed 's/^/    /' "$_US_ERR"; bad "usage harness emitted stderr"
    die "usage contract"
fi
if [ "$_us_rc" -ne 0 ]; then
    bad "usage behaviour differs across profiles or from the adopted baseline"
    echo "MOVE_84_CONTROLLED_BEHAVIOUR: FAIL"
    die "usage contract"
fi
ok "adopted usage behaviour reproduced by both profiles, the baseline authority and the staged standalone binary"

# =========================================================================
# MOVE 84 DEMONSTRATION STAGES. Exercised on the freshly
# built release binary, every report is validated, and every report is
# cross-checked against the ADOPTED legacy verdict line for the same input
# so a report can never contradict the evaluation it claims to describe.
# =========================================================================
echo ""
echo "STAGE R: structured report output (witness-report/1)"
_RPT_DIR="$STAGE_DIR/reports"
mkdir -p "$_RPT_DIR" || die "could not create report staging dir"
_rpt_index=0
_report_case() {
    _rc_sub=$1; _rc_input=$2; _rc_label=$3
    _rpt_index=$((_rpt_index + 1))
    _RC_REPORT="$_RPT_DIR/report_${_rpt_index}.json"
    _RC_RERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RC_RERR"
    _RC_LEG=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RC_LEG"
    _RC_LERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RC_LERR"
    _RC_VOUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RC_VOUT"
    _RC_VERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RC_VERR"

    # the ADOPTED legacy invocation, unchanged
    if [ "$_rc_sub" = "report-bundle" ]; then
        "$RELEASE_BIN" verify "$_rc_input" >"$_RC_LEG" 2>"$_RC_LERR"
    else
        "$RELEASE_BIN" inspect-archive "$_rc_input" >"$_RC_LEG" 2>"$_RC_LERR"
    fi
    _rc_legacy_exit=$?
    if [ -s "$_RC_LERR" ]; then
        sed 's/^/    /' "$_RC_LERR"
        bad "legacy invocation emitted stderr on $_rc_label"
        die "report legacy stderr"
    fi

    # the NEW report invocation
    "$RELEASE_BIN" "$_rc_sub" "$_rc_input" >"$_RC_REPORT" 2>"$_RC_RERR"
    _rc_report_exit=$?
    if [ -s "$_RC_RERR" ]; then
        sed 's/^/    /' "$_RC_RERR"
        bad "report invocation emitted stderr on $_rc_label"
        die "report stderr"
    fi
    if [ "$_rc_report_exit" -ne "$_rc_legacy_exit" ]; then
        bad "report exit $_rc_report_exit differs from legacy exit $_rc_legacy_exit on $_rc_label"
        die "report exit"
    fi

    # BOTH candidate profiles must produce byte-identical reports
    _RC_DBG="$_RPT_DIR/report_${_rpt_index}_debug.json"
    "$DEBUG_BIN" "$_rc_sub" "$_rc_input" >"$_RC_DBG" 2>>"$_RC_RERR"
    if [ -s "$_RC_RERR" ]; then
        sed 's/^/    /' "$_RC_RERR"
        bad "debug report invocation emitted stderr on $_rc_label"
        die "report stderr"
    fi
    if ! "$TRUSTED_PYTHON3" -B -c 'import sys
a=open(sys.argv[1],"rb").read(); b=open(sys.argv[2],"rb").read()
sys.exit(0 if a==b and a else 1)' "$_RC_REPORT" "$_RC_DBG"; then
        bad "release and debug reports differ on $_rc_label"
        die "report profile divergence"
    fi

    "$TRUSTED_PYTHON3" -B "$PR/report_schema.py" \
        --report "$_RC_REPORT" --legacy-stdout "$_RC_LEG" \
        --legacy-exit "$_rc_legacy_exit" \
        >"$_RC_VOUT" 2>"$_RC_VERR"
    _rc_v=$?
    cat "$_RC_VOUT"
    if [ -s "$_RC_VERR" ]; then
        sed 's/^/    /' "$_RC_VERR"
        bad "report validator emitted stderr on $_rc_label"
        die "report validator stderr"
    fi
    if [ "$_rc_v" -ne 0 ]; then
        echo "---- BEGIN REPORT ($_rc_label) ----"
        cat "$_RC_REPORT"
        echo "---- END REPORT ----"
        bad "report failed validation on $_rc_label"
        echo "MOVE_84_DEMO_OUTPUT: FAIL"
        die "report validation"
    fi
    ok "core report validated and consistent with the adopted legacy line: $_rc_label"

    # CLASSIFICATION. final_reason_class and final_stage are LOOKED UP in
    # the adopted reason_map.json bytes; nothing restates those mappings.
    _RC_CLS="$_RPT_DIR/report_${_rpt_index}_classified.json"
    _RC_COUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RC_COUT"
    _RC_CERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RC_CERR"
    "$TRUSTED_PYTHON3" -B "$PR/report_schema.py" \
        --report "$_RC_REPORT" --reason-map "$_RMAP" \
        --classify-out "$_RC_CLS" >"$_RC_COUT" 2>"$_RC_CERR"
    _rc_c=$?
    cat "$_RC_COUT"
    if [ -s "$_RC_CERR" ]; then
        sed 's/^/    /' "$_RC_CERR"
        bad "report classification emitted stderr on $_rc_label"
        die "report classification stderr"
    fi
    if [ "$_rc_c" -ne 0 ]; then
        bad "report classification failed on $_rc_label"
        echo "MOVE_84_DEMO_OUTPUT: FAIL"
        die "report classification"
    fi

    _RC_C2OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RC_C2OUT"
    _RC_C2ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RC_C2ERR"
    "$TRUSTED_PYTHON3" -B "$PR/report_schema.py" --classified \
        --report "$_RC_CLS" --legacy-stdout "$_RC_LEG" \
        --legacy-exit "$_rc_legacy_exit" \
        >"$_RC_C2OUT" 2>"$_RC_C2ERR"
    _rc_c2=$?
    cat "$_RC_C2OUT"
    if [ -s "$_RC_C2ERR" ]; then
        sed 's/^/    /' "$_RC_C2ERR"
        bad "classified report validation emitted stderr on $_rc_label"
        die "classified validation stderr"
    fi
    if [ "$_rc_c2" -ne 0 ]; then
        echo "---- BEGIN CLASSIFIED REPORT ($_rc_label) ----"
        cat "$_RC_CLS"
        echo "---- END CLASSIFIED REPORT ----"
        bad "classified report failed validation on $_rc_label"
        echo "MOVE_84_DEMO_OUTPUT: FAIL"
        die "classified report"
    fi
    ok "classified report validated (class and stage from the adopted reason map): $_rc_label"
}

_report_case report-bundle "$BUNDLE" "clean frozen bundle"
for _rc_f in "$_FIX_DIR"/*; do
    [ -e "$_rc_f" ] || continue
    case "$_rc_f" in
        *.zip) _report_case report-archive "$_rc_f" "${_rc_f##*/}" ;;
        *)     [ -d "$_rc_f" ] && _report_case report-bundle "$_rc_f" "${_rc_f##*/}" ;;
    esac
done
echo "---- BEGIN CORE REPORT SAMPLE (clean frozen bundle) ----"
cat "$_RPT_DIR/report_1.json"
echo "---- END CORE REPORT SAMPLE ----"
echo "---- BEGIN CLASSIFIED REPORT SAMPLE (clean frozen bundle) ----"
cat "$_RPT_DIR/report_1_classified.json"
echo "---- END CLASSIFIED REPORT SAMPLE ----"
ok "every report validated against witness-report/1 and the adopted legacy verdict"

# -------------------------------------------------------------------------
# DIGEST DIFFERENTIAL STAGE. The digest contract claims the digest binds
# exact path, ACTUAL mode bits and content. That is proven here by running
# the REAL compiled binary over trees that differ in exactly one of those.
# A Python model of the serialization is supplementary only.
# -------------------------------------------------------------------------
echo ""
echo "STAGE R2: digest binds path, actual mode bits and content"
_DGF="$STAGE_DIR/digest_fixtures"
_PTF="$STAGE_DIR/path_fixtures"
_DGM="$STAGE_DIR/digest_fixtures.json"
_DG_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_DG_OUT"
_DG_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_DG_ERR"
"$TRUSTED_PYTHON3" -B "$PR/report_schema.py" \
    --make-digest-fixtures "$_DGF" --make-path-fixtures "$_PTF" \
    --fixtures-out "$_DGM" >"$_DG_OUT" 2>"$_DG_ERR"
_dg_rc=$?
cat "$_DG_OUT"
if [ -s "$_DG_ERR" ]; then
    sed 's/^/    /' "$_DG_ERR"
    bad "digest fixture construction emitted stderr"
    die "digest fixtures stderr"
fi
if [ "$_dg_rc" -ne 0 ]; then
    bad "digest fixture construction failed"; die "digest fixtures"
fi

_digest_of() {
    # $1 = bundle root, $2 = binary; prints the input_digest value
    _do_rep=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_do_rep"
    _do_err=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_do_err"
    "$2" report-bundle "$1" >"$_do_rep" 2>"$_do_err"
    if [ -s "$_do_err" ]; then
        sed 's/^/    /' "$_do_err"
        bad "report invocation emitted stderr on $1"
        die "digest differential stderr"
    fi
    "$TRUSTED_PYTHON3" -B -c 'import json,sys
d=json.load(open(sys.argv[1]))["input_digest"]
sys.stdout.write(str(d.get("value")))' "$_do_rep"
}

# Structural cases are included here: each pair differs ONLY in tree
# structure, with identical regular-file bytes and modes on both sides, so
# a digest that covered regular files alone would produce equal values.
_DIF_CASES=$("$TRUSTED_PYTHON3" -B -c 'import json,sys
m=json.load(open(sys.argv[1]))
for c in m["digest_cases"]:
    a,b=c["sides"]
    print("%s\t%s\t%s\t%s" % (c["case_id"], a["root"], b["root"],
                                "1" if c["must_differ"] else "0"))
for c in m.get("structure_cases", []):
    if not c.get("supported"):
        continue
    a,b=c["sides"]
    print("%s\t%s\t%s\t1" % (c["case_id"], a["root"], b["root"]))' "$_DGM")
[ -n "$_DIF_CASES" ] || die "no digest differential cases"

echo "$_DIF_CASES" | while IFS="$(printf '\t')" read -r _c_id _c_a _c_b _c_diff; do
    [ -n "$_c_id" ] || continue
    _ra=$(_digest_of "$_c_a" "$RELEASE_BIN")
    _rb=$(_digest_of "$_c_b" "$RELEASE_BIN")
    _da=$(_digest_of "$_c_a" "$DEBUG_BIN")
    _db=$(_digest_of "$_c_b" "$DEBUG_BIN")
    if [ "$_ra" != "$_da" ] || [ "$_rb" != "$_db" ]; then
        bad "release and debug digests differ on $_c_id"
        die "digest profile divergence"
    fi
    if [ "$_c_diff" = "1" ]; then
        if [ "$_ra" = "$_rb" ]; then
            bad "$_c_id: digest UNCHANGED although the bound property differs"
            echo "MOVE_84_DEMO_OUTPUT: FAIL"
            die "digest binding"
        fi
        echo "  OK    $_c_id: digest differs as the contract requires"
    else
        if [ "$_ra" != "$_rb" ]; then
            bad "$_c_id: identical trees produced different digests"
            echo "MOVE_84_DEMO_OUTPUT: FAIL"
            die "digest determinism"
        fi
        echo "  OK    $_c_id: identical trees produce an identical digest"
    fi
done || die "digest differential"

# hostile names: each must be digestible and distinct from the others
_PATH_ROOTS=$("$TRUSTED_PYTHON3" -B -c 'import json,sys
m=json.load(open(sys.argv[1]))
for c in m.get("path_cases", []):
    if c.get("supported"):
        print("%s\t%s" % (c["case_id"], c["root"]))' "$_DGM")
_PATH_SEEN="$STAGE_DIR/path_digests.txt"
: > "$_PATH_SEEN"
echo "$_PATH_ROOTS" | while IFS="$(printf '\t')" read -r _p_id _p_root; do
    [ -n "$_p_id" ] || continue
    _pd=$(_digest_of "$_p_root" "$RELEASE_BIN")
    echo "$_pd $_p_id" >> "$_PATH_SEEN"
    echo "  OK    $_p_id: hostile name digested"
done || die "path fixtures"
if [ -s "$_PATH_SEEN" ]; then
    _dupes=$(cut -d' ' -f1 "$_PATH_SEEN" | sort | uniq -d)
    if [ -n "$_dupes" ]; then
        bad "distinct hostile names produced the same digest"
        echo "MOVE_84_DEMO_OUTPUT: FAIL"
        die "path collision"
    fi
fi
# Determinism: the identical tree digested twice must give identical bytes.
_DET_A=$(_digest_of "$BUNDLE" "$RELEASE_BIN")
_DET_B=$(_digest_of "$BUNDLE" "$RELEASE_BIN")
if [ "$_DET_A" != "$_DET_B" ]; then
    bad "repeated runs over the identical tree produced different digests"
    echo "MOVE_84_DEMO_OUTPUT: FAIL"
    die "digest determinism"
fi
echo "  OK    repeated runs over the identical tree agree"
ok "digest binds the complete tree structure with exact paths and actual mode bits and content; distinct names never collide"
DIGEST_BINDING=PASS
REPORT_OUTPUT=PASS
CONTROLLED_BEHAVIOUR=PASS

# Both binaries through the UNCHANGED adopted Move 81 adapter: the canonical
# structured records must be byte-identical.
_A81="$ROOT/verify/structured_verdict_v01/adapter.py"
_RMAP="$ROOT/verify/agreement_harness_v01/reason_map.json"
_AR1=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_AR1"
_AR2=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_AR2"
_ARE=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_ARE"
"$TRUSTED_PYTHON3" -B "$_A81" verdict --lane rust_bundle \
    --input "$BUNDLE" --reason-map "$_RMAP" --rust-bin "$RELEASE_BIN" \
    >"$_AR1" 2>"$_ARE"
"$TRUSTED_PYTHON3" -B "$_A81" verdict --lane rust_bundle \
    --input "$BUNDLE" --reason-map "$_RMAP" --rust-bin "$DEBUG_BIN" \
    >"$_AR2" 2>>"$_ARE"
if [ -s "$_ARE" ]; then
    sed 's/^/    /' "$_ARE"; bad "adapter emitted stderr"; die "adapter"
fi
if ! "$TRUSTED_PYTHON3" -B -c 'import sys
a=open(sys.argv[1],"rb").read(); b=open(sys.argv[2],"rb").read()
sys.exit(0 if a==b and a else 1)' "$_AR1" "$_AR2"; then
    echo "  release record:"; sed 's/^/    /' "$_AR1"
    echo "  debug record:";   sed 's/^/    /' "$_AR2"
    bad "structured records from the two profiles differ"
    echo "MOVE_84_DEBUG_RELEASE_EQUIVALENCE: FAIL"
    die "adapter equivalence"
fi
if grep -q '"verdict":"PASS"' "$_AR1"; then
    bad "release binary produced a Rust PASS verdict (honesty violation)"
    die "rust honesty"
fi
ok "both profiles produce byte-identical canonical structured records; no Rust PASS"
DEBUG_RELEASE_EQUIVALENCE=PASS

# =========================================================================
# STAGE H -- provenance (generated into staging, published later).
# =========================================================================
echo ""
echo "STAGE H: build provenance"
# The gate runs NO inline Python: assembly goes through provenance.py, the
# exact path the focused suite drives end to end.
_BLD_FACTS="$STAGE_DIR/build_facts.json"
_BFX_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_BFX_ERR"
"$TRUSTED_PYTHON3" -B -c 'import sys
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if line.startswith("{"):
        open(sys.argv[2], "w", encoding="utf-8").write(line + "\n")
        raise SystemExit(0)
raise SystemExit(1)' "$_BLD_OUT" "$_BLD_FACTS" 2>"$_BFX_ERR"
_bfx_rc=$?
if [ -s "$_BFX_ERR" ]; then
    sed 's/^/    /' "$_BFX_ERR"
    bad "build-facts extraction emitted stderr"; die "build facts stderr"
fi
if [ "$_bfx_rc" -ne 0 ]; then
    bad "could not extract build facts"; die "build facts"
fi
if [ ! -s "$_BLD_FACTS" ]; then
    bad "build-facts extraction produced no output"; die "build facts"
fi

_FINAL_BASE="witness-verify-${_EXPECT_VERSION}-${_RUSTC_HOST}-release"
_PROV_STAGED="$STAGE_DIR/${_FINAL_BASE}.provenance.json"
_PRV_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_PRV_OUT"
_PRV_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_PRV_ERR"
"$TRUSTED_PYTHON3" -B "$PB/provenance.py" \
    --inspect-json "$_INS_JSON" --build-json "$_BLD_FACTS" \
    --binary "$RELEASE_BIN" \
    --reported-version "$_EXPECT_VERSION" \
    --source-candidate-name "${CAND_ZIP##*/}" \
    --source-candidate-sha256 "$_CAND_SHA" \
    --baseline-name "project-witness-MOVE_83_candidate_v13.zip" \
    --baseline-sha256 "$_M83_EXPECT" \
    --test-level fixture_tested \
    --transcript-name "$MOVE84_TRANSCRIPT_NAME" \
    --out "$_PROV_STAGED" >"$_PRV_OUT" 2>"$_PRV_ERR"
_prv_rc=$?
cat "$_PRV_OUT"
if [ -s "$_PRV_ERR" ]; then
    sed 's/^/    /' "$_PRV_ERR"; bad "provenance emitted stderr"
    die "provenance"
fi
if [ "$_prv_rc" -ne 0 ]; then
    bad "provenance record failed validation"
    echo "MOVE_84_PROVENANCE: FAIL"; die "provenance"
fi
echo "---- BEGIN BUILD PROVENANCE RECORD ----"
cat "$_PROV_STAGED"
echo "---- END BUILD PROVENANCE RECORD ----"
ok "canonical build-provenance record generated and validated"
PROVENANCE=PASS

# =========================================================================
# STAGE I -- focused suite.
# =========================================================================
echo ""
echo "STAGE I: Move 84 focused suite"
_MT_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_MT_OUT"
_MT_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_MT_ERR"
( cd "$P" && MOVE84_TEST_SH="$TRUSTED_SH" \
  "$TRUSTED_PYTHON3" -B -W error::ResourceWarning \
  demo_tests.py ) >"$_MT_OUT" 2>"$_MT_ERR"; _mt_rc=$?
if [ "$_mt_rc" -ne 0 ]; then
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused tests failed (exit $_mt_rc)"; die "focused tests"
fi
tail -3 "$_MT_OUT" | sed 's/^/    /'
gate_require_clean_stderr "$_MT_ERR" "focused tests" || {
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    die "focused tests stderr"; }
# The focused result is validated by a helper that anchors the success
# summary to the FINAL stdout line and accepts unittest's legitimate
# annotated forms. A genuine Termux run emitted "OK (skipped=2)" for a
# successful suite and the previous bare-"OK" grep rejected it, while
# "skipped=" was separately treated as a forbidden marker.
_FR_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_FR_OUT"
_FR_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_FR_ERR"
"$TRUSTED_PYTHON3" -B "$PR/check_focused_result.py" \
    --stdout "$_MT_OUT" --stderr "$_MT_ERR" --exit-code "$_mt_rc" \
    --expect-count "$P/EXPECTED_TEST_COUNT.txt" \
    >"$_FR_OUT" 2>"$_FR_ERR"
_fr_rc=$?
cat "$_FR_OUT"
if [ -s "$_FR_ERR" ]; then
    sed 's/^/    /' "$_FR_ERR"
    bad "focused result validator emitted stderr"
    die "focused result stderr"
fi
if [ "$_fr_rc" -ne 0 ]; then
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused suite result did not validate"
    die "focused result"
fi
ok "focused suite PASS (exact pinned count, valid success summary, stderr empty, skips reported honestly)"

# =========================================================================
# STAGE J -- complete unchanged Move 83 regression from an extracted copy
# of the adopted Move 83 v13 archive. Move 82 v07 is supplied to that
# child as one of ITS dependencies; it is not the Move 84 baseline.
# =========================================================================
echo ""
echo "STAGE J: complete adopted Move 83 v13 adoption/regression child gate"
# The adopted Move 83 gate derives its own run directory as the directory
# CONTAINING the candidate zip it is given, and then requires its
# MOVE83_OUTPUT_DIR to sit inside that run directory while staying outside
# the extracted source root. v08 handed the child an unrelated temporary
# directory, so the adopted checker correctly refused it. The child now
# gets a purpose-built private run directory:
#
#   $_M83_RUN/
#       project-witness-MOVE_83_candidate_v13.zip   (verified copy)
#       project-witness-main/                       (extracted source)
#       move83_output/                              (fresh and empty)
#
_M83_RUN=$("$TRUSTED_MKTEMP" -d) || die "could not create the Move 83 child run dir"
gate_track_tmp "$_M83_RUN"
_M83_EXTRACT="$_M83_RUN"
_M83_XOUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M83_XOUT"
_M83_XERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M83_XERR"
"$TRUSTED_PYTHON3" -B "$P/check_move84_inherited.py" \
    --baseline-zip "$M83_ZIP" --expect-sha256 "$_M83_EXPECT" \
    --extract-to "$_M83_EXTRACT" >"$_M83_XOUT" 2>"$_M83_XERR"
_m83_x_rc=$?
echo "---- BEGIN REAL_MOVE83 VALIDATED EXTRACTION EVIDENCE ----"
cat "$_M83_XOUT"
echo "---- END REAL_MOVE83 VALIDATED EXTRACTION EVIDENCE ----"
if [ -s "$_M83_XERR" ]; then
    sed 's/^/    /' "$_M83_XERR"
    bad "baseline extraction emitted stderr"; die "move83 extraction"
fi
[ "$_m83_x_rc" -eq 0 ] || die "REAL_MOVE83 could not be safely extracted"
_M83_ROOT="$_M83_EXTRACT/project-witness-main"
[ -f "$_M83_ROOT/tools/check_move83_report_adoption.sh" ] \
    || die "extracted Move 83 root is not a complete Move 83 tree"
ok "REAL_MOVE83 extracted into the private Move 83 child run directory"

# Place the verified candidate zip INSIDE the child run directory, so the
# adopted gate's own run-directory derivation resolves to $_M83_RUN.
_M83_CHILD_ZIP="$_M83_RUN/project-witness-MOVE_83_candidate_v13.zip"
cp -- "$M83_ZIP" "$_M83_CHILD_ZIP" || die "could not stage the Move 83 child zip"
_M83_CZ_SHA=$("$TRUSTED_SHA256SUM" "$_M83_CHILD_ZIP" | cut -d" " -f1)
if [ "$_M83_CZ_SHA" != "$_M83_EXPECT" ]; then
    bad "staged Move 83 child zip hash $_M83_CZ_SHA does not match the adopted $_M83_EXPECT"
    die "move83 child zip"
fi
ok "adopted Move 83 v13 zip staged into the child run directory and re-verified"

_M83_CHILD_OUT="$_M83_RUN/move83_output"
mkdir "$_M83_CHILD_OUT" || die "could not create the Move 83 child output dir"

_M83_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M83_OUT"
_M83_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M83_ERR"
# The adopted Move 83 gate has its OWN mandatory input contract:
# MOVE83_CANDIDATE_ZIP, MOVE83_CANDIDATE_SHA256, MOVE83_OUTPUT_DIR,
# REAL_MOVE81, REAL_MOVE80, REAL_MOVE79, REAL_MOVE78 and REAL_705.
# Forwarding only the REAL_* dependencies would terminate the child with
# usage exit 2 before it could establish anything. A FRESH, EMPTY,
# gate-owned output directory is created for the child; the Move 84
# output directory is never reused.
case "$_M83_CHILD_OUT" in
    "$_M83_ROOT"|"$_M83_ROOT"/*)
        bad "Move 83 child output dir is inside the extracted Move 83 source root"
        die "move83 child output dir" ;;
esac
if [ "$_M83_CHILD_OUT" = "$OUT_DIR" ]; then
    bad "the Move 83 child must not reuse the Move 84 output directory"
    die "move83 child output dir"
fi
if [ -n "$(ls -A "$_M83_CHILD_OUT" 2>/dev/null)" ]; then
    bad "Move 83 child output dir is not empty"; die "move83 child output dir"
fi
# The child's own output-directory checker lives in the child tree, at
# the path the ADOPTED Move 83 gate itself uses. It is verified present
# before invocation so a wrong path fails here with a clear message
# instead of as an opaque exit 2 from python3.
_M83_ODC="$_M83_ROOT/verify/report_v01/check_move83_inherited.py"
if [ ! -f "$_M83_ODC" ] || [ -L "$_M83_ODC" ]; then
    bad "the adopted Move 83 output-directory checker is missing from the extracted child tree: $_M83_ODC"
    die "move83 child helper"
fi
ok "adopted Move 83 output-directory checker present in the extracted child tree"

# Independently run the ADOPTED Move 83 output-directory checker, from the
# extracted adopted tree, against the exact paths the child will receive.
# If the layout does not satisfy the adopted contract, fail HERE rather
# than after the child has done minutes of work.
_M83_ODO=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M83_ODO"
_M83_ODE=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M83_ODE"
"$TRUSTED_PYTHON3" -B "$_M83_ODC" \
    --check-output-dir "$_M83_CHILD_OUT" --run-dir "$_M83_RUN" \
    --candidate-root "$_M83_ROOT" >"$_M83_ODO" 2>"$_M83_ODE"
_m83_odo_rc=$?
cat "$_M83_ODO"
if [ -s "$_M83_ODE" ]; then
    sed 's/^/    /' "$_M83_ODE"
    bad "adopted Move 83 output-dir checker emitted stderr"
    die "move83 child output dir"
fi
if [ "$_m83_odo_rc" -ne 0 ]; then
    bad "the proposed Move 83 child layout does not satisfy the adopted output-directory contract"
    die "move83 child output dir"
fi
ok "child layout accepted by the ADOPTED Move 83 output-directory checker"
( cd "$_M83_ROOT" \
  && MOVE83_CANDIDATE_ZIP="$_M83_CHILD_ZIP" \
     MOVE83_CANDIDATE_SHA256="$_M83_EXPECT" \
     MOVE83_OUTPUT_DIR="$_M83_CHILD_OUT" \
     REAL_MOVE81="$REAL_MOVE81" REAL_MOVE80="$REAL_MOVE80" \
     REAL_MOVE79="$REAL_MOVE79" REAL_MOVE78="$REAL_MOVE78" \
     REAL_705="$REAL_705" REAL_V20="${REAL_V20:-}" \
     LD_PRELOAD="$GATE_PRELOAD" \
     "$TRUSTED_SH" tools/check_move83_report_adoption.sh \
) >"$_M83_OUT" 2>"$_M83_ERR"; _m83_rc=$?
echo "---- BEGIN COMPLETE MOVE 83 CHILD GATE STDOUT (retained) ----"
cat "$_M83_OUT"
echo "---- END COMPLETE MOVE 83 CHILD GATE STDOUT ----"
echo "---- BEGIN COMPLETE MOVE 83 CHILD GATE STDERR (retained) ----"
cat "$_M83_ERR"
echo "---- END COMPLETE MOVE 83 CHILD GATE STDERR ----"
# Merging the streams could not prove stderr was empty, so they are kept
# apart and the stderr is required to be byte-empty.
if [ -s "$_M83_ERR" ]; then
    bad "Move 83 child gate emitted stderr"
    die "move83 child stderr"
fi
if [ "$_m83_rc" -ne 0 ]; then
    bad "Move 83 child adoption gate failed (exit $_m83_rc)"
    die "move83 regression"
fi
# The child is the ADOPTED MOVE 83 v13 gate. Only markers that gate can
# GENUINELY EMIT as "<NAME>: PASS" are required. It assigns REPORT_OUTPUT
# and DIGEST_BINDING internally but never echoes them in its terminal
# summary -- they appear only on FAIL paths -- so requiring them rejected
# a genuinely successful child run. The required set below is exactly the
# ten markers the adopted gate echoes on success, plus the inherited
# regression marker and the two adopted divergences.
#
# It emits its OWN MOVE_83_*
# stage markers, and -- because it in turn reruns its inherited Move 82
# gate -- its retained transcript also carries genuine MOVE_82_* markers.
# Both are required. The MOVE_82_* ones are inherited evidence produced by
# the child, never relabelled here.
for _need in \
    "MOVE_83_REPORT_ADOPTION_GATE: PASS" \
    "MOVE_83_CANDIDATE_IDENTITY: PASS" \
    "MOVE_83_BASELINE_IMMUTABILITY: PASS" \
    "MOVE_83_TARGET_DETECTION: PASS" \
    "MOVE_83_CLEAN_RELEASE_BUILD: PASS" \
    "MOVE_83_BINARY_INSPECTION: PASS" \
    "MOVE_83_STANDALONE_EXECUTION: PASS" \
    "MOVE_83_CONTROLLED_BEHAVIOUR: PASS" \
    "MOVE_83_DEBUG_RELEASE_EQUIVALENCE: PASS" \
    "MOVE_83_PROVENANCE: PASS" \
    "MOVE_82_REGRESSION_GATE: PASS" \
    "SYSTEM_AGREEMENT_RESULT: FAIL" \
    "SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED"; do
    if ! grep -qF "$_need" "$_M83_OUT"; then
        bad "Move 83 child gate missing expected marker: $_need"
        die "move83 markers"
    fi
done
ok "Move 83 child gate PASS (its own stages, its inherited Move 82 regression evidence, and the two adopted divergences)"

MOVE_83_REGRESSION=PASS

# =========================================================================
# STAGE K -- package hygiene.
# =========================================================================
echo ""
echo "STAGE K: package hygiene"
_PH_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_PH_OUT"
_PH_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_PH_ERR"
"$TRUSTED_SH" tools/check_package_hygiene.sh >"$_PH_OUT" 2>"$_PH_ERR"
_ph_rc=$?
if [ -s "$_PH_ERR" ]; then
    sed 's/^/    /' "$_PH_ERR"
    bad "package hygiene emitted stderr"; die "package hygiene stderr"
fi
if [ "$_ph_rc" -ne 0 ]; then
    sed 's/^/    /' "$_PH_OUT"; bad "package hygiene"; die "package hygiene"
fi
ok "package hygiene PASS"

if [ "$fail" -ne 0 ]; then
    die "one or more checks failed"
fi

# =========================================================================
# PUBLICATION -- only now, after every substantive check has passed.
# =========================================================================
echo ""
echo "PUBLICATION: placing final artefacts in MOVE84_OUTPUT_DIR"
_PUB_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_PUB_OUT"
_PUB_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_PUB_ERR"
"$TRUSTED_PYTHON3" -B "$PB/provenance.py" \
    --publish-binary "$RELEASE_BIN" --publish-record "$_PROV_STAGED" \
    --publish-dir "$OUT_DIR" --publish-base "$_FINAL_BASE" \
    >"$_PUB_OUT" 2>"$_PUB_ERR"
_pub_rc=$?
cat "$_PUB_OUT"
if [ -s "$_PUB_ERR" ]; then
    sed 's/^/    /' "$_PUB_ERR"; bad "publication emitted stderr"
    die "publication"
fi
if [ "$_pub_rc" -ne 0 ]; then
    bad "publication failed; every partially published file was rolled back"
    die "publication"
fi
ok "final artefacts published"

# =========================================================================
# FINAL MARKERS
# =========================================================================
echo ""
echo "==========================================================="
echo "MOVE_84_CANDIDATE_IDENTITY: $CANDIDATE_IDENTITY"
echo "MOVE_84_BASELINE_IMMUTABILITY: $BASELINE_IMMUTABILITY"
echo "MOVE_84_TARGET_DETECTION: $TARGET_DETECTION"
echo "MOVE_84_CLEAN_RELEASE_BUILD: $CLEAN_RELEASE_BUILD"
echo "MOVE_84_BINARY_INSPECTION: $BINARY_INSPECTION"
echo "MOVE_84_STANDALONE_EXECUTION: $STANDALONE_EXECUTION"
echo "MOVE_84_CONTROLLED_BEHAVIOUR: $CONTROLLED_BEHAVIOUR"
echo "MOVE_84_DEBUG_RELEASE_EQUIVALENCE: $DEBUG_RELEASE_EQUIVALENCE"
echo "MOVE_84_PROVENANCE: $PROVENANCE"
echo "MOVE_83_REGRESSION_GATE: $MOVE_83_REGRESSION"
echo "SYSTEM_AGREEMENT_RESULT: FAIL"
echo "SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED"
echo "MOVE_84_TARGET_ANDROID_TERMUX_AARCH64: NATIVE_BUILD_AND_RUNTIME_TEST_PRACTICAL"
echo "MOVE_84_TARGET_LINUX_X86_64: NOT_CURRENTLY_ESTABLISHABLE"
echo "MOVE_84_TARGET_LINUX_AARCH64: NOT_CURRENTLY_ESTABLISHABLE"
echo "MOVE_84_TARGET_WINDOWS_X86_64: NOT_CURRENTLY_ESTABLISHABLE"
echo "MOVE_84_DEMO_ADOPTION_GATE: PASS"
echo "exit_code: 0"
exit 0
