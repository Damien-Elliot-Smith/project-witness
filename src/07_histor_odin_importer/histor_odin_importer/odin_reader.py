# histor_odin_importer/odin_reader.py
# Read + validate a frozen ODIN run (reasoning_report / proof_trace /
# claims_canonical), and provide the subprocess boundary to frozen ODIN's `verify`.
# The runner is injectable so unit tests use an in-process fake.

import json
import os
import subprocess
import sys

from histor_odin_importer.errors import (
    require, OdinRunError, ComponentPathError, OdinVerifyError)
from histor_odin_importer.validation import validate_id
from histor_odin_importer import versions

ODIN_CLI = "odin.py"


def _load_json(path, missing_reason, malformed_reason):
    require(os.path.isfile(path), f"missing {os.path.basename(path)} in ODIN run",
            OdinRunError, reason=missing_reason)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        raise OdinRunError(malformed_reason,
                           f"{os.path.basename(path)} is not valid JSON: {e}")


class OdinRun:
    __slots__ = ("report", "trace", "claims", "report_bytes", "trace_bytes",
                 "claims_bytes")

    def __init__(self, report, trace, claims, report_bytes, trace_bytes,
                 claims_bytes):
        self.report = report
        self.trace = trace
        self.claims = claims
        self.report_bytes = report_bytes
        self.trace_bytes = trace_bytes
        self.claims_bytes = claims_bytes


def read_run(run_dir) -> OdinRun:
    """Load + validate the three ODIN run files. Raises OdinRunError on any
    problem. The status-importability check is done separately."""
    report_path = os.path.join(run_dir, versions.ODIN_REPORT_NAME)
    trace_path = os.path.join(run_dir, versions.ODIN_TRACE_NAME)
    claims_path = os.path.join(run_dir, versions.ODIN_CLAIMS_NAME)

    report = _load_json(report_path, "REPORT_MISSING", "REPORT_MALFORMED")
    trace = _load_json(trace_path, "PROOF_TRACE_MISSING", "PROOF_TRACE_MALFORMED")
    claims = _load_json(claims_path, "CLAIMS_MISSING", "CLAIMS_MALFORMED")

    validate_report(report)
    validate_trace(trace)
    validate_claims(claims)

    # The exact source bytes (for verbatim copies + hashing).
    with open(report_path, "rb") as f:
        report_bytes = f.read()
    with open(trace_path, "rb") as f:
        trace_bytes = f.read()
    with open(claims_path, "rb") as f:
        claims_bytes = f.read()
    return OdinRun(report, trace, claims, report_bytes, trace_bytes, claims_bytes)


def validate_report(report) -> dict:
    require(isinstance(report, dict), "reasoning_report must be a JSON object",
            OdinRunError, reason="REPORT_INVALID")
    for f in ("case_id", "reasoning_status", "claim_count",
              "contradiction_count"):
        require(f in report, f"reasoning_report missing field {f!r}",
                OdinRunError, reason="REPORT_INVALID")
    validate_id(report["case_id"], label="case_id")
    require(isinstance(report["reasoning_status"], str),
            "reasoning_status must be a string", OdinRunError,
            reason="REPORT_INVALID")
    for f in ("claim_count", "contradiction_count"):
        require(isinstance(report[f], int) and report[f] >= 0,
                f"reasoning_report {f} must be a non-negative integer",
                OdinRunError, reason="REPORT_INVALID")
    return report


def validate_trace(trace) -> dict:
    require(isinstance(trace, dict), "proof_trace must be a JSON object",
            OdinRunError, reason="PROOF_TRACE_INVALID")
    require("case_id" in trace, "proof_trace missing case_id",
            OdinRunError, reason="PROOF_TRACE_INVALID")
    require(isinstance(trace.get("steps"), list),
            "proof_trace steps must be a list", OdinRunError,
            reason="PROOF_TRACE_INVALID")
    return trace


def validate_claims(claims) -> dict:
    require(isinstance(claims, dict), "claims_canonical must be a JSON object",
            OdinRunError, reason="REPORT_INVALID")
    require("case_id" in claims, "claims_canonical missing case_id",
            OdinRunError, reason="REPORT_INVALID")
    require(isinstance(claims.get("claims"), list),
            "claims_canonical claims must be a list", OdinRunError,
            reason="REPORT_INVALID")
    return claims


def require_importable_status(report) -> None:
    status = report["reasoning_status"]
    require(status != versions.ODIN_INVALID_INPUT,
            f"ODIN reasoning_status {status!r} is INVALID_INPUT; not importable",
            OdinRunError, reason="REASONING_STATUS_INVALID")
    require(status in versions.IMPORTABLE_REASONING_STATUSES,
            f"ODIN reasoning_status {status!r} is not importable "
            f"(must be CONSISTENT or CONTRADICTION_DETECTED)",
            OdinRunError, reason="REASONING_STATUS_INVALID")


class SubprocessOdinVerifier:
    """Runs frozen ODIN `verify --run` as a subprocess."""

    def __init__(self, odin_root):
        self._root = odin_root

    def verify(self, run_dir):
        cli = os.path.join(self._root, ODIN_CLI)
        require(os.path.isfile(cli), f"ODIN CLI not found: {cli!r}",
                ComponentPathError, reason="ODIN_CLI_MISSING")
        argv = [sys.executable, cli, "verify", "--run", run_dir]
        new_session = {"start_new_session": True} if os.name == "posix" else {}
        try:
            proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL, close_fds=True, text=True, **new_session)
            out, err = proc.communicate(timeout=120)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass
            raise OdinVerifyError("ODIN_VERIFY_TIMEOUT", "ODIN verify timed out")
        except OSError as e:
            raise OdinVerifyError("ODIN_VERIFY_SPAWN_FAILED", str(e))
        if rc != 0:
            raise OdinVerifyError(
                "ODIN_VERIFY_FAILED",
                f"ODIN verify failed (rc={rc}): "
                f"{(err or out or '').strip().splitlines()[-1:]}")
        return True
