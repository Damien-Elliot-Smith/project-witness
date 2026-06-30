# histor_aletheia_importer/importer.py
# Orchestrate: verify the Aletheia bundle -> read manifest -> require
# VERIFIED_PRESENT -> write the four case files. Deterministic. The Aletheia
# integrity status is preserved exactly. The evidence file is NOT copied.

import os

from histor_aletheia_importer.aletheia_reader import (
    read_manifest, require_verified_present, SubprocessAletheiaVerifier)
from histor_aletheia_importer.canonical import canonical_bytes
from histor_aletheia_importer.checksums import format_checksums
from histor_aletheia_importer.errors import require, ComponentPathError
from histor_aletheia_importer.report import build_summary, build_replay_report
from histor_aletheia_importer.validation import sha256_bytes
from histor_aletheia_importer import versions


class ImportResult:
    __slots__ = ("out_dir", "summary")

    def __init__(self, out_dir, summary):
        self.out_dir = out_dir
        self.summary = summary


def _write_bytes(path, data: bytes):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def import_evidence(*, aletheia_root, bundle_dir, out_dir, aletheia_verifier=None):
    """Import a verified Aletheia bundle into a Histor-lite-style evidence case.
    Raises a typed error on failure. `aletheia_verifier` is injectable for tests.
    """
    # 1-2. Path existence.
    if not (isinstance(aletheia_root, str) and os.path.isdir(aletheia_root)):
        raise ComponentPathError("ALETHEIA_ROOT_MISSING",
                                 f"Aletheia root not found: {aletheia_root!r}")
    if not (isinstance(bundle_dir, str) and os.path.isdir(bundle_dir)):
        raise ComponentPathError("BUNDLE_MISSING",
                                 f"Aletheia bundle not found: {bundle_dir!r}")

    # 12. Refuse a non-empty output dir.
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        raise ComponentPathError("OUTPUT_DIR_NOT_EMPTY",
                                 f"output directory is not empty: {out_dir!r}")

    # 3-4. Verify the bundle with frozen Aletheia (injectable).
    if aletheia_verifier is None:
        aletheia_verifier = SubprocessAletheiaVerifier(aletheia_root)
    aletheia_verifier.verify(bundle_dir)  # raises AletheiaVerifyError on failure

    # 5-7. Read manifest; require VERIFIED_PRESENT.
    manifest = read_manifest(bundle_dir)
    require_verified_present(manifest)

    # The canonical manifest copy is what we record + hash (deterministic bytes).
    manifest_copy_bytes = canonical_bytes(manifest)
    manifest_sha = sha256_bytes(manifest_copy_bytes)

    # 9. Build the summary (preserving Aletheia's integrity status exactly).
    summary = build_summary(manifest=manifest, manifest_sha256=manifest_sha)
    summary_bytes = canonical_bytes(summary)

    # 10. Build the replay report.
    replay_text = build_replay_report(summary)
    replay_bytes = replay_text.encode("utf-8")

    # 8/9/10/11. Write all four files atomically.
    os.makedirs(out_dir, exist_ok=True)
    _write_bytes(os.path.join(out_dir, versions.SUMMARY_NAME), summary_bytes)
    _write_bytes(os.path.join(out_dir, versions.MANIFEST_COPY_NAME),
                 manifest_copy_bytes)
    _write_bytes(os.path.join(out_dir, versions.REPLAY_REPORT_NAME), replay_bytes)

    checksums = format_checksums(
        summary_sha256=sha256_bytes(summary_bytes),
        manifest_copy_sha256=manifest_sha,
        replay_report_sha256=sha256_bytes(replay_bytes))
    _write_bytes(os.path.join(out_dir, versions.CHECKSUMS_NAME), checksums)

    return ImportResult(out_dir, summary)
