"""One-Command Demo wrapper engine: eight fixed steps, short-circuit, honest
failure. It only orchestrates the frozen Connected Demo's public CLI through the
injected runner; it never edits frozen folders or invents statuses.
"""

import json
import os

from . import canonical, checksums, verifier, versions
from .canonical import require
from .errors import (CheckError, VerifyError, ONE_COMMAND_DEMO_COMPLETED,
                     FAILED_CONFIG_INVALID, FAILED_CONNECTED_DEMO_RUN,
                     FAILED_CONNECTED_DEMO_VERIFY, FAILED_REQUIRED_STATUS_MISSING,
                     FAILED_TRUTH_BOUNDARY, FAILED_CHECKSUMS_INVALID)
from .runner import RealConnectedDemoRunner, _RUN_KEYS
from .steps import STEPS_ORDER, build_steps, all_completed

_TRUTH_SENTENCE = (
    "One-Command Demo Script v0.1 runs and verifies the frozen Project Witness "
    "Connected Demo v0.1. It does not prove evidence contents are true, does not "
    "prove ODIN claims are true, and does not verify external reality.")


def _load_config(config_path):
    require(os.path.isfile(config_path), FAILED_CONFIG_INVALID,
            "config file not found")
    try:
        cfg = canonical.load_json(config_path)
    except Exception as exc:  # noqa: BLE001
        raise CheckError(FAILED_CONFIG_INVALID, "config not valid JSON: %s" % exc)
    require(isinstance(cfg, dict), FAILED_CONFIG_INVALID, "config not an object")
    require(cfg.get("config_version") == versions.CONFIG_VERSION,
            FAILED_CONFIG_INVALID, "config_version must be %s" % versions.CONFIG_VERSION)
    for key in ("connected_demo_root", "connected_demo_config"):
        require(isinstance(cfg.get(key), str) and cfg[key],
                FAILED_CONFIG_INVALID, "config missing string field: %s" % key)
    return cfg


def _check_demo_root(cfg):
    root = cfg["connected_demo_root"]
    require(os.path.isdir(root), FAILED_CONNECTED_DEMO_RUN,
            "connected_demo_root does not exist")
    require(os.path.isfile(os.path.join(root, "connected_demo.py")),
            FAILED_CONNECTED_DEMO_RUN,
            "connected_demo_root has no connected_demo.py")


def _require_run_keys(demo_config):
    require(isinstance(demo_config, dict), FAILED_CONFIG_INVALID,
            "connected_demo_config not an object")
    for key in _RUN_KEYS:
        require(key in demo_config, FAILED_CONFIG_INVALID,
                "connected_demo_config missing key: %s" % key)


def _parse_verify_ok(text):
    try:
        return bool(json.loads(text).get("verify_ok"))
    except Exception:  # noqa: BLE001
        return False


def _read_truth_boundary(demo_out):
    path = os.path.join(demo_out, "stack_verifier_output",
                        "stack_verification_report.json")
    if not os.path.isfile(path):
        return False
    try:
        return canonical.load_json(path).get("truth_boundary_valid") is True
    except Exception:  # noqa: BLE001
        return False


def _build_report(observed, truth_valid, wrapper_status):
    report = {
        "one_command_demo_script_version":
            versions.ONE_COMMAND_DEMO_SCRIPT_VERSION,
        "wrapper_status": wrapper_status,
        "truth_boundary_valid": bool(truth_valid),
        "truth_boundary": _TRUTH_SENTENCE,
        "known_limitations": list(versions.KNOWN_LIMITATIONS),
    }
    for key in ("connected_demo_status",) + tuple(
            k for k in versions.REQUIRED_STATUSES if k != "connected_demo_status"):
        report[key] = observed.get(key)
    return report


def _write_outputs(out_dir, report, steps):
    canonical.write_canonical(
        os.path.join(out_dir, checksums.REPORT_FILE), report)
    canonical.write_canonical(
        os.path.join(out_dir, checksums.STEPS_FILE),
        {"one_command_demo_steps_version": versions.ONE_COMMAND_DEMO_STEPS_VERSION,
         "steps": steps})
    canonical.atomic_write_bytes(
        os.path.join(out_dir, checksums.CHECKSUMS_FILE),
        checksums.build_checksums_text(out_dir))


def run_wrapper(config_path, out_dir, runner=None):
    os.makedirs(out_dir, exist_ok=True)
    demo_out = os.path.join(out_dir, "connected_demo_output")
    observed = {}
    truth_valid = False
    completed = 0
    try:
        cfg = _load_config(config_path)                       # step_001
        completed = 1
        _check_demo_root(cfg)                                 # step_002
        completed = 2
        if runner is None:
            demo_config = canonical.load_json(cfg["connected_demo_config"])
            _require_run_keys(demo_config)
            runner = RealConnectedDemoRunner(cfg["connected_demo_root"], demo_config)
        rc, out, err = runner.run_demo(demo_out)              # step_003
        require(rc == 0, FAILED_CONNECTED_DEMO_RUN,
                "connected demo run failed: %s" % err.strip()[:200])
        completed = 3
        rc, out, err = runner.verify_demo(demo_out)           # step_004
        require(rc == 0 and _parse_verify_ok(out), FAILED_CONNECTED_DEMO_VERIFY,
                "connected demo verify failed")
        completed = 4
        demo_report = canonical.load_json(                    # step_005
            os.path.join(demo_out, "connected_demo_report.json"))
        observed = dict(demo_report.get("observed_statuses", {}))
        observed["connected_demo_status"] = demo_report.get("demo_status")
        truth_valid = _read_truth_boundary(demo_out)
        completed = 5
        for key, expected in versions.REQUIRED_STATUSES.items():  # step_006
            require(observed.get(key) == expected, FAILED_REQUIRED_STATUS_MISSING,
                    "required status missing or wrong: %s" % key)
        require(truth_valid is True, FAILED_TRUTH_BOUNDARY,
                "truth boundary not valid")
        completed = 6
        report = _build_report(observed, truth_valid, ONE_COMMAND_DEMO_COMPLETED)
        _write_outputs(out_dir, report, all_completed())      # step_007
        completed = 7
        verifier.verify(out_dir)                              # step_008
        completed = 8
        return ONE_COMMAND_DEMO_COMPLETED, report
    except CheckError as exc:
        failed_id = STEPS_ORDER[completed][0]
        report = _build_report(observed, truth_valid, exc.status)
        _write_outputs(out_dir, report, build_steps(completed, failed_id))
        return exc.status, report
    except VerifyError:
        report = _build_report(observed, truth_valid, FAILED_CHECKSUMS_INVALID)
        _write_outputs(out_dir, report, build_steps(7, "step_008"))
        return FAILED_CHECKSUMS_INVALID, report
