"""The Atlas Release Gate 'check' engine.

Runs the fixed, short-circuiting sequence of checks against an Atlas Registry
v0.1 release folder and writes the release-gate output. It never modifies the
registry, never runs workflows, and never asserts truth of contents.
"""

import os

from . import (canonical, validation, documentation_checks, feature_checks,
               report as report_mod, steps as steps_mod, checksums)
from .errors import (
    RELEASE_GATE_PASSED, FAILED_ATLAS_ROOT_MISSING, FAILED_REQUIRED_FILE_MISSING,
    FAILED_REGISTRY_VERIFY, FAILED_EXPORT_VERIFY, FAILED_DOCUMENTATION_CHECK,
    FAILED_HONESTY_CHECK, FAILED_FORBIDDEN_FEATURE_CHECK,
    REGISTRY_VERIFIED, REGISTRY_NOT_VERIFIED, EXPORT_VERIFIED, EXPORT_NOT_VERIFIED,
)

OUTPUT_REPORT = "atlas_release_gate_report.json"
OUTPUT_STEPS = "atlas_release_gate_steps.json"
OUTPUT_CHECKSUMS = "atlas_release_gate_checksums.txt"
EXPORT_DIR = "atlas_export"


class CheckOutcome:
    def __init__(self, status, out_dir):
        self.status = status
        self.out_dir = out_dir
        self.passed = (status == RELEASE_GATE_PASSED)


def _read_doc_text(atlas_root):
    parts = []
    for name in ("README.md", "KNOWN_LIMITATIONS.md"):
        path = os.path.join(atlas_root, name)
        if os.path.isfile(path):
            parts.append(canonical.read_bytes(path).decode("utf-8", "replace"))
    return "\n".join(parts)


def _write_outputs(out_dir, gate_status, registry_status, export_status,
                   required_present, doc_present, honesty_present,
                   forbidden_absent, statuses):
    rpt = report_mod.build_report(
        gate_status, registry_status, export_status,
        required_present, doc_present, honesty_present, forbidden_absent)
    report_mod.write_report(os.path.join(out_dir, OUTPUT_REPORT), rpt)
    steps_obj = steps_mod.build_steps(statuses)
    canonical.write_canonical(os.path.join(out_dir, OUTPUT_STEPS), steps_obj)
    paths = checksums.present_canonical_paths(out_dir)
    canonical.atomic_write_bytes(
        os.path.join(out_dir, OUTPUT_CHECKSUMS),
        checksums.build_checksums_text(out_dir, paths))


def _finish_fail(out_dir, gate_status, fail_index, registry_status, export_status,
                 required_present, doc_present, honesty_present, forbidden_absent):
    statuses = steps_mod.statuses_with_failure_at(fail_index)
    _write_outputs(out_dir, gate_status, registry_status, export_status,
                   required_present, doc_present, honesty_present,
                   forbidden_absent, statuses)
    return CheckOutcome(gate_status, out_dir)


def run_check(atlas_root, out_dir, runner):
    """Run the release gate. 'runner' is an Atlas runner (fake or subprocess)."""
    os.makedirs(out_dir, exist_ok=True)
    export_dir = os.path.join(out_dir, EXPORT_DIR)
    os.makedirs(export_dir, exist_ok=True)

    registry_status = REGISTRY_NOT_VERIFIED
    export_status = EXPORT_NOT_VERIFIED

    # step_001 CHECK_REQUIRED_FILES (root + required files + registry presence)
    if not validation.atlas_root_exists(atlas_root):
        return _finish_fail(out_dir, FAILED_ATLAS_ROOT_MISSING, 0,
                            registry_status, export_status,
                            False, False, False, False)
    if validation.missing_required(atlas_root):
        return _finish_fail(out_dir, FAILED_REQUIRED_FILE_MISSING, 0,
                            registry_status, export_status,
                            False, False, False, False)
    required_present = True

    # step_002 VERIFY_ATLAS_REGISTRY
    rr = runner.verify_registry(atlas_root)
    if not rr.ok:
        return _finish_fail(out_dir, FAILED_REGISTRY_VERIFY, 1,
                            registry_status, export_status,
                            required_present, False, False, False)
    registry_status = REGISTRY_VERIFIED

    # step_003 EXPORT_ATLAS_REGISTRY
    er = runner.export_registry(atlas_root, export_dir)
    if not er.ok:
        return _finish_fail(out_dir, FAILED_EXPORT_VERIFY, 2,
                            registry_status, export_status,
                            required_present, False, False, False)

    # step_004 VERIFY_ATLAS_EXPORT
    evr = runner.verify_export(export_dir)
    if not evr.ok:
        return _finish_fail(out_dir, FAILED_EXPORT_VERIFY, 3,
                            registry_status, export_status,
                            required_present, False, False, False)
    export_status = EXPORT_VERIFIED

    doc_text = _read_doc_text(atlas_root)

    # step_005 CHECK_DOCUMENTATION
    if documentation_checks.check_documentation(doc_text):
        return _finish_fail(out_dir, FAILED_DOCUMENTATION_CHECK, 4,
                            registry_status, export_status,
                            required_present, False, False, False)
    doc_present = True

    # step_006 CHECK_HONESTY_BOUNDARY
    if documentation_checks.check_honesty(doc_text):
        return _finish_fail(out_dir, FAILED_HONESTY_CHECK, 5,
                            registry_status, export_status,
                            required_present, doc_present, False, False)
    honesty_present = True

    # step_007 CHECK_FORBIDDEN_FEATURES
    if feature_checks.scan_forbidden_features(doc_text):
        return _finish_fail(out_dir, FAILED_FORBIDDEN_FEATURE_CHECK, 6,
                            registry_status, export_status,
                            required_present, doc_present, honesty_present, False)
    forbidden_absent = True

    # step_008 WRITE_RELEASE_GATE_REPORT + step_009 VERIFY_RELEASE_GATE_OUTPUT
    statuses = steps_mod.all_completed()
    _write_outputs(out_dir, RELEASE_GATE_PASSED, registry_status, export_status,
                   required_present, doc_present, honesty_present,
                   forbidden_absent, statuses)
    return CheckOutcome(RELEASE_GATE_PASSED, out_dir)
