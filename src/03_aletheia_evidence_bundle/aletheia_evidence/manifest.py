# aletheia_evidence/manifest.py
# Build and structurally validate the evidence_manifest dict.

from aletheia_evidence.errors import require, VerifyError
from aletheia_evidence.hashing import is_valid_sha256
from aletheia_evidence import versions

# Exact manifest field set (no more, no less) for v0.1.
MANIFEST_FIELDS = (
    "aletheia_evidence_bundle_version",
    "case_id",
    "evidence_id",
    "source_file_name",
    "source_file_size_bytes",
    "source_file_sha256",
    "bundled_file_path",
    "bundled_file_sha256",
    "bundle_status",
    "evidence_status",
    "created_at_utc",
    "known_limitations",
)


def build_manifest(*, case_id, evidence_id, source_file_name,
                   source_file_size_bytes, source_file_sha256,
                   bundled_file_sha256, created_at_utc) -> dict:
    """Assemble the manifest dict. The recorded evidence_status is the honest
    integrity verdict at bundle time (VERIFIED_PRESENT once hashes agree)."""
    return {
        "aletheia_evidence_bundle_version":
            versions.ALETHEIA_EVIDENCE_BUNDLE_VERSION,
        "case_id": case_id,
        "evidence_id": evidence_id,
        "source_file_name": source_file_name,
        "source_file_size_bytes": source_file_size_bytes,
        "source_file_sha256": source_file_sha256,
        "bundled_file_path":
            f"{versions.EVIDENCE_DIRNAME}/{versions.BUNDLED_FILE_NAME}",
        "bundled_file_sha256": bundled_file_sha256,
        "bundle_status": versions.BUNDLE_STATUS_BUNDLED,
        "evidence_status": versions.EVIDENCE_VERIFIED_PRESENT,
        "created_at_utc": created_at_utc,
        "known_limitations": list(versions.KNOWN_LIMITATIONS),
    }


def validate_manifest_shape(manifest) -> None:
    """Structural validation of a loaded manifest. Raises
    VerifyError(FAILED_MANIFEST_INVALID) on any structural problem."""
    bad = versions.EVIDENCE_FAILED_MANIFEST_INVALID
    require(isinstance(manifest, dict), "manifest is not a JSON object",
            VerifyError, status=bad)
    keys = set(manifest.keys())
    expected = set(MANIFEST_FIELDS)
    require(keys == expected,
            f"manifest fields mismatch: missing={sorted(expected - keys)}, "
            f"unknown={sorted(keys - expected)}", VerifyError, status=bad)

    require(manifest["aletheia_evidence_bundle_version"]
            == versions.ALETHEIA_EVIDENCE_BUNDLE_VERSION,
            "manifest version mismatch", VerifyError, status=bad)
    require(manifest["bundle_status"] == versions.BUNDLE_STATUS_BUNDLED,
            f"unexpected bundle_status {manifest['bundle_status']!r}",
            VerifyError, status=bad)
    require(manifest["bundled_file_path"]
            == f"{versions.EVIDENCE_DIRNAME}/{versions.BUNDLED_FILE_NAME}",
            "unexpected bundled_file_path", VerifyError, status=bad)
    for f in ("case_id", "evidence_id", "source_file_name", "created_at_utc"):
        require(isinstance(manifest[f], str) and manifest[f] != "",
                f"manifest field {f} must be a non-empty string",
                VerifyError, status=bad)
    require(isinstance(manifest["source_file_size_bytes"], int)
            and manifest["source_file_size_bytes"] >= 0,
            "source_file_size_bytes must be a non-negative integer",
            VerifyError, status=bad)
    for f in ("source_file_sha256", "bundled_file_sha256"):
        require(is_valid_sha256(manifest[f]),
                f"manifest field {f} is not a valid sha256",
                VerifyError, status=bad)
    require(isinstance(manifest["known_limitations"], list)
            and all(isinstance(x, str) for x in manifest["known_limitations"]),
            "known_limitations must be a list of strings",
            VerifyError, status=bad)
    # The recorded evidence_status must be the integrity-pass value; a stored
    # failure status is not a valid bundle.
    require(manifest["evidence_status"] == versions.EVIDENCE_VERIFIED_PRESENT,
            f"manifest evidence_status {manifest['evidence_status']!r} is not "
            f"{versions.EVIDENCE_VERIFIED_PRESENT}", VerifyError, status=bad)
