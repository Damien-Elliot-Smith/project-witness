# case_bundle_v02_lib/input_verifiers.py
# Verify each input case folder's internal integrity before bundling. Each frozen
# producer uses a slightly different checksums format, so each verifier knows its
# own producer's real file names and checksum line format. These are in-process
# format/hash checks (no subprocess), and the build wires them in via an injectable
# verifier object so the default test suite is not subprocess-heavy.
#
# Sentinel (Histor-lite v0.1.2) checksums.txt line format:  <key>  <digest>  <name>
#   and includes a source_run_sha256 line for a file OUTSIDE the case folder.
# Aletheia / ODIN importer checksums line format:           <digest>  <name>

import json
import os

from case_bundle_v02_lib.errors import require, InputCaseError
from case_bundle_v02_lib.validation import is_valid_sha256, sha256_file
from case_bundle_v02_lib import versions


def _read_json(path, status, reason):
    require(os.path.isfile(path), f"missing {os.path.basename(path)}",
            InputCaseError, bundle_status=status, reason=reason)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        raise InputCaseError(status, reason,
                             f"{os.path.basename(path)} not valid JSON: {e}")


def _require_files(case_dir, names, status):
    require(os.path.isdir(case_dir), f"case folder not found: {case_dir!r}",
            InputCaseError, bundle_status=status, reason="CASE_MISSING")
    for n in names:
        require(os.path.isfile(os.path.join(case_dir, n)),
                f"missing required file {n} in {os.path.basename(case_dir)}",
                InputCaseError, bundle_status=status, reason="CASE_FILE_MISSING")


def _verify_two_token_checksums(case_dir, checksums_name, status):
    """Verify a <digest>  <name> checksums file by recomputing in-folder hashes."""
    path = os.path.join(case_dir, checksums_name)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    seen = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split("  ", 1)
        require(len(parts) == 2, f"malformed checksum line in {checksums_name}",
                InputCaseError, bundle_status=status, reason="CHECKSUMS_MALFORMED")
        digest, name = parts[0].strip(), parts[1].strip()
        require(is_valid_sha256(digest),
                f"bad digest in {checksums_name}: {digest!r}", InputCaseError,
                bundle_status=status, reason="CHECKSUMS_MALFORMED")
        target = os.path.join(case_dir, name)
        require(os.path.isfile(target),
                f"{checksums_name} references missing file {name}", InputCaseError,
                bundle_status=status, reason="CHECKSUMS_FILE_MISSING")
        require(sha256_file(target) == digest,
                f"internal checksum mismatch for {name}", InputCaseError,
                bundle_status=status, reason="INTERNAL_CHECKSUM_MISMATCH")
        seen.add(name)
    return seen


def _verify_three_token_checksums(case_dir, checksums_name, status):
    """Verify a <key>  <digest>  <name> checksums file (Sentinel). Lines whose
    referenced file is not present in the case folder (e.g. the external source
    run) are skipped for hash recomputation but still format-checked."""
    path = os.path.join(case_dir, checksums_name)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        require(len(parts) == 3,
                f"malformed Sentinel checksum line in {checksums_name}",
                InputCaseError, bundle_status=status, reason="CHECKSUMS_MALFORMED")
        _key, digest, name = parts
        require(is_valid_sha256(digest),
                f"bad digest in {checksums_name}: {digest!r}", InputCaseError,
                bundle_status=status, reason="CHECKSUMS_MALFORMED")
        target = os.path.join(case_dir, name)
        if os.path.isfile(target):
            require(sha256_file(target) == digest,
                    f"internal checksum mismatch for {name}", InputCaseError,
                    bundle_status=status, reason="INTERNAL_CHECKSUM_MISMATCH")


class InProcessInputVerifier:
    """Verifies the three input case folders using in-process format/hash checks.
    Returns a dict of extracted facts per case (status fields + case_id)."""

    def verify_sentinel(self, case_dir):
        st = versions.FAILED_SENTINEL_CASE_VERIFY
        _require_files(case_dir, versions.SENTINEL_FILES, st)
        _verify_three_token_checksums(case_dir, versions.SENTINEL_CHECKSUMS, st)
        summary = _read_json(os.path.join(case_dir, versions.SENTINEL_SUMMARY),
                            st, "SUMMARY_INVALID")
        require("case_id" in summary, "Sentinel summary missing case_id",
                InputCaseError, bundle_status=st, reason="SUMMARY_INVALID")
        return {
            "case_id": summary.get("case_id"),
            "case_status": summary.get("import_status"),
            "action_status": summary.get("sentinel_replay_verdict"),
            "source_component": versions.SENTINEL_SOURCE_COMPONENT,
        }

    def verify_aletheia(self, case_dir):
        st = versions.FAILED_ALETHEIA_CASE_VERIFY
        _require_files(case_dir, versions.ALETHEIA_FILES, st)
        _verify_two_token_checksums(case_dir, versions.ALETHEIA_CHECKSUMS, st)
        summary = _read_json(os.path.join(case_dir, versions.ALETHEIA_SUMMARY),
                            st, "SUMMARY_INVALID")
        require("case_id" in summary, "Aletheia summary missing case_id",
                InputCaseError, bundle_status=st, reason="SUMMARY_INVALID")
        return {
            "case_id": summary.get("case_id"),
            "import_status": summary.get("import_status"),
            "source_evidence_status": summary.get("source_evidence_status"),
            "source_component": versions.ALETHEIA_SOURCE_COMPONENT,
        }

    def verify_odin(self, case_dir):
        st = versions.FAILED_ODIN_CASE_VERIFY
        _require_files(case_dir, versions.ODIN_FILES, st)
        _verify_two_token_checksums(case_dir, versions.ODIN_CHECKSUMS, st)
        summary = _read_json(os.path.join(case_dir, versions.ODIN_SUMMARY),
                            st, "SUMMARY_INVALID")
        require("case_id" in summary, "ODIN summary missing case_id",
                InputCaseError, bundle_status=st, reason="SUMMARY_INVALID")
        status = summary.get("source_reasoning_status")
        # INVALID_INPUT is never packageable.
        require(status != versions.ODIN_INVALID_INPUT,
                "ODIN case is INVALID_INPUT; not packageable", InputCaseError,
                bundle_status=st, reason="ODIN_INVALID_INPUT")
        require(status in versions.ODIN_IMPORTABLE_STATUSES,
                f"ODIN reasoning status {status!r} is not packageable",
                InputCaseError, bundle_status=st, reason="ODIN_STATUS_INVALID")
        return {
            "case_id": summary.get("case_id"),
            "import_status": summary.get("import_status"),
            "source_reasoning_status": status,
            "claim_count": summary.get("claim_count"),
            "contradiction_count": summary.get("contradiction_count"),
            "source_component": versions.ODIN_SOURCE_COMPONENT,
        }
