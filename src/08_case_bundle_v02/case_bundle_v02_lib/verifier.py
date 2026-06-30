# case_bundle_v02_lib/verifier.py
# Verify a Case Bundle v0.2's internal integrity. Returns success only if every
# check passes. Proves the verified case records were bundled and checksummed — NOT
# truth of evidence or claims.

import json
import os

from case_bundle_v02_lib.canonical import canonical_bytes
from case_bundle_v02_lib.checksums import parse_checksums, REQUIRED_KEYS, MANIFEST_KEY
from case_bundle_v02_lib.errors import require, VerifyError
from case_bundle_v02_lib.input_verifiers import (
    _verify_two_token_checksums, _verify_three_token_checksums)
from case_bundle_v02_lib.validation import sha256_bytes, sha256_file, scan_truth
from case_bundle_v02_lib import versions

_ALLOWED_TOP = ({versions.MANIFEST_NAME, versions.CHECKSUMS_NAME}
                | set(versions.SUBFOLDERS))
_SUBCASE_FILES = {
    versions.SENTINEL_DIR: set(versions.SENTINEL_FILES),
    versions.ALETHEIA_DIR: set(versions.ALETHEIA_FILES),
    versions.ODIN_DIR: set(versions.ODIN_FILES),
}


class VerifyResult:
    __slots__ = ("bundle_dir", "bundle_status", "case_id",
                 "odin_reasoning_status", "aletheia_status")

    def __init__(self, bundle_dir, bundle_status, case_id, odin_reasoning_status,
                 aletheia_status):
        self.bundle_dir = bundle_dir
        self.bundle_status = bundle_status
        self.case_id = case_id
        self.odin_reasoning_status = odin_reasoning_status
        self.aletheia_status = aletheia_status


def _load_json(path, reason):
    require(os.path.isfile(path), f"missing {os.path.basename(path)}",
            VerifyError, reason=reason)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        raise VerifyError(reason, f"{os.path.basename(path)} not valid JSON: {e}")


def _read_text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8", errors="replace")


def verify_bundle(bundle_dir) -> VerifyResult:
    """Verify a Case Bundle v0.2. Raises VerifyError on any failure."""
    require(os.path.isdir(bundle_dir), f"bundle dir not found: {bundle_dir!r}",
            VerifyError, reason="BUNDLE_MISSING")

    manifest_path = os.path.join(bundle_dir, versions.MANIFEST_NAME)
    checksums_path = os.path.join(bundle_dir, versions.CHECKSUMS_NAME)

    # 1. Required top-level files and folders exist.
    for p in (manifest_path, checksums_path):
        require(os.path.isfile(p), f"missing {os.path.basename(p)}",
                VerifyError, reason="BUNDLE_FILE_MISSING")
    for sub in versions.SUBFOLDERS:
        require(os.path.isdir(os.path.join(bundle_dir, sub)),
                f"missing subfolder {sub}/", VerifyError,
                reason="SUBFOLDER_MISSING")

    # 2. Refuse unknown extra top-level files.
    top = {n for n in os.listdir(bundle_dir) if not n.endswith(".tmp")}
    require(not (top - _ALLOWED_TOP),
            f"unknown extra top-level entries: {sorted(top - _ALLOWED_TOP)}",
            VerifyError, reason="UNKNOWN_FILE")

    # 3-6. Required files in each subfolder; refuse unknown extra subfolder files.
    for sub, names in _SUBCASE_FILES.items():
        sub_dir = os.path.join(bundle_dir, sub)
        present = {n for n in os.listdir(sub_dir) if not n.endswith(".tmp")}
        for n in names:
            require(n in present, f"missing {sub}/{n}", VerifyError,
                    reason="SUBCASE_FILE_MISSING")
        require(not (present - names),
                f"unknown extra file(s) in {sub}/: {sorted(present - names)}",
                VerifyError, reason="UNKNOWN_SUBCASE_FILE")

    # 7-8. Load + canonical-check the manifest.
    with open(manifest_path, "rb") as f:
        manifest_raw = f.read()
    try:
        manifest = json.loads(manifest_raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise VerifyError("MANIFEST_NON_CANONICAL",
                          f"case_manifest.json not valid JSON: {e}")
    require(canonical_bytes(manifest) == manifest_raw,
            "case_manifest.json is not in canonical form (possible tamper)",
            VerifyError, reason="MANIFEST_NON_CANONICAL")

    # 9-13. Strict bundle checksums parse (uppercase rejected in parse).
    with open(checksums_path, encoding="utf-8") as f:
        checksums = parse_checksums(f.read())

    # 14. Recompute all bundle-level hashes.
    require(checksums[MANIFEST_KEY] == sha256_bytes(manifest_raw),
            "case_manifest.json hash mismatch", VerifyError, reason="HASH_MISMATCH")
    for key in REQUIRED_KEYS:
        if key == MANIFEST_KEY:
            continue
        target = os.path.join(bundle_dir, key)
        require(os.path.isfile(target), f"checksums reference missing {key}",
                VerifyError, reason="HASH_MISMATCH")
        require(checksums[key] == sha256_file(target),
                f"bundle hash mismatch for {key}", VerifyError,
                reason="HASH_MISMATCH")

    # 15-17. Verify each subcase's INTERNAL checksums (their own formats). Any
    # mismatch is mapped to the FAILED_*_CASE_VERIFY-style reason via VerifyError.
    sentinel_dir = os.path.join(bundle_dir, versions.SENTINEL_DIR)
    aletheia_dir = os.path.join(bundle_dir, versions.ALETHEIA_DIR)
    odin_dir = os.path.join(bundle_dir, versions.ODIN_DIR)
    try:
        _verify_three_token_checksums(sentinel_dir, versions.SENTINEL_CHECKSUMS,
                                      versions.FAILED_SENTINEL_CASE_VERIFY)
    except Exception as e:  # noqa: BLE001
        raise VerifyError("INTERNAL_SENTINEL_CHECKSUM_MISMATCH", str(e))
    try:
        _verify_two_token_checksums(aletheia_dir, versions.ALETHEIA_CHECKSUMS,
                                    versions.FAILED_ALETHEIA_CASE_VERIFY)
    except Exception as e:  # noqa: BLE001
        raise VerifyError("INTERNAL_ALETHEIA_CHECKSUM_MISMATCH", str(e))
    try:
        _verify_two_token_checksums(odin_dir, versions.ODIN_CHECKSUMS,
                                    versions.FAILED_ODIN_CASE_VERIFY)
    except Exception as e:  # noqa: BLE001
        raise VerifyError("INTERNAL_ODIN_CHECKSUM_MISMATCH", str(e))

    # Load the three subcase summaries for cross-checks.
    sentinel_summary = _load_json(
        os.path.join(sentinel_dir, versions.SENTINEL_SUMMARY), "SUBCASE_FILE_MISSING")
    aletheia_summary = _load_json(
        os.path.join(aletheia_dir, versions.ALETHEIA_SUMMARY), "SUBCASE_FILE_MISSING")
    odin_summary = _load_json(
        os.path.join(odin_dir, versions.ODIN_SUMMARY), "SUBCASE_FILE_MISSING")

    # 18. All three case IDs match case_manifest.case_id.
    case_id = manifest.get("case_id")
    require(sentinel_summary.get("case_id") == case_id,
            "Sentinel case_id != manifest case_id", VerifyError,
            reason="CASE_ID_MISMATCH")
    require(aletheia_summary.get("case_id") == case_id,
            "Aletheia case_id != manifest case_id", VerifyError,
            reason="CASE_ID_MISMATCH")
    require(odin_summary.get("case_id") == case_id,
            "ODIN case_id != manifest case_id", VerifyError,
            reason="CASE_ID_MISMATCH")

    # 19. bundle_status == BUNDLED_VERIFIED_CASE.
    require(manifest.get("bundle_status") == versions.BUNDLED_VERIFIED_CASE,
            f"bundle_status {manifest.get('bundle_status')!r} != "
            f"{versions.BUNDLED_VERIFIED_CASE}", VerifyError,
            reason="BUNDLE_STATUS_INVALID")

    # 20. Aletheia status is VERIFIED_PRESENT (manifest + subcase summary).
    require(manifest.get("aletheia", {}).get("source_evidence_status")
            == versions.ALETHEIA_VERIFIED_PRESENT,
            "manifest aletheia.source_evidence_status != VERIFIED_PRESENT",
            VerifyError, reason="ALETHEIA_STATUS_INVALID")
    require(aletheia_summary.get("source_evidence_status")
            == versions.ALETHEIA_VERIFIED_PRESENT,
            "Aletheia subcase source_evidence_status != VERIFIED_PRESENT",
            VerifyError, reason="ALETHEIA_STATUS_INVALID")

    # 21-22. ODIN status is CONSISTENT or CONTRADICTION_DETECTED; INVALID_INPUT
    # refused (manifest + subcase summary).
    odin_status = manifest.get("odin", {}).get("source_reasoning_status")
    require(odin_status != versions.ODIN_INVALID_INPUT,
            "ODIN status is INVALID_INPUT (not packageable)", VerifyError,
            reason="ODIN_INVALID_INPUT")
    require(odin_status in versions.ODIN_IMPORTABLE_STATUSES,
            f"ODIN status {odin_status!r} is not packageable", VerifyError,
            reason="ODIN_STATUS_INVALID")
    require(odin_summary.get("source_reasoning_status") == odin_status,
            "ODIN subcase status != manifest odin.source_reasoning_status",
            VerifyError, reason="ODIN_STATUS_MISMATCH")

    # 23. No truth-like claim in the bundle manifest.
    scan_truth(json.dumps(manifest, ensure_ascii=False), "case_manifest.json")

    # 24. No truth-like claim in any packaged replay report.
    scan_truth(_read_text(os.path.join(sentinel_dir, versions.SENTINEL_REPLAY)),
               "sentinel_replay_report.txt")
    scan_truth(_read_text(os.path.join(aletheia_dir, versions.ALETHEIA_REPLAY)),
               "aletheia_replay_report.txt")
    scan_truth(_read_text(os.path.join(odin_dir, versions.ODIN_REPLAY)),
               "odin_replay_report.txt")

    # 25. All checks passed.
    return VerifyResult(bundle_dir, manifest.get("bundle_status"), case_id,
                        odin_status,
                        manifest.get("aletheia", {}).get("source_evidence_status"))
