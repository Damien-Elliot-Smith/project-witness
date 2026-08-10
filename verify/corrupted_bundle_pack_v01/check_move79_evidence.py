"""Move 80: mechanical validator of complete Move 79 regression evidence.

The Move 80 gate invokes the exact adopted
tools/check_move79_instrument_adoption.sh as a child, retains its FULL
output in the Move 80 transcript, and then requires (review-mandated)
that every one of the following facts is present and exact -- validated
here mechanically, never by prose. Line forms are anchored to the real
v27 Termux adoption transcript (MOVE_79_V27_TERMUX_GATE.txt, sha256
7d72ab50e8b5ab1180ebc0d4c3aa8def9d4b6def00b204fe1e811c620f1c72a8):

  - 63/63 harness self-tests   ("Ran 63 tests", pass line)
  - 73/73 gate-unit tests      ("Ran 73 tests", pass line)
  - all 85 cases executed
  - 74 agreement cases passed
  - 6 Python-only passed
  - 3 Rust-only passed
  - exactly 2 known divergences
  - divergent IDs are exactly the two declared, and the adopted gate's
    declared IDs are exactly stage_manifest_json_invalid and
    stage_report_field_missing_repaired (read from the ADOPTED gate
    script bytes, so the transcript's "the two declared" binds to the
    exact IDs)
  - no unmapped reasons
  - no missing diagnostics
  - MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS
  - SYSTEM_AGREEMENT_RESULT: FAIL
  - SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED
  - child gate exit code 0 (passed by the caller)

Usage:
  python3 -B check_move79_evidence.py --child-output <file> --child-exit <n>

Exit 0 when every fact is present and exact; 1 otherwise; 2 usage.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ADOPTED_GATE = os.path.join(ROOT, "tools",
                            "check_move79_instrument_adoption.sh")

REQUIRED_LINES = (
    ("63/63 harness self-tests",
     "  OK    self-tests pass, warning-clean (Ran 63 tests)"),
    ("73/73 gate-unit tests",
     "  OK    gate unit tests pass, warning-clean (Ran 73 tests)"),
    ("all 85 cases executed",
     "  OK    all 85 cases executed"),
    ("74 agreement cases passed",
     "  OK    74 agreement cases passed"),
    ("6 Python-only passed",
     "  OK    6 Python-only passed"),
    ("3 Rust-only passed",
     "  OK    3 Rust-only passed"),
    ("exactly 2 known divergences",
     "  OK    exactly 2 known divergences"),
    ("divergent IDs exactly the two declared",
     "  OK    divergent IDs are exactly the two declared"),
    ("no unmapped reasons",
     "  OK    no unmapped reasons"),
    ("no missing diagnostics",
     "  OK    no missing diagnostics"),
    ("agreement reports the divergence",
     "  OK    agreement reports the divergence"),
    ("harness exit 1 (agreement FAIL)",
     "  OK    harness exit 1 (agreement FAIL)"),
    ("Move 79 gate PASS marker",
     "MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS"),
    ("SYSTEM_AGREEMENT_RESULT: FAIL",
     "SYSTEM_AGREEMENT_RESULT: FAIL"),
    ("SYSTEM_AGREEMENT_REASON marker",
     "SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED"),
)

EXPECTED_DIV_IDS_LINE = ('export EXPECT_DIV_IDS="stage_manifest_json_'
                         'invalid stage_report_field_missing_repaired"')


def validate(child_output_text, child_exit, adopted_gate_path=None):
    """Returns (ok, report_lines)."""
    report = []
    ok = True
    lines = set(child_output_text.splitlines())

    for label, required in REQUIRED_LINES:
        if required in lines:
            report.append("  OK    Move 79 evidence: %s" % label)
        else:
            report.append("  FAIL  Move 79 evidence missing: %s "
                          "(required exact line: %r)" % (label, required))
            ok = False

    if child_exit == 0:
        report.append("  OK    Move 79 evidence: child gate exit 0")
    else:
        report.append("  FAIL  Move 79 child gate exit %s (expected 0)"
                      % child_exit)
        ok = False

    gate_path = adopted_gate_path or ADOPTED_GATE
    try:
        with open(gate_path, "r", encoding="utf-8") as handle:
            gate_src = handle.read()
    except OSError:
        report.append("  FAIL  adopted Move 79 gate script unreadable")
        return False, report
    if EXPECTED_DIV_IDS_LINE in gate_src:
        report.append("  OK    Move 79 evidence: declared divergence IDs "
                      "(from adopted gate bytes) are exactly "
                      "stage_manifest_json_invalid and "
                      "stage_report_field_missing_repaired")
    else:
        report.append("  FAIL  adopted gate does not declare the exact "
                      "expected divergence IDs")
        ok = False

    return ok, report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Require complete, exact Move 79 regression evidence "
                    "in the retained child gate output.")
    parser.add_argument("--child-output", required=True,
                        help="file containing the COMPLETE output of the "
                             "adopted Move 79 gate child process")
    parser.add_argument("--child-exit", required=True, type=int,
                        help="the child gate's exit code")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.child_output):
        print("usage error: --child-output is not a file")
        return 2
    with open(args.child_output, "r", encoding="utf-8",
              errors="replace") as handle:
        text = handle.read()

    ok, report = validate(text, args.child_exit)
    for line in report:
        print(line)
    print("MOVE_79_EVIDENCE_CHECK: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
