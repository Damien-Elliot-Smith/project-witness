# gate_bootstrap.sh — trusted execution bootstrap for the Move 79 adoption gate.
#
# v15: the gate establishes a TRUSTED execution environment BEFORE any
# preflight, self-test, or provenance check, so a fake python3/sh/cargo/rustc
# on the caller's PATH — or a caller-created PREFIX — cannot fabricate results.
#
# Trust root is a LITERAL internal constant, never the inherited PREFIX:
#   /data/data/com.termux/files/usr
# The named production gate resolves its critical commands only from beneath
# that literal prefix, sanitizes interpreter/build environment variables,
# replaces PATH with a minimal trusted PATH, and uses absolute trusted command
# paths thereafter. A caller-created fake prefix is rejected.
#
# Requires nothing else sourced first. Sets, on success, for each critical
# command: TRUSTED_<CMD> (the applet ENTRYPOINT — the value everything INVOKES)
# and TRUSTED_<CMD>_REAL (the canonical target, used ONLY for validation).
# On Termux the entrypoints are symlinks into the coreutils multicall binary,
# so TRUSTED_<CMD> and TRUSTED_<CMD>_REAL differ and only the entrypoint keeps
# the applet identity (argv[0]); the canonical target is never invoked. Also
# sets GATE_CARGO_HOME and a trusted PATH.

TRUSTED_TERMUX_PREFIX=/data/data/com.termux/files/usr
GATE_TRUSTED_PATH="$TRUSTED_TERMUX_PREFIX/bin:/system/bin"
GATE_CRITICAL_CMDS="sh python3 cargo rustc timeout readlink sha256sum mktemp"
REQUIRED_CARGO_VERSION=1.96.0
REQUIRED_RUSTC_VERSION=1.96.0

# ---- temp tracking + cleanup + real signal handling (B3) ----
GATE_TMP_ITEMS=""
GATE_CHILD_PID=""
gate_track_tmp() { GATE_TMP_ITEMS="$GATE_TMP_ITEMS $1"; }
gate_cleanup() {
    for _gc in $GATE_TMP_ITEMS; do
        [ -n "$_gc" ] && rm -rf "$_gc" 2>/dev/null
    done
    GATE_TMP_ITEMS=""
}

# gate_on_signal -> clean up AND terminate immediately. It first clears the
# traps (so the EXIT trap does not recurse), terminates any active measurement
# child (which, being exec'd, is the real process), removes every tracked temp,
# and exits nonzero. An interruption therefore cannot continue into the next
# measurement.
gate_on_signal() {
    trap - EXIT HUP INT TERM
    if [ -n "${GATE_CHILD_PID:-}" ]; then
        kill -TERM "$GATE_CHILD_PID" 2>/dev/null || true
    fi
    gate_cleanup
    exit 1
}

# gate_install_traps -> a dedicated EXIT cleanup trap plus HUP/INT/TERM handlers
# that clean and terminate. Call once, immediately after a successful bootstrap.
gate_install_traps() {
    trap 'gate_cleanup' EXIT
    trap 'gate_on_signal' HUP INT TERM
}

gate_sanitize_env() {
    unset PYTHONPATH PYTHONHOME PYTHONSTARTUP LD_PRELOAD LD_LIBRARY_PATH \
          ENV BASH_ENV CARGO CARGO_HOME RUSTC RUSTC_WRAPPER \
          RUSTC_WORKSPACE_WRAPPER RUSTFLAGS CARGO_ENCODED_RUSTFLAGS \
          CARGO_BUILD_RUSTC CARGO_BUILD_RUSTC_WRAPPER CARGO_TARGET_DIR \
          2>/dev/null || true
}

# gate_validate_preload PREFIX READLINK VALUE -> validate the inherited
# LD_PRELOAD. Termux relies on its legitimate libtermux-exec.so preload for
# nested process execution, so the gate must PRESERVE that one library while
# still rejecting anything else. On success sets GATE_PRELOAD to the exact
# validated value (empty if none) and returns 0; returns 1 on any illegitimate
# value. VALUE is passed explicitly (production passes the inherited LD_PRELOAD)
# so this is testable without polluting the test process's own loader.
gate_validate_preload() {
    _vp_pfx=$1; _vp_rl=$2; _vp_val=$3; _vp_require=${4:-0}
    _vp_expected="$_vp_pfx/lib/libtermux-exec.so"
    GATE_PRELOAD_FAIL=""
    if [ -z "$_vp_val" ]; then
        if [ "$_vp_require" = 1 ]; then
            echo "TERMUX_EXEC_PRELOAD_CHECK: FAIL"
            echo "no inherited Termux exec preload (libtermux-exec.so required)" >&2
            GATE_PRELOAD_FAIL="missing"; return 1
        fi
        GATE_PRELOAD=""; return 0
    fi
    # exactly ONE entry (reject space/colon/semicolon-separated extras)
    case "$_vp_val" in
        *" "*|*"	"*|*:*|*\;*)
            echo "TERMUX_EXEC_PRELOAD_CHECK: FAIL"
            echo "LD_PRELOAD has multiple/extra entries: $_vp_val" >&2
            GATE_PRELOAD_FAIL="invalid"; return 1 ;;
    esac
    case "$_vp_val" in
        /*) : ;;
        *) echo "TERMUX_EXEC_PRELOAD_CHECK: FAIL"
           echo "LD_PRELOAD is not an absolute path: $_vp_val" >&2
           GATE_PRELOAD_FAIL="invalid"; return 1 ;;
    esac
    if [ "$_vp_val" != "$_vp_expected" ]; then
        echo "TERMUX_EXEC_PRELOAD_CHECK: FAIL"
        echo "LD_PRELOAD is not the legitimate Termux exec preload ($_vp_expected): $_vp_val" >&2
        GATE_PRELOAD_FAIL="invalid"; return 1
    fi
    _vp_real=$("$_vp_rl" -f "$_vp_val" 2>/dev/null) || _vp_real=""
    if [ -z "$_vp_real" ]; then
        echo "TERMUX_EXEC_PRELOAD_CHECK: FAIL"
        echo "LD_PRELOAD canonical target missing/broken: $_vp_val" >&2
        GATE_PRELOAD_FAIL="invalid"; return 1
    fi
    case "$_vp_real" in
        "$_vp_pfx/lib/"*) : ;;
        *) echo "TERMUX_EXEC_PRELOAD_CHECK: FAIL"
           echo "LD_PRELOAD canonical target escapes $_vp_pfx/lib: $_vp_real" >&2
           GATE_PRELOAD_FAIL="invalid"; return 1 ;;
    esac
    if [ ! -f "$_vp_real" ] || [ ! -r "$_vp_real" ]; then
        echo "TERMUX_EXEC_PRELOAD_CHECK: FAIL"
        echo "LD_PRELOAD target is not a readable regular file: $_vp_real" >&2
        GATE_PRELOAD_FAIL="invalid"; return 1
    fi
    GATE_PRELOAD="$_vp_val"
    return 0
}

# gate_nested_exec_probe -> after bootstrap and before the preflights, prove the
# sanitised trusted environment can actually nest processes (the Termux
# libtermux-exec preload must survive). Uses the trusted Python/sh entrypoints
# and the same sanitised env the test suites will receive. Any PermissionError/
# EACCES/traceback/stderr/nonzero exit -> return 1.
gate_nested_exec_probe() {
    _ne_err=$("$TRUSTED_MKTEMP") || return 1
    gate_track_tmp "$_ne_err"
    _ne_out=$(TRUSTED_PYTHON3="$TRUSTED_PYTHON3" TRUSTED_SH="$TRUSTED_SH" \
        TRUSTED_TIMEOUT="$TRUSTED_TIMEOUT" TRUSTED_READLINK="$TRUSTED_READLINK" \
        "$TRUSTED_PYTHON3" -B - 2>"$_ne_err" <<'PY'
import os, subprocess
PY3 = os.environ["TRUSTED_PYTHON3"]; SH = os.environ["TRUSTED_SH"]
TO = os.environ["TRUSTED_TIMEOUT"]; RL = os.environ["TRUSTED_READLINK"]
# 1. trusted Python launches trusted Python --version
subprocess.run([PY3, "--version"], check=True, capture_output=True)
# 2. trusted Python launches trusted sh -c 'echo NESTED_SH_OK'
r = subprocess.run([SH, "-c", "echo NESTED_SH_OK"], check=True,
                   capture_output=True, text=True)
assert r.stdout.strip() == "NESTED_SH_OK", r.stdout
# 3. trusted sh launches trusted Python --version
subprocess.run([SH, "-c", '"$0" --version', PY3], check=True,
               capture_output=True)
# 4. a second-level Python subprocess launches another trusted process
code = ("import os,subprocess;"
        "subprocess.run([os.environ['TRUSTED_SH'],'-c','echo L2_OK'],"
        "check=True,capture_output=True)")
subprocess.run([PY3, "-c", code], check=True, capture_output=True)
# 5. the trusted TIMEOUT entrypoint launches a trusted child (production relies
#    on timeout for the measurements). Require exit 0, exact stdout, no stderr.
t = subprocess.run([TO, "30", SH, "-c", "echo TIMEOUT_CHILD_OK"],
                   capture_output=True, text=True)
assert t.returncode == 0, "timeout rc=%d stderr=%r" % (t.returncode, t.stderr)
assert t.stdout.strip() == "TIMEOUT_CHILD_OK", "timeout stdout=%r" % t.stdout
assert t.stderr == "", "timeout stderr=%r" % t.stderr
print("NESTED_OK")
PY
    )
    _ne_rc=$?
    if [ "$_ne_rc" -ne 0 ] || [ -s "$_ne_err" ] || [ "$_ne_out" != "NESTED_OK" ]; then
        echo "nested trusted execution failed (rc $_ne_rc)" >&2
        [ -s "$_ne_err" ] && head -c 400 "$_ne_err" | sed 's/^/      | /' >&2
        rm -f "$_ne_err"; return 1
    fi
    rm -f "$_ne_err"
    return 0
}

# _gate_resolve_from PREFIX -> resolves every critical command from beneath
# PREFIX with the prefix's own readlink, requiring each resolved path to stay
# beneath the prefix, and requires cargo/rustc versions. Sets TRUSTED_* and a
# single CARGO_HOME. Returns 0 on success, 3 if the toolchain is simply absent,
# 1 if present-but-untrusted. Shared by the production bootstrap (literal
# prefix) and the TEST-ONLY resolver (controlled prefix).
_gate_resolve_from() {
    _rf_pfx=$1
    _rf_preload=${2-}
    _rf_require=${3:-0}
    # Missing-preload classification with shell BUILT-INS ONLY, before any
    # external command. On real Termux a genuinely missing libtermux-exec.so
    # preload would prevent even the trusted readlink from executing (EACCES),
    # so this MUST be decided before the command-resolution loop runs anything.
    if [ "$_rf_require" = 1 ] && [ -z "$_rf_preload" ]; then
        echo "TERMUX_EXEC_PRELOAD_CHECK: FAIL"
        echo "no inherited Termux exec preload (libtermux-exec.so required)" >&2
        GATE_PRELOAD_FAIL="missing"
        return 1
    fi
    if [ ! -d "$_rf_pfx" ]; then
        echo "trusted prefix $_rf_pfx not present" >&2; return 3
    fi
    _rf_rl="$_rf_pfx/bin/readlink"
    [ -x "$_rf_rl" ] || { echo "trusted readlink missing under $_rf_pfx" >&2; return 3; }
    _rf_root=$("$_rf_rl" -f "$_rf_pfx") || return 1
    for _rf_c in $GATE_CRITICAL_CMDS; do
        # ENTRYPOINT — the literal applet path we INVOKE. On Termux this is a
        # symlink into the coreutils multicall binary; invoking it preserves the
        # applet identity (argv[0] basename), so `mktemp -d` stays `mktemp -d`.
        _rf_p="$_rf_pfx/bin/$_rf_c"
        if [ ! -x "$_rf_p" ]; then
            echo "trusted $_rf_c entrypoint missing at $_rf_p" >&2
            return 3
        fi
        # CANONICAL TARGET — used ONLY to validate provenance/containment. For a
        # coreutils applet this resolves to .../bin/coreutils; we must NOT invoke
        # it directly (that would lose the applet identity: `coreutils -d`).
        _rf_r=$("$_rf_rl" -f "$_rf_p") || return 1
        if [ -z "$_rf_r" ] || [ ! -x "$_rf_r" ]; then
            echo "trusted $_rf_c canonical target missing/broken: $_rf_r" >&2
            return 1
        fi
        case "$_rf_r" in
            "$_rf_root"/*) : ;;
            *) echo "$_rf_c canonical target escapes the trusted prefix: $_rf_r" >&2
               return 1 ;;
        esac
        # Store the ENTRYPOINT for invocation and the canonical target for the
        # record. Never exchange them; never invoke the *_REAL value.
        case "$_rf_c" in
            sh)        TRUSTED_SH=$_rf_p;        TRUSTED_SH_REAL=$_rf_r ;;
            python3)   TRUSTED_PYTHON3=$_rf_p;   TRUSTED_PYTHON3_REAL=$_rf_r ;;
            cargo)     TRUSTED_CARGO=$_rf_p;     TRUSTED_CARGO_REAL=$_rf_r ;;
            rustc)     TRUSTED_RUSTC=$_rf_p;     TRUSTED_RUSTC_REAL=$_rf_r ;;
            timeout)   TRUSTED_TIMEOUT=$_rf_p;   TRUSTED_TIMEOUT_REAL=$_rf_r ;;
            readlink)  TRUSTED_READLINK=$_rf_p;  TRUSTED_READLINK_REAL=$_rf_r ;;
            sha256sum) TRUSTED_SHA256SUM=$_rf_p; TRUSTED_SHA256SUM_REAL=$_rf_r ;;
            mktemp)    TRUSTED_MKTEMP=$_rf_p;    TRUSTED_MKTEMP_REAL=$_rf_r ;;
            *) echo "unexpected critical command $_rf_c" >&2; return 1 ;;
        esac
    done
    _rf_cv=$("$TRUSTED_CARGO" --version 2>/dev/null); set -- $_rf_cv
    if [ "${1:-}" != cargo ] || [ "${2:-}" != "$REQUIRED_CARGO_VERSION" ]; then
        echo "cargo version '$_rf_cv' != cargo $REQUIRED_CARGO_VERSION" >&2; return 1
    fi
    _rf_rv=$("$TRUSTED_RUSTC" --version 2>/dev/null); set -- $_rf_rv
    if [ "${1:-}" != rustc ] || [ "${2:-}" != "$REQUIRED_RUSTC_VERSION" ]; then
        echo "rustc version '$_rf_rv' != rustc $REQUIRED_RUSTC_VERSION" >&2; return 1
    fi
    # Validate the inherited LD_PRELOAD (legitimate Termux exec preload only)
    # BEFORE sanitising, so we can preserve exactly that library for children.
    gate_validate_preload "$_rf_pfx" "$_rf_rl" "$_rf_preload" "$_rf_require" || return 1
    gate_sanitize_env
    # Restore ONLY the validated Termux exec preload; LD_LIBRARY_PATH stays unset.
    if [ -n "${GATE_PRELOAD:-}" ]; then
        export LD_PRELOAD="$GATE_PRELOAD"
    fi
    export PATH="$_rf_root/bin:/system/bin"
    export RUSTC="$TRUSTED_RUSTC"
    GATE_CARGO_HOME=$("$TRUSTED_MKTEMP" -d) || return 1
    gate_track_tmp "$GATE_CARGO_HOME"
    export CARGO_HOME="$GATE_CARGO_HOME"
    return 0
}

# gate_bootstrap PRELOAD -> PRODUCTION. Trust root is the LITERAL prefix only.
# PRELOAD is the LD_PRELOAD value captured by the named gate BEFORE it unset any
# loader variable; the production bootstrap REQUIRES the legitimate Termux exec
# preload. A caller-created PREFIX that differs from the literal is rejected.
# Returns 0 (trusted), 3 (toolchain absent -> INCONCLUSIVE), or 1 (untrusted;
# GATE_PRELOAD_FAIL is set to missing/invalid for a preload-specific failure).
gate_bootstrap() {
    _gb_preload=${1-}
    if [ -n "${PREFIX+x}" ] && [ "$PREFIX" != "$TRUSTED_TERMUX_PREFIX" ]; then
        echo "inherited PREFIX ('$PREFIX') != trusted $TRUSTED_TERMUX_PREFIX" >&2
        return 1
    fi
    # Classify a missing preload with shell BUILT-INS ONLY, before any external
    # command: on real Termux the very readlink used downstream cannot execute
    # without libtermux-exec.so, so the decision must precede _gate_resolve_from.
    if [ -z "$_gb_preload" ]; then
        echo "TERMUX_EXEC_PRELOAD_CHECK: FAIL"
        echo "no inherited Termux exec preload (libtermux-exec.so required)" >&2
        GATE_PRELOAD_FAIL="missing"
        return 1
    fi
    _gate_resolve_from "$TRUSTED_TERMUX_PREFIX" "$_gb_preload" 1
}

# _gate_test_resolve_prefix PREFIX [PRELOAD] -> TEST-ONLY. Resolves a controlled
# prefix so isolated helper tests and the controlled full-gate fixture can
# exercise resolution without a real Termux toolchain. Preload is OPTIONAL here
# (no-preload mode is for generic desktop fixtures); production REQUIRES it. The
# named production gate NEVER calls this.
_gate_test_resolve_prefix() {
    _gate_resolve_from "$1" "${2-}" 0
}
