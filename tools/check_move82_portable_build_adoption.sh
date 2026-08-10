#!/bin/sh
# MOVE 82 PORTABLE BUILD ADOPTION GATE.
#
# Move 82 produces ONE target-specific standalone witness-verify executable
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
#   MOVE82_CANDIDATE_ZIP     the candidate archive this tree came from
#   MOVE82_CANDIDATE_SHA256  its externally supplied expected SHA-256
#   MOVE82_OUTPUT_DIR        pre-created, empty, not a symlink, outside the
#                            extracted candidate source root
#   REAL_MOVE81              adopted Move 81 v08 zip (baseline + regression)
#   REAL_MOVE80 REAL_MOVE79 REAL_MOVE78 REAL_705
#                            adopted dependencies forwarded to the child
#
# Final markers on success (exit 0):
#   MOVE_82_CANDIDATE_IDENTITY: PASS
#   MOVE_82_BASELINE_IMMUTABILITY: PASS
#   MOVE_82_TARGET_DETECTION: PASS
#   MOVE_82_CLEAN_RELEASE_BUILD: PASS
#   MOVE_82_BINARY_INSPECTION: PASS
#   MOVE_82_STANDALONE_EXECUTION: PASS
#   MOVE_82_CONTROLLED_BEHAVIOUR: PASS
#   MOVE_82_DEBUG_RELEASE_EQUIVALENCE: PASS
#   MOVE_82_PROVENANCE: PASS
#   MOVE_81_REGRESSION_GATE: PASS
#   SYSTEM_AGREEMENT_RESULT: FAIL
#   SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED
#   MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: PASS
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
[ -z "${MOVE82_CANDIDATE_ZIP:-}" ] && _missing="$_missing MOVE82_CANDIDATE_ZIP"
[ -z "${MOVE82_CANDIDATE_SHA256:-}" ] && _missing="$_missing MOVE82_CANDIDATE_SHA256"
[ -z "${MOVE82_OUTPUT_DIR:-}" ] && _missing="$_missing MOVE82_OUTPUT_DIR"
[ -z "${REAL_MOVE81:-}" ] && _missing="$_missing REAL_MOVE81"
[ -z "${REAL_MOVE80:-}" ] && _missing="$_missing REAL_MOVE80"
[ -z "${REAL_MOVE79:-}" ] && _missing="$_missing REAL_MOVE79"
[ -z "${REAL_MOVE78:-}" ] && _missing="$_missing REAL_MOVE78"
[ -z "${REAL_705:-}" ] && _missing="$_missing REAL_705"
if [ -n "$_missing" ]; then
    echo "Required input(s) not supplied:$_missing"
    echo "MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: USAGE (missing:$_missing)"
    exit 2
fi

# (1c) Every supplied path must be ABSOLUTE AS SUPPLIED, before any
#      canonicalisation. Canonicalising first would let a relative path be
#      silently promoted to an absolute one and accepted.
for _pv in "MOVE82_CANDIDATE_ZIP=$MOVE82_CANDIDATE_ZIP" \
           "MOVE82_OUTPUT_DIR=$MOVE82_OUTPUT_DIR" \
           "REAL_MOVE81=$REAL_MOVE81" "REAL_MOVE80=$REAL_MOVE80" \
           "REAL_MOVE79=$REAL_MOVE79" "REAL_MOVE78=$REAL_MOVE78" \
           "REAL_705=$REAL_705"; do
    _pval=${_pv#*=}
    case "$_pval" in
        /*) : ;;
        *)  echo "refusing: supplied path is not absolute: $_pv"
            echo "MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: FAIL (relative path)"
            exit 1 ;;
    esac
done

# (1b) Missing-preload rejection with built-ins only (Termux host).
if [ -d /data/data/com.termux/files/usr ] && [ -z "$GATE_INHERITED_LD_PRELOAD" ]; then
    echo "the legitimate Termux exec preload (libtermux-exec.so) is absent."
    echo "MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: FAIL (missing Termux exec preload)"
    exit 1
fi

# (2) Canonicalise $0 with the LITERAL trusted readlink. No PATH lookup and
#     no external dirname/pwd may run before trust is established.
_TRUSTED_READLINK=/data/data/com.termux/files/usr/bin/readlink
if [ ! -x "$_TRUSTED_READLINK" ]; then
    echo "trusted readlink absent at $_TRUSTED_READLINK (this gate runs only on Termux)"
    echo "MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
    exit 3
fi
SCRIPT_REAL=$("$_TRUSTED_READLINK" -f -- "$0") || SCRIPT_REAL=""
case "$SCRIPT_REAL" in
    */tools/check_move82_portable_build_adoption.sh) : ;;
    *)
        echo "refusing: canonical script path is not the genuine named gate ($SCRIPT_REAL)"
        echo "MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: FAIL (untrusted script path)"
        exit 1 ;;
esac
if [ ! -f "$SCRIPT_REAL" ]; then
    echo "refusing: canonical script target is not a regular file"
    echo "MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: FAIL (untrusted script path)"
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
die(){ echo "MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: FAIL ($1)"; exit 1; }

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
    echo "MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
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
    echo "MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: FAIL (nested exec)"
    exit 1
fi

P="$ROOT/verify/portable_build_v01"
TRUSTED_PY=$("$TRUSTED_READLINK" -f -- "$TRUSTED_PYTHON3") || TRUSTED_PY=""
case "$TRUSTED_PY" in /*) : ;; *) die "trusted python path" ;; esac

# =========================================================================
# STAGE A -- candidate identity. The candidate may NOT declare its own hash.
# =========================================================================
echo ""
echo "STAGE A: candidate identity (externally supplied hash)"
CAND_ZIP=$("$TRUSTED_READLINK" -f -- "$MOVE82_CANDIDATE_ZIP") || CAND_ZIP=""
case "$CAND_ZIP" in /*) : ;; *) die "MOVE82_CANDIDATE_ZIP path" ;; esac
[ -f "$CAND_ZIP" ] || die "MOVE82_CANDIDATE_ZIP is not a regular file"
_CAND_SHA=$("$TRUSTED_SHA256SUM" "$CAND_ZIP"); _CAND_SHA=${_CAND_SHA%% *}
if [ "$_CAND_SHA" != "$MOVE82_CANDIDATE_SHA256" ]; then
    bad "candidate sha256 $_CAND_SHA != supplied $MOVE82_CANDIDATE_SHA256"
    echo "MOVE_82_CANDIDATE_IDENTITY: FAIL"
    die "candidate identity"
fi
echo "MOVE82_CANDIDATE_ZIP verified by trusted sha256sum:"
echo "$_CAND_SHA"
ok "candidate identity verified against the externally supplied hash"

# The live tree must be byte-identical to the verified archive in BOTH
# directions. Hash-verifying the archive while path-checking the tree
# would let a modified allowlisted file through, binding the generated
# binary to reviewed NAMES rather than reviewed BYTES.
_SB_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_SB_OUT"
_SB_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_SB_ERR"
"$TRUSTED_PYTHON3" -B "$P/check_move82_inherited.py" \
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
    echo "MOVE_82_CANDIDATE_IDENTITY: FAIL"; die "source binding"
fi
ok "live tree bound byte-for-byte to the verified candidate archive"
CANDIDATE_IDENTITY=PASS

# Output-directory contract.
OUT_DIR=$("$TRUSTED_READLINK" -f -- "$MOVE82_OUTPUT_DIR") || OUT_DIR=""
case "$OUT_DIR" in /*) : ;; *) die "MOVE82_OUTPUT_DIR path" ;; esac
RUN_DIR=${CAND_ZIP%/*}
# The output-directory rules live in a factored production helper so they
# are executable and directly testable, rather than asserted by reading
# this script's source.
_OD_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_OD_OUT"
_OD_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_OD_ERR"
"$TRUSTED_PYTHON3" -B "$P/check_move82_inherited.py" \
    --check-output-dir "$MOVE82_OUTPUT_DIR" --run-dir "$RUN_DIR" \
    --candidate-root "$ROOT" >"$_OD_OUT" 2>"$_OD_ERR"
_od_rc=$?
cat "$_OD_OUT"
if [ -s "$_OD_ERR" ]; then
    sed 's/^/    /' "$_OD_ERR"; bad "output-dir checker emitted stderr"
    die "output dir"
fi
if [ "$_od_rc" -ne 0 ]; then
    bad "MOVE82_OUTPUT_DIR does not satisfy the output-directory contract"
    die "output dir"
fi
ok "output directory is absolute, empty, not a symlink, outside the source root"

# Private staging area. Nothing is published until every check passes.
STAGE_DIR=$("$TRUSTED_MKTEMP" -d) || die "could not create staging dir"
gate_track_tmp "$STAGE_DIR"
ok "private staging directory established"

# =========================================================================
# STAGE B -- baseline immutability against the real adopted Move 81 v08.
# =========================================================================
echo ""
echo "STAGE B: baseline immutability (candidate vs real Move 81 v08 zip)"
M81_ZIP=$("$TRUSTED_READLINK" -f -- "$REAL_MOVE81") || M81_ZIP=""
case "$M81_ZIP" in /*) : ;; *) die "REAL_MOVE81 path" ;; esac
[ -f "$M81_ZIP" ] || die "REAL_MOVE81 is not a regular file"
_M81_SHA=$("$TRUSTED_SHA256SUM" "$M81_ZIP"); _M81_SHA=${_M81_SHA%% *}
_M81_EXPECT=7b49a3a5d1e1c6380b27c7b43aca721391189cffbecbf4f51a56c4d12c1d3d0d
if [ "$_M81_SHA" != "$_M81_EXPECT" ]; then
    bad "supplied Move 81 zip sha256 $_M81_SHA != adopted $_M81_EXPECT"
    echo "MOVE_82_BASELINE_IMMUTABILITY: FAIL"; die "baseline zip hash"
fi
echo "REAL_MOVE81 verified by trusted sha256sum:"
echo "$_M81_EXPECT"
_B_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_B_OUT"
_B_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_B_ERR"
"$TRUSTED_PYTHON3" -B "$P/check_move82_inherited.py" \
    --baseline-zip "$M81_ZIP" --root "$ROOT" \
    --expect-sha256 "$_M81_EXPECT" \
    --allowlist "$P/allowlist_move82.json" >"$_B_OUT" 2>"$_B_ERR"
_b_rc=$?
echo "---- BEGIN BASELINE SAFETY + INHERITED-DIFF EVIDENCE ----"
cat "$_B_OUT"
echo "---- END BASELINE SAFETY + INHERITED-DIFF EVIDENCE ----"
if [ -s "$_B_ERR" ]; then
    sed 's/^/    /' "$_B_ERR"
    bad "baseline checker emitted stderr"
    echo "MOVE_82_BASELINE_IMMUTABILITY: FAIL"; die "baseline stderr"
fi
if [ "$_b_rc" -ne 0 ]; then
    bad "candidate does not match the adopted Move 81 v08 baseline + allowlist"
    echo "MOVE_82_BASELINE_IMMUTABILITY: FAIL"; die "baseline immutability"
fi
ok "every inherited file byte-identical; additions match the Move 82 allowlist"
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
        echo "MOVE_82_TARGET_DETECTION: FAIL"
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
"$TRUSTED_PYTHON3" -B "$P/build_binary.py" \
    --cargo "$TRUSTED_CARGO" --rustc "$TRUSTED_RUSTC" \
    --manifest-dir "$ROOT/rust" --profile release \
    --require-clean-target >"$_BLD_OUT" 2>"$_BLD_ERR"
if [ $? -ne 0 ] || [ -s "$_BLD_ERR" ]; then
    cat "$_BLD_OUT"; sed 's/^/    /' "$_BLD_ERR"
    bad "release build failed"; echo "MOVE_82_CLEAN_RELEASE_BUILD: FAIL"
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
"$TRUSTED_PYTHON3" -B "$P/build_binary.py" \
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
# candidate binaries agreeing, so the adopted Move 81 v08 verifier is
# freshly built from a private extracted copy of the adopted archive and
# its exact stdout/stderr/exit becomes the authority every candidate
# profile must match.
_BASE_EXTRACT=$("$TRUSTED_MKTEMP" -d) || die "could not create baseline dir"
gate_track_tmp "$_BASE_EXTRACT"
_BX_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_BX_OUT"
_BX_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_BX_ERR"
"$TRUSTED_PYTHON3" -B "$P/check_move82_inherited.py" \
    --baseline-zip "$M81_ZIP" --expect-sha256 "$_M81_EXPECT" \
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
"$TRUSTED_PYTHON3" -B "$P/build_binary.py" \
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
ok "adopted Move 81 baseline verifier freshly built as the byte authority"

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
CLEAN_RELEASE_BUILD=PASS

# =========================================================================
# STAGE E -- binary inspection from the binary's own headers.
# =========================================================================
echo ""
echo "STAGE E: binary inspection (parsed from the executable itself)"
_INS_JSON="$STAGE_DIR/inspect.json"
_INS_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_INS_OUT"
_INS_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_INS_ERR"
"$TRUSTED_PYTHON3" -B "$P/inspect_binary.py" --binary "$RELEASE_BIN" \
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
    echo "MOVE_82_BINARY_INSPECTION: FAIL"; die "binary inspection"
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
"$TRUSTED_PYTHON3" -B "$P/equivalence.py" --mode standalone \
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
    echo "MOVE_82_STANDALONE_EXECUTION: FAIL"; die "standalone"
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
"$TRUSTED_PYTHON3" -B "$P/equivalence.py" --mode make-edge-fixtures \
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
"$TRUSTED_PYTHON3" -B "$P/equivalence.py" --mode full-corpus \
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
    echo "MOVE_82_CONTROLLED_BEHAVIOUR: FAIL"
    die "controlled behaviour"
fi
ok "every adopted case matched its expectation, the baseline authority, both profiles and the staged standalone binary"

# Move 81 adapter equivalence across every applicable case.
_AD_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_AD_OUT"
_AD_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_AD_ERR"
"$TRUSTED_PYTHON3" -B "$P/equivalence.py" --mode adapter-equivalence \
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
    echo "MOVE_82_DEBUG_RELEASE_EQUIVALENCE: FAIL"
    die "adapter equivalence"
fi
ok "both profiles produced byte-identical canonical structured records; no Rust PASS"

# Hostile edge fixtures: exact declared stage per fixture.
_EDQ_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_EDQ_OUT"
_EDQ_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_EDQ_ERR"
"$TRUSTED_PYTHON3" -B "$P/equivalence.py" --mode edge-equivalence \
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
    echo "MOVE_82_DEBUG_RELEASE_EQUIVALENCE: FAIL"
    die "edge equivalence"
fi
ok "every hostile edge fixture was answered at its declared stage and both profiles agreed"

# Adopted USAGE contract, executed rather than assumed.
_US_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_US_OUT"
_US_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_US_ERR"
"$TRUSTED_PYTHON3" -B "$P/equivalence.py" --mode usage-contract \
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
    echo "MOVE_82_CONTROLLED_BEHAVIOUR: FAIL"
    die "usage contract"
fi
ok "adopted usage behaviour reproduced by both profiles, the baseline authority and the staged standalone binary"
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
    echo "MOVE_82_DEBUG_RELEASE_EQUIVALENCE: FAIL"
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
"$TRUSTED_PYTHON3" -B "$P/provenance.py" \
    --inspect-json "$_INS_JSON" --build-json "$_BLD_FACTS" \
    --binary "$RELEASE_BIN" \
    --reported-version "$_EXPECT_VERSION" \
    --source-candidate-name "${CAND_ZIP##*/}" \
    --source-candidate-sha256 "$_CAND_SHA" \
    --baseline-name "project-witness-MOVE_81_candidate_v08.zip" \
    --baseline-sha256 "$_M81_EXPECT" \
    --test-level fixture_tested \
    --transcript-name "MOVE_82_V07_TERMUX_GATE.txt" \
    --out "$_PROV_STAGED" >"$_PRV_OUT" 2>"$_PRV_ERR"
_prv_rc=$?
cat "$_PRV_OUT"
if [ -s "$_PRV_ERR" ]; then
    sed 's/^/    /' "$_PRV_ERR"; bad "provenance emitted stderr"
    die "provenance"
fi
if [ "$_prv_rc" -ne 0 ]; then
    bad "provenance record failed validation"
    echo "MOVE_82_PROVENANCE: FAIL"; die "provenance"
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
echo "STAGE I: Move 82 focused suite"
_MT_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_MT_OUT"
_MT_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_MT_ERR"
( cd "$P" && MOVE82_TEST_SH="$TRUSTED_SH" \
  "$TRUSTED_PYTHON3" -B -W error::ResourceWarning \
  portable_tests.py ) >"$_MT_OUT" 2>"$_MT_ERR"; _mt_rc=$?
if [ "$_mt_rc" -ne 0 ]; then
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused tests failed (exit $_mt_rc)"; die "focused tests"
fi
tail -3 "$_MT_OUT" | sed 's/^/    /'
gate_require_clean_stderr "$_MT_ERR" "focused tests" || {
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    die "focused tests stderr"; }
_EXPECT_N=$("$TRUSTED_PYTHON3" -B -c 'import sys
with open(sys.argv[1]) as h:
    sys.stdout.write(h.read().strip())' "$P/EXPECTED_TEST_COUNT.txt")
grep -q "^Ran ${_EXPECT_N} tests" "$_MT_OUT" || {
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused test count is not the pinned ${_EXPECT_N}"
    die "focused count"; }
grep -q "^OK$" "$_MT_OUT" || {
    gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
    bad "focused stdout lacks the final OK line"; die "focused OK"; }
for _bad_marker in "FAILED" "errors=" "failures=" "skipped="; do
    if grep -q "$_bad_marker" "$_MT_OUT"; then
        gate_dump_focused_failure "$_MT_OUT" "$_MT_ERR" "$_mt_rc"
        bad "focused stdout contains forbidden marker: $_bad_marker"
        die "focused forbidden marker"
    fi
done
ok "focused suite PASS (no skips, exact count, stderr empty)"

# =========================================================================
# STAGE J -- complete unchanged Move 81 regression from an extracted copy.
# =========================================================================
echo ""
echo "STAGE J: complete Move 81 adoption/regression child gate"
_M81_EXTRACT=$("$TRUSTED_MKTEMP" -d) || die "could not create extraction dir"
gate_track_tmp "$_M81_EXTRACT"
_M81_XOUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M81_XOUT"
_M81_XERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M81_XERR"
"$TRUSTED_PYTHON3" -B "$P/check_move82_inherited.py" \
    --baseline-zip "$M81_ZIP" --expect-sha256 "$_M81_EXPECT" \
    --extract-to "$_M81_EXTRACT" >"$_M81_XOUT" 2>"$_M81_XERR"
_m81_x_rc=$?
echo "---- BEGIN REAL_MOVE81 VALIDATED EXTRACTION EVIDENCE ----"
cat "$_M81_XOUT"
echo "---- END REAL_MOVE81 VALIDATED EXTRACTION EVIDENCE ----"
if [ -s "$_M81_XERR" ]; then
    sed 's/^/    /' "$_M81_XERR"
    bad "baseline extraction emitted stderr"; die "move81 extraction"
fi
[ "$_m81_x_rc" -eq 0 ] || die "REAL_MOVE81 could not be safely extracted"
_M81_ROOT="$_M81_EXTRACT/project-witness-main"
[ -f "$_M81_ROOT/tools/check_move81_structured_verdict_adoption.sh" ] \
    || die "extracted Move 81 root is not a complete Move 81 tree"
ok "REAL_MOVE81 extracted to a private gate-owned directory"

_M81_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M81_OUT"
_M81_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_M81_ERR"
( cd "$_M81_ROOT" \
  && REAL_MOVE78="$REAL_MOVE78" REAL_705="$REAL_705" \
     REAL_MOVE79="$REAL_MOVE79" REAL_MOVE80="$REAL_MOVE80" \
     REAL_V20="${REAL_V20:-}" LD_PRELOAD="$GATE_PRELOAD" \
     "$TRUSTED_SH" tools/check_move81_structured_verdict_adoption.sh \
) >"$_M81_OUT" 2>"$_M81_ERR"; _m81_rc=$?
echo "---- BEGIN COMPLETE MOVE 81 CHILD GATE STDOUT (retained) ----"
cat "$_M81_OUT"
echo "---- END COMPLETE MOVE 81 CHILD GATE STDOUT ----"
echo "---- BEGIN COMPLETE MOVE 81 CHILD GATE STDERR (retained) ----"
cat "$_M81_ERR"
echo "---- END COMPLETE MOVE 81 CHILD GATE STDERR ----"
# Merging the streams could not prove stderr was empty, so they are kept
# apart and the stderr is required to be byte-empty.
if [ -s "$_M81_ERR" ]; then
    bad "Move 81 child gate emitted stderr"
    die "move81 child stderr"
fi
if [ "$_m81_rc" -ne 0 ]; then
    bad "Move 81 child adoption gate failed (exit $_m81_rc)"
    die "move81 regression"
fi
for _need in \
    "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: PASS" \
    "MOVE_80_REGRESSION_GATE: PASS" \
    "SYSTEM_AGREEMENT_RESULT: FAIL" \
    "SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED"; do
    if ! grep -qF "$_need" "$_M81_OUT"; then
        bad "Move 81 child gate missing expected marker: $_need"
        die "move81 markers"
    fi
done
ok "Move 81 child gate PASS (two adopted divergences remain visible)"
rm -rf "$_M81_EXTRACT"
MOVE_81_REGRESSION=PASS

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
echo "PUBLICATION: placing final artefacts in MOVE82_OUTPUT_DIR"
_PUB_OUT=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_PUB_OUT"
_PUB_ERR=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_PUB_ERR"
"$TRUSTED_PYTHON3" -B "$P/provenance.py" \
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
echo "MOVE_82_CANDIDATE_IDENTITY: $CANDIDATE_IDENTITY"
echo "MOVE_82_BASELINE_IMMUTABILITY: $BASELINE_IMMUTABILITY"
echo "MOVE_82_TARGET_DETECTION: $TARGET_DETECTION"
echo "MOVE_82_CLEAN_RELEASE_BUILD: $CLEAN_RELEASE_BUILD"
echo "MOVE_82_BINARY_INSPECTION: $BINARY_INSPECTION"
echo "MOVE_82_STANDALONE_EXECUTION: $STANDALONE_EXECUTION"
echo "MOVE_82_CONTROLLED_BEHAVIOUR: $CONTROLLED_BEHAVIOUR"
echo "MOVE_82_DEBUG_RELEASE_EQUIVALENCE: $DEBUG_RELEASE_EQUIVALENCE"
echo "MOVE_82_PROVENANCE: $PROVENANCE"
echo "MOVE_81_REGRESSION_GATE: $MOVE_81_REGRESSION"
echo "SYSTEM_AGREEMENT_RESULT: FAIL"
echo "SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED"
echo "MOVE_82_TARGET_ANDROID_TERMUX_AARCH64: NATIVE_BUILD_AND_RUNTIME_TEST_PRACTICAL"
echo "MOVE_82_TARGET_LINUX_X86_64: NOT_CURRENTLY_ESTABLISHABLE"
echo "MOVE_82_TARGET_LINUX_AARCH64: NOT_CURRENTLY_ESTABLISHABLE"
echo "MOVE_82_TARGET_WINDOWS_X86_64: NOT_CURRENTLY_ESTABLISHABLE"
echo "MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: PASS"
echo "exit_code: 0"
exit 0
