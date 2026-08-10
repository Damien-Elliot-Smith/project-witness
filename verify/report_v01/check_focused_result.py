#!/usr/bin/env python3
"""Move 83 — focused-suite result validation.

A genuine Termux run produced `OK (skipped=2)` — unittest's legitimate
success summary when tests were skipped — and the gate rejected it,
because it required a bare `OK` line and separately treated the substring
`skipped=` as a forbidden marker. The suite had genuinely succeeded.

This validates the result properly instead. Success requires ALL of:

* the suite process exited 0;
* stdout carries a `Ran <N> tests` line whose N equals the pinned count;
* the FINAL non-empty stdout line is a valid unittest success summary;
* no failure summary appears anywhere in stdout;
* stderr is empty.

The success summary is anchored to the final line, so an `OK` appearing in
a test name, in earlier output, or in text a test printed cannot satisfy
it. The accepted grammar is exactly what `unittest.TextTestRunner` emits
on success:

    OK
    OK (skipped=N)
    OK (expected failures=N)
    OK (skipped=N, expected failures=M)

Nothing broader is accepted. `unexpected successes` is deliberately absent:
`TestResult.wasSuccessful()` is False when any occur, so a run reporting
them is not a success and must not parse as one.

Skips are reported as evidence, never suppressed. Two device-node cases
legitimately skip on an unprivileged Android/Termux filesystem.
"""

import argparse
import os
import re
import sys

# Each annotation unittest can attach to a SUCCESSFUL run.
_ANNOTATION = r"(?:skipped|expected failures)=\d+"
SUCCESS_SUMMARY = re.compile(
    r"^OK(?: \((%s(?:, %s)*)\))?$" % (_ANNOTATION, _ANNOTATION))
RAN_LINE = re.compile(r"^Ran (\d+) tests? in ")
FAILURE_SUMMARY = re.compile(r"^FAILED\b")


class FocusedResultError(Exception):
    """Deterministic, message-only validation failure."""


def parse_annotations(annotation_text):
    """`skipped=2, expected failures=1` -> {'skipped': 2, ...}"""
    found = {}
    if not annotation_text:
        return found
    for part in annotation_text.split(", "):
        name, _, value = part.partition("=")
        found[name] = int(value)
    return found


def validate(stdout_text, stderr_text, exit_code, expected_count):
    """Returns (problems, facts)."""
    problems = []
    facts = {"exit_code": exit_code, "ran": None, "skipped": 0,
             "expected_failures": 0, "summary": None}

    if exit_code != 0:
        problems.append("focused suite exited %r, not 0" % exit_code)
    if stderr_text:
        problems.append("focused suite emitted stderr (%d bytes)"
                        % len(stderr_text))

    lines = stdout_text.splitlines()
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        problems.append("focused suite produced no stdout")
        return problems, facts

    # the pinned count, from the Ran line
    ran_values = [int(m.group(1))
                  for m in (RAN_LINE.match(line) for line in lines) if m]
    if not ran_values:
        problems.append("focused stdout has no 'Ran <N> tests' line")
    elif len(ran_values) != 1:
        problems.append("focused stdout has %d 'Ran' lines; expected one"
                        % len(ran_values))
    else:
        facts["ran"] = ran_values[0]
        if ran_values[0] != expected_count:
            problems.append(
                "focused test count is %d, the pinned count is %d"
                % (ran_values[0], expected_count))

    # any failure summary anywhere is disqualifying
    for line in lines:
        if FAILURE_SUMMARY.match(line):
            problems.append("focused stdout contains a failure summary: %r"
                            % line.strip()[:80])
            break

    # the success summary must be the FINAL non-empty line
    final = non_empty[-1].rstrip()
    match = SUCCESS_SUMMARY.match(final)
    if match is None:
        problems.append(
            "the final stdout line is not a valid unittest success "
            "summary: %r" % final[:80])
    else:
        facts["summary"] = final
        annotations = parse_annotations(match.group(1))
        unknown = sorted(set(annotations) - {"skipped", "expected failures"})
        if unknown:
            problems.append("unrecognised success annotation(s): %s"
                            % ", ".join(unknown))
        facts["skipped"] = annotations.get("skipped", 0)
        facts["expected_failures"] = annotations.get("expected failures", 0)
    return problems, facts


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Move 83 focused-suite result validation")
    parser.add_argument("--stdout", required=True,
                        help="absolute path to captured stdout")
    parser.add_argument("--stderr", required=True,
                        help="absolute path to captured stderr")
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--expect-count", required=True,
                        help="absolute path to EXPECTED_TEST_COUNT.txt")
    args = parser.parse_args(argv)

    for label, path in (("--stdout", args.stdout),
                        ("--stderr", args.stderr),
                        ("--expect-count", args.expect_count)):
        if not os.path.isabs(path) or not os.path.isfile(path):
            print("usage error: %s must be an absolute regular file"
                  % label)
            return 2

    with open(args.stdout, encoding="utf-8", errors="replace") as handle:
        stdout_text = handle.read()
    with open(args.stderr, "rb") as handle:
        stderr_bytes = handle.read()
    with open(args.expect_count, encoding="utf-8") as handle:
        raw_count = handle.read().strip()
    if not raw_count.isdigit():
        print("usage error: pinned count is not an integer: %r" % raw_count)
        return 2

    problems, facts = validate(stdout_text, stderr_bytes.decode(
        "utf-8", "replace"), args.exit_code, int(raw_count))

    print("FOCUSED_RAN: %s" % facts["ran"])
    print("FOCUSED_PINNED: %s" % raw_count)
    print("FOCUSED_SUMMARY: %s" % (facts["summary"] or "(none)"))
    print("FOCUSED_SKIPPED: %d" % facts["skipped"])
    print("FOCUSED_EXPECTED_FAILURES: %d" % facts["expected_failures"])
    for problem in sorted(set(problems)):
        print("FOCUSED_PROBLEM: %s" % problem)
    if problems:
        print("MOVE_83_FOCUSED_RESULT: FAIL (%d problem(s))"
              % len(set(problems)))
        return 1
    print("MOVE_83_FOCUSED_RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
