# histor_odin_importer/importer.py
# Orchestrate: verify the ODIN run -> read the three ODIN files -> require an
# importable reasoning status -> copy the three files verbatim and write the case
# summary, replay report, and checksums. Deterministic. ODIN's reasoning status is
# preserved exactly. The copied files are byte-for-byte verbatim (not rewritten).

import os

from histor_odin_importer.canonical import canonical_bytes
from histor_odin_importer.checksums import format_checksums
from histor_odin_importer.errors import require, ComponentPathError
from histor_odin_importer.odin_reader import (
    read_run, require_importable_status, SubprocessOdinVerifier)
from histor_odin_importer.report import build_summary, build_replay_report
from histor_odin_importer.validation import sha256_bytes
from histor_odin_importer import versions


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


def import_reasoning(*, odin_root, run_dir, out_dir, odin_verifier=None):
    """Import a verified ODIN run into a Histor-lite-style reasoning case. Raises a
    typed error on failure. `odin_verifier` is injectable for tests."""
    # 1-2. Path existence.
    if not (isinstance(odin_root, str) and os.path.isdir(odin_root)):
        raise ComponentPathError("ODIN_ROOT_MISSING",
                                 f"ODIN root not found: {odin_root!r}")
    if not (isinstance(run_dir, str) and os.path.isdir(run_dir)):
        raise ComponentPathError("RUN_MISSING",
                                 f"ODIN run not found: {run_dir!r}")

    # 14. Refuse a non-empty output dir.
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        raise ComponentPathError("OUTPUT_DIR_NOT_EMPTY",
                                 f"output directory is not empty: {out_dir!r}")

    # 3-4. Verify the run with frozen ODIN (injectable).
    if odin_verifier is None:
        odin_verifier = SubprocessOdinVerifier(odin_root)
    odin_verifier.verify(run_dir)  # raises OdinVerifyError on failure

    # 5-9. Read the three files; require an importable reasoning status.
    run = read_run(run_dir)
    require_importable_status(run.report)

    # The copies are the EXACT source bytes (verbatim; not rewritten). ODIN output
    # is already canonical, so these are also canonical for verify's canonical check.
    report_sha = sha256_bytes(run.report_bytes)
    trace_sha = sha256_bytes(run.trace_bytes)
    claims_sha = sha256_bytes(run.claims_bytes)

    # 11. Build the summary (preserving ODIN's reasoning status exactly).
    summary = build_summary(
        report=run.report, trace=run.trace, claims=run.claims,
        claims_sha256=claims_sha, report_sha256=report_sha, trace_sha256=trace_sha)
    summary_bytes = canonical_bytes(summary)

    # 12. Build the replay report.
    replay_bytes = build_replay_report(summary).encode("utf-8")

    # 10-13. Write all six files atomically.
    os.makedirs(out_dir, exist_ok=True)
    _write_bytes(os.path.join(out_dir, versions.SUMMARY_NAME), summary_bytes)
    _write_bytes(os.path.join(out_dir, versions.REPORT_COPY_NAME),
                 run.report_bytes)
    _write_bytes(os.path.join(out_dir, versions.TRACE_COPY_NAME), run.trace_bytes)
    _write_bytes(os.path.join(out_dir, versions.CLAIMS_COPY_NAME),
                 run.claims_bytes)
    _write_bytes(os.path.join(out_dir, versions.REPLAY_REPORT_NAME), replay_bytes)

    checksums = format_checksums(
        summary_sha256=sha256_bytes(summary_bytes),
        report_copy_sha256=report_sha,
        trace_copy_sha256=trace_sha,
        claims_copy_sha256=claims_sha,
        replay_report_sha256=sha256_bytes(replay_bytes))
    _write_bytes(os.path.join(out_dir, versions.CHECKSUMS_NAME), checksums)

    return ImportResult(out_dir, summary)
