#!/usr/bin/env python3
"""In-process self-checks for Stack Selfcheck v0.1. Small, fast gates only -- does
NOT run the full unit suite. No bare asserts, no subprocesses."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stack_selfcheck_lib import canonical, report as report_mod, steps as steps_mod, \
    checksums, verifier
from stack_selfcheck_lib.errors import CheckError
from tests.synthetic import build_inventory, build_stack_verifier_output


class SelfCheckError(Exception):
    pass


def _expect(cond, msg):
    if not cond:
        raise SelfCheckError(msg)


def _write_out(report, work):
    out = os.path.join(work, "out_%d" % len(os.listdir(work)))
    os.makedirs(out, exist_ok=True)
    canonical.write_canonical(os.path.join(out, "stack_selfcheck_report.json"), report)
    canonical.write_canonical(os.path.join(out, "stack_selfcheck_steps.json"),
                              steps_mod.build_steps(steps_mod.all_completed()))
    canonical.atomic_write_bytes(
        os.path.join(out, "stack_selfcheck_checksums.txt"),
        checksums.build_checksums_text(out))
    return out


def gate_imports():
    for mod in ("canonical", "errors", "versions", "validation", "checksums",
                "steps", "inventory_reader", "component_checks", "sidecar_checks",
                "documentation_checks", "legacy_documentation",
                "stack_verifier_reader", "report", "verifier"):
        __import__("stack_selfcheck_lib." + mod)


def gate_canonical_json():
    raw = canonical.canonical_bytes({"b": 1, "a": 2})
    _expect(raw == b'{"a":2,"b":1}', "canonical ordering wrong")
    _expect(canonical.is_canonical_bytes(raw), "is_canonical false negative")


def gate_valid_inventory():
    with tempfile.TemporaryDirectory() as work:
        inv = build_inventory(work)
        report, _ = report_mod.build_selfcheck_report(inv)
        _expect(report["stack_selfcheck_status"] == "STACK_SELFCHECK_PASSED", "valid inv failed")
        _expect(report["component_count"] == 22, "expected 22 components")


def gate_missing_component_refused():
    with tempfile.TemporaryDirectory() as work:
        inv = build_inventory(work)
        # drop one component from the inventory file
        data = canonical.load_json(inv)
        data["components"] = [c for c in data["components"]
                              if c["component_id"] != "odin_claim_reasoner_v01"]
        canonical.write_canonical(inv, data)
        try:
            report_mod.build_selfcheck_report(inv)
            raise SelfCheckError("missing component not refused")
        except CheckError:
            pass


def gate_zip_sidecar_mismatch_refused():
    with tempfile.TemporaryDirectory() as work:
        inv = build_inventory(work)
        data = canonical.load_json(inv)
        # corrupt one zip so its sidecar no longer matches
        for c in data["components"]:
            if c.get("zip_path"):
                with open(c["zip_path"], "ab") as f:
                    f.write(b"x")
                break
        try:
            report_mod.build_selfcheck_report(inv)
            raise SelfCheckError("zip mismatch not refused")
        except CheckError:
            pass


def gate_bad_stack_verifier_output_refused():
    with tempfile.TemporaryDirectory() as work:
        inv = build_inventory(work)
        run = os.path.join(work, "sv")
        build_stack_verifier_output(run, stack_verification_status="FAILED_SOURCE_VERIFY")
        try:
            report_mod.build_selfcheck_report(inv, run)
            raise SelfCheckError("bad stack verifier output not refused")
        except CheckError:
            pass


def gate_verify_valid_selfcheck_output():
    with tempfile.TemporaryDirectory() as work:
        inv = build_inventory(work)
        report, _ = report_mod.build_selfcheck_report(inv)
        out = _write_out(report, work)
        _expect(verifier.verify(out).ok, "verify of valid output failed")


def gate_no_truth_claims():
    with tempfile.TemporaryDirectory() as work:
        inv = build_inventory(work)
        report, _ = report_mod.build_selfcheck_report(inv)
        out = _write_out(report, work)
        _expect(verifier.verify(out).ok, "truth scan failed on clean output")


def gate_legacy_documentation_allowed():
    with tempfile.TemporaryDirectory() as work:
        legacy = {
            "sentinel_core_v022": ["KNOWN_LIMITATIONS.md", "RELEASE_COMMANDS.md"],
            "histor_lite_v012": ["RELEASE_COMMANDS.md"],
            "case_bundle_v011": ["RELEASE_COMMANDS.md"],
            "atlas_red_blue_pack_v01": ["KNOWN_LIMITATIONS.md", "RELEASE_COMMANDS.md"],
        }
        from stack_selfcheck_lib import versions
        profiles = {cid: versions.LEGACY_DOCUMENTATION_PROFILE for cid in legacy}
        inv = build_inventory(work, omit_docs=legacy, legacy_profiles=profiles)
        report, _ = report_mod.build_selfcheck_report(inv)
        _expect(report["stack_selfcheck_status"] == "STACK_SELFCHECK_PASSED",
                "legacy inventory failed")
        used = {r["component_id"] for r in report["legacy_documentation_allowances"]
                if r["legacy_documentation_allowance_used"]}
        _expect(used == set(legacy), "legacy allowances not recorded")
        out = _write_out(report, work)
        _expect(verifier.verify(out).ok, "legacy output did not verify")


def gate_unknown_legacy_claim_refused():
    with tempfile.TemporaryDirectory() as work:
        from stack_selfcheck_lib import versions
        inv = build_inventory(work, legacy_profiles={
            "stack_verifier_v01": versions.LEGACY_DOCUMENTATION_PROFILE})
        try:
            report_mod.build_selfcheck_report(inv)
            raise SelfCheckError("unknown legacy claim not refused")
        except CheckError:
            pass


GATES = (
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("valid_inventory", gate_valid_inventory),
    ("missing_component_refused", gate_missing_component_refused),
    ("zip_sidecar_mismatch_refused", gate_zip_sidecar_mismatch_refused),
    ("bad_stack_verifier_output_refused", gate_bad_stack_verifier_output_refused),
    ("verify_valid_selfcheck_output", gate_verify_valid_selfcheck_output),
    ("no_truth_claims", gate_no_truth_claims),
    ("legacy_documentation_allowed", gate_legacy_documentation_allowed),
    ("unknown_legacy_claim_refused", gate_unknown_legacy_claim_refused),
)


def main():
    failures = []
    for name, func in GATES:
        try:
            func()
            print("PASS  " + name)
        except Exception as exc:
            failures.append((name, exc))
            print("FAIL  %s: %s" % (name, exc))
    if failures:
        print("selfcheck: %d gate(s) failed" % len(failures))
        return 1
    print("selfcheck: all %d gates passed" % len(GATES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
