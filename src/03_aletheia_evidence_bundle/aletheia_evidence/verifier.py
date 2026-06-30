# aletheia_evidence/verifier.py
# Verify an evidence bundle's internal integrity. Returns VERIFIED_PRESENT only if
# every check passes. Proves preservation/hash consistency — NOT truth.

import json
import os

from aletheia_evidence.canonical import canonical_bytes
from aletheia_evidence.checksums import (
    parse_checksums, MANIFEST_KEY, BUNDLED_KEY)
from aletheia_evidence.errors import require, VerifyError
from aletheia_evidence.hashing import sha256_file, sha256_bytes
from aletheia_evidence.manifest import validate_manifest_shape
from aletheia_evidence import versions

# The exact set of files/dirs a v0.1 bundle may contain.
_ALLOWED_TOP_LEVEL = {versions.MANIFEST_NAME, versions.CHECKSUMS_NAME,
                      versions.EVIDENCE_DIRNAME}


class VerifyResult:
    __slots__ = ("bundle_dir", "evidence_status", "case_id", "evidence_id")

    def __init__(self, bundle_dir, evidence_status, case_id, evidence_id):
        self.bundle_dir = bundle_dir
        self.evidence_status = evidence_status
        self.case_id = case_id
        self.evidence_id = evidence_id


def verify_bundle(bundle_dir) -> VerifyResult:
    """Verify an evidence bundle. Raises VerifyError (carrying an evidence_status)
    on any failure; returns VerifyResult(VERIFIED_PRESENT) if all checks pass."""
    require(os.path.isdir(bundle_dir),
            f"bundle directory not found: {bundle_dir!r}",
            VerifyError, status=versions.EVIDENCE_FAILED_MISSING_FILE)

    manifest_path = os.path.join(bundle_dir, versions.MANIFEST_NAME)
    checksums_path = os.path.join(bundle_dir, versions.CHECKSUMS_NAME)
    evidence_dir = os.path.join(bundle_dir, versions.EVIDENCE_DIRNAME)
    bundled_path = os.path.join(evidence_dir, versions.BUNDLED_FILE_NAME)

    # 1. Required files exist.
    require(os.path.isfile(manifest_path),
            f"missing {versions.MANIFEST_NAME}", VerifyError,
            status=versions.EVIDENCE_FAILED_MISSING_FILE)
    require(os.path.isfile(checksums_path),
            f"missing {versions.CHECKSUMS_NAME}", VerifyError,
            status=versions.EVIDENCE_FAILED_MISSING_FILE)
    require(os.path.isdir(evidence_dir),
            f"missing {versions.EVIDENCE_DIRNAME}/ directory", VerifyError,
            status=versions.EVIDENCE_FAILED_MISSING_FILE)
    require(os.path.isfile(bundled_path),
            f"missing bundled evidence file {BUNDLED_KEY}", VerifyError,
            status=versions.EVIDENCE_FAILED_MISSING_FILE)

    # 2. Refuse unknown extra files (top level and inside evidence/).
    _refuse_unknown_files(bundle_dir, evidence_dir)

    # 3/4. Load manifest; check it is valid AND canonical.
    with open(manifest_path, "rb") as f:
        manifest_raw = f.read()
    try:
        manifest = json.loads(manifest_raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise VerifyError(versions.EVIDENCE_FAILED_MANIFEST_INVALID,
                          f"manifest is not valid JSON: {e}")
    require(canonical_bytes(manifest) == manifest_raw,
            "manifest is not in canonical form (possible tamper)",
            VerifyError, status=versions.EVIDENCE_FAILED_NON_CANONICAL_MANIFEST)
    validate_manifest_shape(manifest)

    # 5-8. Load + strictly parse checksums.
    with open(checksums_path, encoding="utf-8") as f:
        checksums = parse_checksums(f.read())

    # 9. Recompute manifest hash; 10. recompute bundled file hash.
    manifest_sha = sha256_bytes(manifest_raw)
    bundled_sha = sha256_file(bundled_path)

    # 11. checksum file must match actual files.
    require(checksums[MANIFEST_KEY] == manifest_sha,
            "manifest hash does not match checksums file", VerifyError,
            status=versions.EVIDENCE_FAILED_HASH_MISMATCH)
    require(checksums[BUNDLED_KEY] == bundled_sha,
            "bundled file hash does not match checksums file", VerifyError,
            status=versions.EVIDENCE_FAILED_HASH_MISMATCH)

    # 12. manifest bundled_file_sha256 must match actual bundled file.
    require(manifest["bundled_file_sha256"] == bundled_sha,
            "manifest bundled_file_sha256 does not match actual bundled file",
            VerifyError, status=versions.EVIDENCE_FAILED_HASH_MISMATCH)

    # 13. manifest source_file_sha256 must equal bundled_file_sha256.
    require(manifest["source_file_sha256"] == manifest["bundled_file_sha256"],
            "manifest source_file_sha256 != bundled_file_sha256",
            VerifyError, status=versions.EVIDENCE_FAILED_HASH_MISMATCH)

    # 14. All integrity checks passed.
    return VerifyResult(bundle_dir, versions.EVIDENCE_VERIFIED_PRESENT,
                        manifest["case_id"], manifest["evidence_id"])


def _refuse_unknown_files(bundle_dir, evidence_dir):
    bad = versions.EVIDENCE_FAILED_CHECKSUMS_INVALID
    top = set(os.listdir(bundle_dir))
    # Ignore the atomic-write temp files defensively (should never persist).
    top = {n for n in top if not n.endswith(".tmp")}
    unknown_top = top - _ALLOWED_TOP_LEVEL
    require(not unknown_top,
            f"unknown extra files in bundle: {sorted(unknown_top)}",
            VerifyError, status=bad)
    inside = set(os.listdir(evidence_dir))
    unknown_inside = inside - {versions.BUNDLED_FILE_NAME}
    require(not unknown_inside,
            f"unknown extra files in {versions.EVIDENCE_DIRNAME}/: "
            f"{sorted(unknown_inside)}", VerifyError, status=bad)
