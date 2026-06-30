# aletheia_evidence/builder.py
# Build an evidence bundle from one local file. Deterministic except for the
# created_at_utc timestamp (which is recorded honestly, not hashed into the file
# names). Refuses if the copied file's hash does not match the source.

import datetime
import os
import shutil

from aletheia_evidence.canonical import canonical_bytes
from aletheia_evidence.checksums import format_checksums
from aletheia_evidence.errors import require, BuildError
from aletheia_evidence.hashing import sha256_file, sha256_bytes
from aletheia_evidence.manifest import build_manifest
from aletheia_evidence.validation import validate_id, validate_source_file
from aletheia_evidence import versions


class BuildResult:
    __slots__ = ("out_dir", "manifest", "evidence_status")

    def __init__(self, out_dir, manifest, evidence_status):
        self.out_dir = out_dir
        self.manifest = manifest
        self.evidence_status = evidence_status


def _utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _write_bytes(path, data: bytes):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def build_bundle(*, source_file, case_id, evidence_id, out_dir,
                 created_at_utc=None) -> BuildResult:
    """Build an evidence bundle. Raises ValidationError/BuildError on failure.

    The output directory must not already exist or must be empty.
    """
    case_id = validate_id(case_id, label="case_id")
    evidence_id = validate_id(evidence_id, label="evidence_id")
    size = validate_source_file(source_file)

    # Refuse a non-empty output directory (no silent overwrite/mixing).
    if os.path.isdir(out_dir):
        require(not os.listdir(out_dir),
                f"output directory is not empty: {out_dir!r}",
                BuildError, reason="OUTPUT_DIR_NOT_EMPTY")
    os.makedirs(out_dir, exist_ok=True)
    evidence_dir = os.path.join(out_dir, versions.EVIDENCE_DIRNAME)
    os.makedirs(evidence_dir, exist_ok=True)

    source_sha = sha256_file(source_file)
    bundled_path = os.path.join(evidence_dir, versions.BUNDLED_FILE_NAME)
    shutil.copyfile(source_file, bundled_path)  # copy contents only (no metadata)
    bundled_sha = sha256_file(bundled_path)

    # Integrity invariant at bundle time: the copy must match the source.
    require(bundled_sha == source_sha,
            f"bundled file hash {bundled_sha} != source hash {source_sha}",
            BuildError, reason="COPY_HASH_MISMATCH")

    manifest = build_manifest(
        case_id=case_id, evidence_id=evidence_id,
        source_file_name=os.path.basename(source_file),
        source_file_size_bytes=size, source_file_sha256=source_sha,
        bundled_file_sha256=bundled_sha,
        created_at_utc=created_at_utc or _utc_now_iso())

    manifest_bytes = canonical_bytes(manifest)
    _write_bytes(os.path.join(out_dir, versions.MANIFEST_NAME), manifest_bytes)
    manifest_sha = sha256_bytes(manifest_bytes)

    checksums_bytes = format_checksums(
        manifest_sha256=manifest_sha, bundled_sha256=bundled_sha)
    _write_bytes(os.path.join(out_dir, versions.CHECKSUMS_NAME), checksums_bytes)

    return BuildResult(out_dir, manifest, versions.EVIDENCE_VERIFIED_PRESENT)
