# gate_lib.sh — Move 79 adoption-gate decision helpers (POSIX sh).
#
# Sourced by tools/check_move79_instrument_adoption.sh and tools/gate_flow.sh,
# and exercised directly by verify/agreement_harness_v01/gate_unit_tests.py.
#
# v14 (B1): the production toolchain is resolved from a CANONICAL trusted
# location ($PREFIX/bin on Termux), never from caller PATH. Symlinks are
# resolved with readlink -f and required to stay beneath the prefix; exact
# versions are required; build-affecting environment variables are sanitized
# and a fresh empty CARGO_HOME is used. There is no command -v cargo fallback.
#
# v14 (B2): gate_measurement_stderr_clean requires a measurement process to
# have produced ZERO bytes of stderr; any stderr is an instrument failure.
# The trusted toolchain (and version pinning) is established by gate_bootstrap.

# ---- workspace marker/warning classification ---------------------------

classify_workspace_marker() {
    _cwm_out=$1; _cwm_rc=$2; _cwm_pass=0; _cwm_unavail=0
    if printf '%s\n' "$_cwm_out" | grep -qx 'RUST_WORKSPACE_CHECK: PASS'; then
        _cwm_pass=1
    fi
    if printf '%s\n' "$_cwm_out" \
        | grep -qx 'RUST_WORKSPACE_CHECK: INCONCLUSIVE_TOOLCHAIN_UNAVAILABLE'
    then
        _cwm_unavail=1
    fi
    if [ "$_cwm_pass" -eq 1 ] && [ "$_cwm_unavail" -eq 1 ]; then echo FAIL; return 0; fi
    if [ "$_cwm_pass" -eq 1 ]; then
        if [ "$_cwm_rc" -eq 0 ]; then echo PASS; else echo FAIL; fi; return 0
    fi
    if [ "$_cwm_unavail" -eq 1 ]; then
        if [ "$_cwm_rc" -eq 3 ]; then echo UNAVAIL; else echo FAIL; fi; return 0
    fi
    echo FAIL
}

gate_output_has_warnings() {
    printf '%s\n' "$1" \
        | grep -qE 'ResourceWarning|Exception ignored in:|unclosed file|Traceback \(most recent call last\)'
}

classify_workspace_result() {
    if gate_output_has_warnings "$1"; then echo FAIL; return 0; fi
    classify_workspace_marker "$1" "$2"
}

# ---- B2: measurement stderr must be empty -------------------------------

# gate_measurement_stderr_clean ERRF -> 0 if the file is exactly zero bytes,
# else 1 (prints a bounded excerpt). Any stderr from a measurement process
# (a ResourceWarning, a post-report traceback, anything) is an instrument
# failure and must never be mistaken for expected system disagreement.
gate_measurement_stderr_clean() {
    _errf=$1
    if [ ! -f "$_errf" ]; then
        echo "stderr capture file missing: $_errf" >&2; return 1
    fi
    if [ -s "$_errf" ]; then
        echo "measurement produced stderr (instrument failure); first 400 bytes:" >&2
        head -c 400 "$_errf" | sed 's/^/      | /' >&2
        return 1
    fi
    return 0
}

# ---- target sequence (B3 from earlier rounds) ---------------------------

gate_assert_no_target() {
    if [ -e rust/target ]; then
        echo "rust/target already exists before any cargo execution" >&2; return 1
    fi
    return 0
}

gate_clean_target() {
    rm -rf rust/target
    if [ -e rust/target ]; then
        echo "rust/target could not be removed" >&2; return 1
    fi
    return 0
}

# ---- build (toolchain is resolved ONCE by gate_bootstrap) ---------------

# _gate_build_with CARGO_EXE -> build and require exactly the one executable.
_gate_build_with() {
    _gbw_cargo=$1; _gbw_bin="rust/target/debug/witness-verify"
    if ! ( cd rust && "$_gbw_cargo" build -q ); then
        echo "cargo build failed" >&2; return 1
    fi
    if [ ! -x "$_gbw_bin" ]; then
        echo "build produced no executable at $_gbw_bin" >&2; return 1
    fi
    printf '%s\n' "$_gbw_bin"; return 0
}

# gate_build_once_production -> B1/B5: the ONLY builder the named gate uses. It
# builds with the ALREADY-RESOLVED trusted cargo ($TRUSTED_CARGO, set once by
# gate_bootstrap). It does NOT re-resolve the toolchain and never consults PATH,
# CARGO, or PREFIX. If $TRUSTED_CARGO is unset (bootstrap not run), it fails.
gate_build_once_production() {
    if [ -z "${TRUSTED_CARGO:-}" ] || [ ! -x "${TRUSTED_CARGO:-/nonexistent}" ]; then
        echo "no trusted cargo resolved (bootstrap not run)" >&2; return 1
    fi
    _gate_build_with "$TRUSTED_CARGO"
}

# gate_build_once_with_stub -> TEST-ONLY. Honours ${CARGO:-cargo}. The named
# gate never calls this; it exists only so unit tests can drive build
# success/failure without a real toolchain.
gate_build_once_with_stub() {
    _gate_build_with "${CARGO:-cargo}"
}
