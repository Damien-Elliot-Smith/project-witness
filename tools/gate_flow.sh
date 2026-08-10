# gate_flow.sh — Move 79 adoption-gate orchestration.
#
# gate_run_flow drives the decisive sequence: source provenance -> trusted
# toolchain guard -> workspace checker -> clean build -> binary version ->
# three stderr-checked measurements -> final adoption decision.
#
# v15: this file NO LONGER resolves the toolchain and NO LONGER reads FLOW_H
# from the environment. The trusted commands ($TRUSTED_PYTHON3, $TRUSTED_SH,
# $TRUSTED_TIMEOUT, $TRUSTED_CARGO) are resolved ONCE by gate_bootstrap (or, in
# tests, set explicitly by the controlled fixture). The reviewed harness path
# is a FIXED constant, not an inherited variable (B3).
#
# External dependencies are NAMED SEAM FUNCTIONS with production defaults. A
# controlled test fixture may redefine them AFTER sourcing and BEFORE calling
# gate_run_flow. The named production gate does not redefine them and exposes no
# bypass. gate_build_once_production is NEVER overridden.
#
# Requires gate_lib.sh sourced first.

# FIXED reviewed harness path (B3): never taken from the environment.
GATE_HARNESS_DIR=verify/agreement_harness_v01

# ---- production seam defaults (use ABSOLUTE trusted commands, B4) --------

flow_run_provenance() {
    "$TRUSTED_PYTHON3" -B tools/verify_rust_provenance.py "$REAL_MOVE78" >"$1" 2>&1
}

flow_run_checker() {
    PYTHONWARNINGS=error::ResourceWarning "$TRUSTED_SH" tools/check_rust_workspace.sh >"$1" 2>&1
}

flow_run_measurement() {
    _fm_order=$1; _fm_bin=$2; _fm_out=$3; _fm_err=$4
    set -- "$GATE_HARNESS_DIR/run_agreement.py" --order "$_fm_order" --rust-bin "$_fm_bin"
    [ -n "${REAL_V20:-}" ]    && set -- "$@" --real-v20    "$REAL_V20"
    [ -n "${REAL_705:-}" ]    && set -- "$@" --real-705    "$REAL_705"
    [ -n "${REAL_MOVE78:-}" ] && set -- "$@" --real-move78 "$REAL_MOVE78"
    # exec so the backgrounded PID IS the measurement process (directly
    # killable on interruption); redirections apply to the exec'd command.
    PYTHONWARNINGS=error::ResourceWarning \
        exec "$TRUSTED_TIMEOUT" -k 5 "${HARNESS_TIMEOUT:-900}" \
        "$TRUSTED_PYTHON3" -B "$@" >"$_fm_out" 2>"$_fm_err"
}

# ---- orchestration ------------------------------------------------------

gate_run_flow() {
    _flow_fail=0
    _fok(){ printf "  OK    %s\n" "$1"; }
    _fbad(){ printf "  FAIL  %s\n" "$1"; _flow_fail=1; }

    : "${EXPECT_TOTAL:?}"; : "${EXPECT_AGREE:?}"; : "${EXPECT_PY_ONLY:?}"
    : "${EXPECT_RS_ONLY:?}"; : "${EXPECT_DIV:?}"; : "${EXPECT_DIV_IDS:?}"

    # trusted interpreters must already be resolved (bootstrap or fixture).
    for _t in "${TRUSTED_PYTHON3:-}" "${TRUSTED_SH:-}" "${TRUSTED_TIMEOUT:-}"; do
        if [ -z "$_t" ] || [ ! -x "$_t" ]; then
            echo "  FAIL  trusted interpreters not resolved"
            echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (untrusted environment)"
            return 1
        fi
    done

    echo ""
    echo "SOURCE PROVENANCE: binding adoption to reviewed Rust source"
    _PF=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_PF"
    flow_run_provenance "$_PF"; _prc=$?
    if [ "$_prc" -eq 0 ] && grep -qx 'RUST_PROVENANCE_CHECK: PASS' "$_PF"; then
        _fok "pin DERIVED from the real adopted Move 78 v10 artifact"
    else
        _fbad "pin is NOT derived from the real adopted baseline (rc $_prc)"
        sed 's/^/        /' "$_PF"
    fi
    rm -f "$_PF"
    if [ "$_flow_fail" -ne 0 ]; then
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (source provenance)"; return 1
    fi

    echo ""
    echo "BUILD: trusted toolchain, clean target, exact marker"
    if ! gate_assert_no_target; then
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (stale target)"; return 1
    fi

    # Toolchain was resolved ONCE at bootstrap. Absent trusted cargo -> 3.
    if [ -z "${TRUSTED_CARGO:-}" ] || [ ! -x "${TRUSTED_CARGO:-/nonexistent}" ]; then
        echo "  trusted toolchain unavailable; cannot adopt without a build."
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: INCONCLUSIVE_RUST_UNAVAILABLE"
        return 3
    fi
    _fok "trusted toolchain present (resolved once at bootstrap)"

    _RWF=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_RWF"
    flow_run_checker "$_RWF"; _rwrc=$?
    _RW=$(cat "$_RWF"); rm -f "$_RWF"
    if gate_output_has_warnings "$_RW"; then
        _fbad "rust workspace checker emitted warnings"
        printf '%s\n' "$_RW" | grep -E 'ResourceWarning|Exception ignored in:|unclosed file|Traceback' | head -3 | sed 's/^/    /'
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (workspace warnings)"; return 1
    fi
    _CLASS=$(classify_workspace_result "$_RW" "$_rwrc")
    case "$_CLASS" in
        PASS) _fok "RUST_WORKSPACE_CHECK: PASS (exact marker + exit 0)" ;;
        UNAVAIL)
            _fbad "workspace UNAVAIL after a resolved toolchain"
            echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (toolchain contradiction)"; return 1 ;;
        *)
            _fbad "RUST_WORKSPACE_CHECK not exact PASS/0 (exit $_rwrc)"
            printf '%s\n' "$_RW" | tail -4 | sed 's/^/    /'
            echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (workspace marker/exit)"; return 1 ;;
    esac

    if ! gate_clean_target; then
        _fbad "could not remove checker-created rust/target"
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (target cleanup)"; return 1
    fi
    _fok "checker target tree removed; building clean"

    BUILT=$(gate_build_once_production)
    if [ $? -ne 0 ] || [ -z "$BUILT" ]; then
        echo "  FAIL  clean build did not produce the executable"
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (build)"; return 1
    fi
    _fok "built from reviewed source (clean target): $BUILT"
    RUST_USE="$BUILT"

    _EXPECT_VERSION="0.0.8-step79-diagnostics"
    _REPORTED=$("$RUST_USE" verify /nonexistent 2>/dev/null | "$TRUSTED_PYTHON3" -B tools/read_version.py)
    if [ "$_REPORTED" != "$_EXPECT_VERSION" ]; then
        _fbad "built binary reports version '$_REPORTED', expected '$_EXPECT_VERSION'"
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (binary version)"; return 1
    fi
    _fok "built binary reports $_EXPECT_VERSION"

    echo ""
    echo "MEASUREMENT: three fresh processes; every stderr must be empty"
    _HASHES=""; _FIRST=""; _FIRST_RC=""
    for _ORDER in original reversed shuffled; do
        printf "  ... %s\n" "$_ORDER" >&2
        _OUTF=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_OUTF"
        _ERRF=$("$TRUSTED_MKTEMP"); gate_track_tmp "$_ERRF"
        # run the measurement as a tracked background child so a HUP/INT/TERM
        # during it is handled immediately (gate_on_signal kills the child and
        # exits) and cannot begin the next order. The seam exec's its process,
        # so GATE_CHILD_PID is the real measurement PID.
        flow_run_measurement "$_ORDER" "$RUST_USE" "$_OUTF" "$_ERRF" &
        GATE_CHILD_PID=$!
        wait "$GATE_CHILD_PID"; _mrc=$?
        GATE_CHILD_PID=""
        if [ "$_mrc" -eq 124 ] || [ "$_mrc" -eq 137 ]; then
            _fbad "$_ORDER: TIMED OUT (not an agreement result)"; rm -f "$_OUTF" "$_ERRF"; continue
        fi
        if ! gate_measurement_stderr_clean "$_ERRF"; then
            _fbad "$_ORDER: measurement produced stderr (harness did not complete cleanly)"
            rm -f "$_OUTF" "$_ERRF"; continue
        fi
        if [ ! -s "$_OUTF" ]; then
            _fbad "$_ORDER: empty stdout (exit $_mrc)"; rm -f "$_OUTF" "$_ERRF"; continue
        fi
        _STATUS=$("$TRUSTED_PYTHON3" -B -c "
import json,sys
try:
    with open('$_OUTF') as _h: print(json.load(_h)['overall_status'])
except Exception: print('UNPARSEABLE')")
        case "$_STATUS" in
            PASS) _WANT=0 ;; FAIL) _WANT=1 ;; USAGE) _WANT=2 ;; INCONCLUSIVE) _WANT=3 ;; *) _WANT=99 ;;
        esac
        if [ "$_mrc" != "$_WANT" ]; then
            _fbad "$_ORDER: status $_STATUS requires exit $_WANT, got $_mrc"
        else
            _fok "$_ORDER: $_STATUS, exit $_mrc, stderr empty (consistent)"
        fi
        _HH=$("$TRUSTED_PYTHON3" -B -c "
import json,hashlib,sys
try:
    with open('$_OUTF') as _h: d=json.load(_h)
except Exception: print('UNPARSEABLE'); sys.exit(0)
sem={k:v for k,v in d.items() if k!='execution_order'}
print(hashlib.sha256(json.dumps(sem,sort_keys=True).encode()).hexdigest())")
        _HASHES="$_HASHES $_HH"
        if [ -z "$_FIRST" ]; then _FIRST=$(cat "$_OUTF"); _FIRST_RC=$_mrc; fi
        rm -f "$_OUTF" "$_ERRF"
    done
    _UNIQ=$(printf '%s' "$_HASHES" | tr ' ' '\n' | grep -v '^$' | sort -u | wc -l)
    [ "$_UNIQ" -eq 1 ] && _fok "3 processes: canonical responses identical" || _fbad "fresh-process responses differ"

    echo ""
    echo "MEASUREMENT ASSERTIONS:"
    if [ -z "$_FIRST" ]; then
        _fbad "no measurement produced a parseable response"
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (measurement)"; return 1
    fi
    eval "$(printf '%s' "$_FIRST" | "$TRUSTED_PYTHON3" -B -c "
import sys,json
try:
    d=json.load(sys.stdin)
except Exception as _e:
    print('KIND=malformed')
    print('ENVREASON=\"%s\"'%str(_e).replace(chr(34),' ')[:160]); sys.exit(0)
s=d.get('summary')
_req=('total_cases','shared_agreement_cases_passed','python_only_cases_passed',
      'rust_only_cases_passed','divergences','divergent_cases','unmapped_reasons',
      'missing_diagnostics','rust_lane_validated')
if not isinstance(s,dict) or not all(k in s for k in _req):
    print('KIND=envelope')
    print('ENVSTATUS=\"%s\"'%str(d.get('overall_status','?')))
    print('ENVRC=\"%s\"'%str(d.get('reason_code','?')))
    print('ENVDETAIL=\"%s\"'%str(d.get('detail','')).replace(chr(34),' ')[:200])
    sys.exit(0)
print('KIND=summary')
print('RC_=%s'%d.get('reason_code'))
print('TOT=%s'%s['total_cases']); print('AGR=%s'%s['shared_agreement_cases_passed'])
print('PYO=%s'%s['python_only_cases_passed']); print('RSO=%s'%s['rust_only_cases_passed'])
print('DIV=%s'%s['divergences']); print('DIVIDS=\"%s\"'%' '.join(sorted(s['divergent_cases'])))
print('UNM=%s'%s['unmapped_reasons']); print('MSD=%s'%s['missing_diagnostics'])
print('RLV=%s'%s['rust_lane_validated'])")"
    # Fail CLOSED on an error envelope, malformed JSON, or an incomplete summary
    # — never assume a summary is present (that raised KeyError before v27).
    if [ "${KIND:-}" != "summary" ]; then
        if [ "${KIND:-}" = "envelope" ]; then
            _fbad "measurement returned an error envelope: status=${ENVSTATUS:-?} reason=${ENVRC:-?} detail=${ENVDETAIL:-}"
        elif [ "${KIND:-}" = "malformed" ]; then
            _fbad "measurement response was not valid JSON: ${ENVREASON:-}"
        else
            _fbad "measurement response lacked a complete summary"
        fi
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (measurement)"
        return 1
    fi
    [ "${RLV:-}" = "True" ] && _fok "Rust lane executed" || _fbad "Rust lane not executed"
    [ "${TOT:-0}" = "$EXPECT_TOTAL" ] && _fok "all $EXPECT_TOTAL cases executed" || _fbad "expected $EXPECT_TOTAL cases, got ${TOT:-?}"
    [ "${AGR:-0}" = "$EXPECT_AGREE" ] && _fok "$EXPECT_AGREE agreement cases passed" || _fbad "expected $EXPECT_AGREE, got ${AGR:-?}"
    [ "${PYO:-0}" = "$EXPECT_PY_ONLY" ] && _fok "$EXPECT_PY_ONLY Python-only passed" || _fbad "expected $EXPECT_PY_ONLY, got ${PYO:-?}"
    [ "${RSO:-0}" = "$EXPECT_RS_ONLY" ] && _fok "$EXPECT_RS_ONLY Rust-only passed" || _fbad "expected $EXPECT_RS_ONLY, got ${RSO:-?}"
    [ "${DIV:-0}" = "$EXPECT_DIV" ] && _fok "exactly $EXPECT_DIV known divergences" || _fbad "expected $EXPECT_DIV divergences, got ${DIV:-?}"
    [ "${DIVIDS:-}" = "$EXPECT_DIV_IDS" ] && _fok "divergent IDs are exactly the two declared" || _fbad "unexpected divergence set: ${DIVIDS:-none}"
    [ "${UNM:-1}" = "0" ] && _fok "no unmapped reasons" || _fbad "unmapped reasons present"
    [ "${MSD:-1}" = "0" ] && _fok "no missing diagnostics" || _fbad "missing diagnostics"
    [ "${RC_:-}" = "BEHAVIOURAL_DIVERGENCE_DETECTED" ] && _fok "agreement reports the divergence" || _fbad "expected BEHAVIOURAL_DIVERGENCE_DETECTED, got ${RC_:-?}"
    [ "${_FIRST_RC:-}" = "1" ] && _fok "harness exit 1 (agreement FAIL)" || _fbad "expected exit 1, got ${_FIRST_RC:-?}"

    echo ""
    echo "POST-RUN hygiene:"
    _cache=$(find . -name '__pycache__' -o -name '*.pyc' -o -name '*.pyo' 2>/dev/null | head -1)
    [ -z "$_cache" ] && _fok "no bytecode/cache written during measurement" || _fbad "measurement wrote bytecode/cache: $_cache"

    echo ""
    if [ "$_flow_fail" -ne 0 ]; then
        echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL"; return 1
    fi
    echo "MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS"
    echo "SYSTEM_AGREEMENT_RESULT: FAIL"
    echo "SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED"
    return 0
}
