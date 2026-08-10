#!/bin/sh
# Move 79 INSTRUMENT ADOPTION GATE.
#
# TWO AXES, never conflated:
#   MOVE_79_INSTRUMENT_ADOPTION_GATE — did the instrument correctly and
#       reproducibly MEASURE the systems?
#   SYSTEM_AGREEMENT_RESULT — do Python and Rust actually AGREE?
#
# v15 — TRUSTED EXECUTION BOUNDARY FIRST:
#   Before ANY preflight, self-test, or provenance check, the gate bootstraps a
#   trusted execution environment from a LITERAL Termux prefix
#   (/data/data/com.termux/files/usr), resolving sh/python3/cargo/rustc/timeout/
#   readlink/sha256sum/mktemp only from beneath it, sanitizing interpreter and
#   build environment variables, and replacing PATH with a minimal trusted PATH.
#   A caller-created PREFIX that differs from the literal is REJECTED. This
#   prevents a fake python3/sh/cargo/rustc from fabricating any stage. Trust is
#   never derived from the inherited PREFIX or PATH.
#
#   The toolchain is resolved ONCE, at bootstrap; one fresh CARGO_HOME is
#   created and a trap removes every temp on PASS/FAIL/INCONCLUSIVE/timeout/
#   interrupt. Every measurement process must produce ZERO stderr bytes. The
#   decisive orchestration is tools/gate_flow.sh (gate_run_flow); the reviewed
#   harness path is fixed, never taken from FLOW_H.
#
# Required inputs (user-supplied; not bundled, never searched for):
#   REAL_MOVE78=<adopted Move 78 v10 zip>   (mandatory; provenance baseline)
#   REAL_705=<Move 70.5 zip>                (mandatory; measurement corpus)
#   REAL_V20=<path>                         (optional; defaults to in-repo v20)
set -u
export PYTHONDONTWRITEBYTECODE=1

# (0a) CAPTURE the inherited LD_PRELOAD FIRST, with a shell assignment only —
#      before unsetting anything and before running any external binary. Termux
#      needs its legitimate libtermux-exec.so preload for nested exec; it is
#      validated (below) after the trusted readlink exists, then restored. The
#      captured value is not executed, expanded as a command, split, or
#      normalised before trusted bootstrap.
GATE_INHERITED_LD_PRELOAD=${LD_PRELOAD-}
readonly GATE_INHERITED_LD_PRELOAD

# (0b) Sanitize dangerous inherited environment with shell BUILT-INS, before
#      invoking even the literal trusted readlink (LD_PRELOAD/LD_LIBRARY_PATH
#      could otherwise hijack an absolute binary).
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP LD_PRELOAD LD_LIBRARY_PATH ENV \
      BASH_ENV CDPATH CARGO CARGO_HOME RUSTC RUSTC_WRAPPER \
      RUSTC_WORKSPACE_WRAPPER RUSTFLAGS CARGO_ENCODED_RUSTFLAGS \
      CARGO_BUILD_RUSTC CARGO_BUILD_RUSTC_WRAPPER CARGO_TARGET_DIR \
      2>/dev/null || true

# (1) Argument validation — a pure built-in check, no external command, no
#     sourcing. USAGE precedes trust establishment because it needs neither.
if [ -z "${REAL_MOVE78:-}" ] || [ -z "${REAL_705:-}" ]; then
    _missing=""
    [ -z "${REAL_MOVE78:-}" ] && _missing="$_missing REAL_MOVE78"
    [ -z "${REAL_705:-}" ]    && _missing="$_missing REAL_705"
    echo "Required input(s) not supplied:$_missing"
    echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: USAGE (missing:$_missing)"
    exit 2
fi

# (1b) MISSING-PRELOAD REJECTION with shell BUILT-INS ONLY, before invoking any
#      external command. On a genuine Termux host (literal prefix present) the
#      libtermux-exec.so preload is mandatory: without it the very readlink used
#      to canonicalise $0 below cannot execute, so the decision must be made here
#      with the [ builtin. Off Termux (literal prefix absent) we skip this and
#      fall through to canonicalisation, which yields INCONCLUSIVE.
if [ -d /data/data/com.termux/files/usr ] && [ -z "$GATE_INHERITED_LD_PRELOAD" ]; then
    echo "the legitimate Termux exec preload (libtermux-exec.so) is absent."
    echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (missing Termux exec preload)"
    exit 1
fi

# (2) v17-B1: CANONICALISE THE SCRIPT TARGET before sourcing any module. A
#     symlink alias to this gate inside an attacker tree would leave textual
#     $0 pointing at fake adjacent modules; cd -P resolves directory symlinks
#     but NOT the script file named by $0. So resolve $0 itself with the
#     LITERAL trusted Termux readlink and require the real path to be exactly
#     .../tools/check_move79_instrument_adoption.sh, then derive ROOT from it —
#     never from textual $0, and never from a caller-supplied override.
_TRUSTED_READLINK=/data/data/com.termux/files/usr/bin/readlink
if [ ! -x "$_TRUSTED_READLINK" ]; then
    echo "trusted readlink absent at $_TRUSTED_READLINK (this gate runs only on Termux)"
    echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
    exit 3
fi
SCRIPT_REAL=$("$_TRUSTED_READLINK" -f -- "$0") || SCRIPT_REAL=""
case "$SCRIPT_REAL" in
    */tools/check_move79_instrument_adoption.sh) : ;;
    *)
        echo "refusing: canonical script path is not the genuine named gate ($SCRIPT_REAL)"
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (untrusted script path)"
        exit 1 ;;
esac
if [ ! -f "$SCRIPT_REAL" ]; then
    echo "refusing: canonical script target is not a regular file"
    echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (untrusted script path)"
    exit 1
fi
_SCRIPT_DIR=${SCRIPT_REAL%/*}   # <root>/tools
ROOT=${_SCRIPT_DIR%/*}          # <root>
cd "$ROOT" || exit 2

# (3) Source ONLY the bootstrap, from the canonical ROOT, before trust exists.
. "$ROOT/tools/gate_bootstrap.sh"
H="verify/agreement_harness_v01"
fail=0
ok(){ printf "  OK    %s\n" "$1"; }
bad(){ printf "  FAIL  %s\n" "$1"; fail=1; }

export EXPECT_TOTAL=85 EXPECT_AGREE=74 EXPECT_PY_ONLY=6 EXPECT_RS_ONLY=3 EXPECT_DIV=2
export EXPECT_DIV_IDS="stage_manifest_json_invalid stage_report_field_missing_repaired"

echo "==========================================================="
echo " MOVE 79 INSTRUMENT ADOPTION GATE"
echo "==========================================================="

# (2) TRUSTED BOOTSTRAP — must precede every preflight and provenance check.
echo ""
echo "BOOTSTRAP: establishing the trusted execution environment"
gate_bootstrap "$GATE_INHERITED_LD_PRELOAD"
BOOT_RC=$?
if [ "$BOOT_RC" -eq 3 ]; then
    echo "  trusted Termux toolchain is not present on this host."
    echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
    exit 3
elif [ "$BOOT_RC" -ne 0 ]; then
    if [ "${GATE_PRELOAD_FAIL:-}" = missing ]; then
        echo "  the legitimate Termux exec preload (libtermux-exec.so) is absent."
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (missing Termux exec preload)"
    elif [ "${GATE_PRELOAD_FAIL:-}" = invalid ]; then
        echo "  the inherited LD_PRELOAD is not the sole legitimate Termux exec preload."
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (untrusted Termux exec preload)"
    else
        echo "  refusing to run in an untrusted environment."
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (untrusted environment)"
    fi
    exit 1
fi
# B3: dedicated EXIT cleanup + HUP/INT/TERM handlers that clean and terminate.
gate_install_traps
# B4: only now, with trust established, source the rest from canonical ROOT.
. "$ROOT/tools/gate_lib.sh"
. "$ROOT/tools/gate_flow.sh"
ok "trusted environment established (cargo/rustc $REQUIRED_CARGO_VERSION under $TRUSTED_TERMUX_PREFIX)"

# (2) NESTED EXECUTION — prove the sanitised trusted environment can actually
# nest processes (the legitimate Termux libtermux-exec preload must survive).
# Runs before the test suites, which are subprocess-heavy.
echo ""
echo "NESTED EXEC: verifying trusted nested process execution"
if gate_nested_exec_probe; then
    echo "TERMUX_NESTED_EXEC_CHECK: PASS"
else
    echo "TERMUX_NESTED_EXEC_CHECK: FAIL"
    echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (nested exec)"
    exit 1
fi

# (2) Preflights — run with ABSOLUTE trusted interpreters (B4).
echo ""
echo "PREFLIGHT (1/7) package hygiene, before:"
"$TRUSTED_SH" tools/check_package_hygiene.sh >/dev/null 2>&1 \
    && ok "repository cache-clean" || bad "repository not clean before run"

echo "PREFLIGHT (2/7) harness self-tests (strict, warning-clean) [UNCONDITIONAL]:"
ST=$("$TRUSTED_PYTHON3" -B -W error::ResourceWarning "$H/self_tests.py" 2>&1); ST_RC=$?
if [ "$ST_RC" -ne 0 ]; then
    bad "harness self-tests FAILED (exit $ST_RC)"; printf '%s\n' "$ST" | tail -12
elif gate_output_has_warnings "$ST"; then
    bad "self-tests emitted warnings (exit 0 is NOT proof)"
else
    ok "self-tests pass, warning-clean ($(printf '%s' "$ST" | grep -oE 'Ran [0-9]+ tests' | head -1))"
fi

echo "PREFLIGHT (3/7) adoption-gate unit tests (strict, warning-clean) [UNCONDITIONAL]:"
GUT=$("$TRUSTED_PYTHON3" -B -W error::ResourceWarning "$H/gate_unit_tests.py" 2>&1); GUT_RC=$?
if [ "$GUT_RC" -ne 0 ]; then
    bad "gate unit tests FAILED (exit $GUT_RC)"; printf '%s\n' "$GUT" | tail -12
elif gate_output_has_warnings "$GUT"; then
    bad "gate unit tests emitted warnings (exit 0 is NOT proof)"
else
    ok "gate unit tests pass, warning-clean ($(printf '%s' "$GUT" | grep -oE 'Ran [0-9]+ tests' | head -1))"
fi

echo "PREFLIGHT (4/7) adopted artifacts immutable:"
"$TRUSTED_SH" tools/check_adopted_immutable.sh >/dev/null 2>&1 \
    && ok "adopted history byte-identical" || bad "ADOPTED HISTORY MUTATED"

echo "PREFLIGHT (5/7) source matches declared release:"
"$TRUSTED_SH" tools/check_src_matches_release.sh >/dev/null 2>&1 \
    && ok "src matches declared release" || bad "src does not match release"

echo "PREFLIGHT (6/7) current release state:"
"$TRUSTED_SH" tools/check_current_release_state.sh >/dev/null 2>&1 \
    && ok "release state consistent" || bad "release state inconsistent"

# (B6) Full package-hygiene gate AFTER the preflight stages, before provenance
# or any Cargo execution — require its exact PASS marker and exit 0.
echo "PREFLIGHT (7/7) package hygiene, after preflights [REQUIRED]:"
PH=$("$TRUSTED_SH" tools/check_package_hygiene.sh 2>&1); PH_RC=$?
if [ "$PH_RC" -eq 0 ] && printf '%s\n' "$PH" | grep -qx 'PACKAGE_HYGIENE_CHECK: PASS'; then
    ok "package hygiene PASS (exact marker + exit 0)"
else
    bad "post-preflight package hygiene did not PASS (exit $PH_RC)"
fi

if [ "$fail" -ne 0 ]; then
    echo ""
    echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (preflight)"
    exit 1
fi

# (3) Decisive path: provenance -> workspace -> clean build -> three
# stderr-checked measurements -> decision (same code the controlled fixture
# drives; seams are NOT redefined here).
gate_run_flow
exit $?
