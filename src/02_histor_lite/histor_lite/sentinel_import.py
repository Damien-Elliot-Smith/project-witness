# histor_lite/sentinel_import.py
# Orchestrates: Sentinel run file -> verify via frozen Sentinel -> write case.

import os

from histor_lite.canonical import canonical_bytes, hash_file
from histor_lite.errors import require, ImportRefused, VerifierUnavailable
from histor_lite.verifier import run_sentinel_replay
from histor_lite import versions
from histor_lite.case_summary import (
    build_case_summary, render_checksums, utc_now_iso,
    CASE_SUMMARY_NAME, REPLAY_REPORT_NAME, CHECKSUMS_NAME,
)


class ImportResult:
    __slots__ = ("case_dir", "case_summary", "verdict", "import_status")

    def __init__(self, case_dir, case_summary, verdict, import_status):
        self.case_dir = case_dir
        self.case_summary = case_summary
        self.verdict = verdict
        self.import_status = import_status


def _atomic_write_bytes(path, data: bytes):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def import_sentinel_run(*, sentinel_root, run_path, out_dir, now_utc=None):
    """Import one Sentinel v0.2.2 run.

    Steps (per spec): check root, check verifier module, check run file, hash the
    run, run Sentinel replay, accept only the two PASS verdicts, refuse the rest,
    and write the case folder. Returns an ImportResult on success.

    Raises:
      VerifierUnavailable  - root/verifier missing, or the verifier could not run.
      ImportRefused        - missing/malformed run, or a refused verdict
                             (FAIL / REPLAY_INCOMPATIBLE / unexpected).
    """
    # 1-2. root + verifier module existence are checked inside run_sentinel_replay
    #      (raising VerifierUnavailable). We also pre-check the run file here.
    # 3. run file exists.
    if not os.path.isfile(run_path):
        raise ImportRefused("RUN_FILE_MISSING", f"Run file not found: {run_path!r}")

    # 4. SHA-256 of the run file (computed before any verdict so it is recorded
    #    even on refusal paths the caller may log).
    source_run_sha256 = hash_file(run_path)

    # 5. Run Sentinel replay/verification (may raise VerifierUnavailable).
    verdict_obj = run_sentinel_replay(sentinel_root, run_path)
    verdict = verdict_obj.verdict

    # 6-7. Accept only the two PASS verdicts, AND only when the verifier's own
    #      ok flag agrees. A verdict that LOOKS accepted but carries ok=False is
    #      internally contradictory: trusting the verdict string while ignoring
    #      ok would import a case the verifier itself did not bless. Refuse it.
    import_status = versions.status_for_verdict(verdict)
    if import_status is not None and verdict_obj.ok is not True:
        raise ImportRefused(
            "SENTINEL_VERDICT_INCONSISTENT",
            f"Refusing import: Sentinel verifier returned verdict {verdict!r} but "
            f"ok={verdict_obj.ok!r}. An accepted verdict must have ok=True; this "
            f"result is internally inconsistent.")
    if import_status is None:
        if verdict == versions.VERDICT_FAIL:
            reason = "SENTINEL_REPLAY_FAIL"
        elif verdict == versions.VERDICT_REPLAY_INCOMPATIBLE:
            reason = "SENTINEL_REPLAY_INCOMPATIBLE"
        else:
            reason = "SENTINEL_VERDICT_UNRECOGNISED"
        raise ImportRefused(
            reason,
            f"Refusing import: Sentinel replay verdict {verdict!r} is not "
            f"accepted. Only PASS_STRICT and PASS_WITH_ENVIRONMENTAL_EXCEPTIONS "
            f"are imported.")

    # 8. Write the case folder.
    verified_at = now_utc or utc_now_iso()
    summary = build_case_summary(
        source_run_path=os.path.abspath(run_path),
        source_run_sha256=source_run_sha256,
        verdict=verdict,                 # preserved EXACTLY
        ok=verdict_obj.ok,
        import_status=import_status,
        verified_at_utc=verified_at,
    )

    os.makedirs(out_dir, exist_ok=True)
    summary_path = os.path.join(out_dir, CASE_SUMMARY_NAME)
    report_path = os.path.join(out_dir, REPLAY_REPORT_NAME)
    checksums_path = os.path.join(out_dir, CHECKSUMS_NAME)

    summary_bytes = canonical_bytes(summary)
    report_bytes = (verdict_obj.report or "").encode("utf-8")
    if not report_bytes.endswith(b"\n"):
        report_bytes += b"\n"

    _atomic_write_bytes(summary_path, summary_bytes)
    _atomic_write_bytes(report_path, report_bytes)

    checksums_text = render_checksums(
        source_run_sha256=source_run_sha256,
        source_run_label=os.path.basename(run_path),
        case_summary_sha256=hash_file(summary_path),
        replay_report_sha256=hash_file(report_path),
    )
    _atomic_write_bytes(checksums_path, checksums_text.encode("utf-8"))

    return ImportResult(out_dir, summary, verdict, import_status)
