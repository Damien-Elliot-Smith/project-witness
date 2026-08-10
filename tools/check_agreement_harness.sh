#!/bin/sh
# Move 79 agreement-harness checker.
#
# The instrument must not mutate the baseline it measures: bytecode is
# disabled for EVERY python invocation, and package hygiene is verified
# BEFORE and AFTER. Three fresh processes run the corpus exactly ONCE each
# (--order original|reversed|shuffled); their COMPLETE canonical semantic
# responses are compared. Every process exit code is enforced against its
# structured status.
#
#   REAL_705=<path> REAL_MOVE78=<path> [REAL_V20=<path>] [RUST_BIN=<path>]
set -u
export PYTHONDONTWRITEBYTECODE=1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2
H="verify/agreement_harness_v01"
TIMEOUT_S=${HARNESS_TIMEOUT:-600}
START=$(date +%s)
fail=0
ok(){ printf "  OK    %s\n" "$1"; }
bad(){ printf "  FAIL  %s\n" "$1"; fail=1; }

echo "Agreement harness check (Move 79)"
echo "---------------------------------"

echo "Hygiene BEFORE:"
sh tools/check_package_hygiene.sh >/dev/null 2>&1 \
    && ok "repository clean before run" \
    || bad "repository not clean BEFORE run"

echo "Harness self-tests (warning-clean enforced):"
# B2: ResourceWarnings fire during finalization as "Exception ignored" and do
# NOT change the exit code. Trusting exit 0 was a false-green in the warning
# check itself. Treat warning TEXT as failure.
ST=$(python3 -B -W error::ResourceWarning "$H/self_tests.py" 2>&1)
ST_RC=$?
if [ "$ST_RC" -ne 0 ]; then
    bad "harness self-tests FAILED (exit $ST_RC)"
    printf '%s\n' "$ST" | tail -15
elif printf '%s' "$ST" | grep -qE "ResourceWarning|Exception ignored in:|unclosed file"; then
    bad "self-tests emitted warnings (exit was 0 — warning text is failure)"
    printf '%s' "$ST" | grep -E "ResourceWarning|Exception ignored in:|unclosed file" | head -5 | sed 's/^/    /'
else
    ok "self-tests pass, warning-clean ($(printf '%s' "$ST" | grep -oE 'Ran [0-9]+ tests' | head -1))"
fi

required_exit() {   # $1 = overall_status
    case "$1" in
        PASS) echo 0 ;; FAIL) echo 1 ;; USAGE) echo 2 ;;
        INCONCLUSIVE) echo 3 ;; *) echo 99 ;;
    esac
}

echo "Three fresh processes (one corpus pass each):"
HASHES=""
FIRST_OUT=""
for ORDER in original reversed shuffled; do
    printf "  ... %s\n" "$ORDER" >&2
    OUTF=$(mktemp); ERRF=$(mktemp)
    set -- "$H/run_agreement.py" --order "$ORDER"
    [ -n "${RUST_BIN:-}" ]    && set -- "$@" --rust-bin    "$RUST_BIN"
    [ -n "${REAL_V20:-}" ]    && set -- "$@" --real-v20    "$REAL_V20"
    [ -n "${REAL_705:-}" ]    && set -- "$@" --real-705    "$REAL_705"
    [ -n "${REAL_MOVE78:-}" ] && set -- "$@" --real-move78 "$REAL_MOVE78"
    # B3: NEVER pipe the harness — capture stdout, stderr and the exit code
    timeout -k 5 "$TIMEOUT_S" python3 -B "$@" >"$OUTF" 2>"$ERRF"
    RC=$?
    if [ "$RC" -eq 124 ] || [ "$RC" -eq 137 ]; then
        bad "$ORDER: TIMED OUT after ${TIMEOUT_S}s"
        rm -f "$OUTF" "$ERRF"; continue
    fi
    if [ ! -s "$OUTF" ]; then
        bad "$ORDER: empty stdout (exit $RC)"
        head -5 "$ERRF" | sed 's/^/    stderr: /'
        rm -f "$OUTF" "$ERRF"; continue
    fi
    STATUS=$(python3 -B -c "
import sys,json
try:
    with open('$OUTF') as _h: print(json.load(_h)['overall_status'])
except Exception: print('UNPARSEABLE')")
    if [ "$STATUS" = "UNPARSEABLE" ]; then
        bad "$ORDER: malformed harness JSON"
        rm -f "$OUTF" "$ERRF"; continue
    fi
    WANT=$(required_exit "$STATUS")
    if [ "$RC" != "$WANT" ]; then
        bad "$ORDER: status $STATUS requires exit $WANT, got $RC"
    else
        ok "$ORDER: $STATUS, exit $RC (consistent)"
    fi
    # B4: hash the COMPLETE semantic response. execution_order is the ONE
    # documented non-semantic field and is the only exclusion.
    HH=$(python3 -B -c "
import json,hashlib
with open('$OUTF') as _h: d=json.load(_h)
sem={k:v for k,v in d.items() if k!='execution_order'}
print(hashlib.sha256(json.dumps(sem,sort_keys=True).encode()).hexdigest())")
    HASHES="$HASHES $HH"
    [ -z "$FIRST_OUT" ] && FIRST_OUT=$(cat "$OUTF")
    rm -f "$OUTF" "$ERRF"
done

UNIQ=$(printf '%s' "$HASHES" | tr ' ' '\n' | grep -v '^$' | sort -u | wc -l)
if [ "$UNIQ" -eq 1 ]; then
    ok "3 fresh processes: complete canonical responses identical"
else
    bad "fresh-process responses differ ($UNIQ distinct)"
fi

echo "Hygiene AFTER:"
sh tools/check_package_hygiene.sh >/dev/null 2>&1 \
    && ok "repository clean after run" \
    || bad "harness DIRTIED the repository"

ELAPSED=$(( $(date +%s) - START ))
echo "  elapsed: ${ELAPSED}s"

if [ "$fail" -ne 0 ]; then
    echo "HARNESS_IMPLEMENTATION_CHECK: FAIL"
    exit 1
fi

AGREE=$(printf '%s' "$FIRST_OUT" | python3 -B -c "
import sys,json; d=json.load(sys.stdin)
print('%s %s' % (d['overall_status'], d['reason_code']))")
echo "HARNESS_IMPLEMENTATION_CHECK: PASS"
echo "SYSTEM_AGREEMENT_RESULT: $AGREE"
case "$AGREE" in
    INCONCLUSIVE*) exit 3 ;;
    PASS*) exit 0 ;;
    *) exit 1 ;;
esac
