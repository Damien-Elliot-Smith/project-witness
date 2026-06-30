# sentinel_core/replay.py
# Manifest-based deterministic replay.
#
# Replay has TWO independent jobs, kept conceptually separate:
#
#   (A) TAMPER-EVIDENCE. Every saved receipt is reloaded and its canonical_hash
#       is recomputed (ReceiptChain.from_receipts_list raises on mismatch). The
#       chain linkage and, for closed runs, the run seal are verified. Any
#       mutation of target_path, allowed_root, decision, a deleted receipt, or a
#       deleted/edited seal is caught here BEFORE any re-execution. This is the
#       integrity guarantee.
#
#   (B) REPRODUCIBILITY. A fresh kernel is built and each saved request is fed
#       back through it against a sandbox filesystem reconstructed to be
#       consistent with the recorded decisions. The freshly derived
#       (decision, reason_code, executed) is compared to the saved one for every
#       receipt. This confirms the saved decisions are reproducible decisions of
#       the current kernel logic, not just stored strings.
#
# Why not exact hash-identity on re-run? A successful CREATE_DIRECTORY is not
# idempotent, and the original absolute allowed_root plus any pre-existing
# external directories are not reconstructable from the manifest. Re-execution
# therefore happens against a sandbox manifest root. Since v1.1.0 requests
# carry no allowed_root, saved requests are replayed byte-for-byte unchanged;
# only the manifest root is repointed at the sandbox. Receipts whose detail
# embeds resolved absolute paths still legitimately differ in hash, so job (B)
# compares the (decision, reason_code, executed) projection. Hash-identity is
# provided by job (A) on the SAVED receipts. KNOWN_LIMITATIONS documents this
# contract precisely. We do not claim more than this.

import os
import shutil
import tempfile
from typing import Tuple

from sentinel_core.errors import ManifestError, ReplayIncompatible
from sentinel_core.journal import Journal
from sentinel_core.kernel import Kernel
from sentinel_core.manifest import (
    validate_manifest, load_run_file, clone_manifest_run_data, compute_manifest_hash,
)
from sentinel_core.receipts import ReceiptChain
from sentinel_core.run_seal import validate_run_seal
from sentinel_core.persistence import VolatileTestBackend
from sentinel_core.reason_codes import (
    ALLOW_CREATE_DIRECTORY, DRY_RUN_CREATE_DIRECTORY, BLOCK_TARGET_ALREADY_EXISTS,
    INTENT_CREATE_DIRECTORY,
)
from sentinel_core.action_schema import ACTION_CREATE_DIRECTORY

MAX_REPLAY_RECEIPTS = 10000
MAX_RUN_FILE_BYTES = 10 * 1024 * 1024

# ── Replay verdict categories (v0.2.2) ──────────────────────────────────────
# The verdict distinguishes a run that re-derived strictly from one that only
# passed because an environmental ERROR receipt (ERROR_EXECUTION_FAILED /
# ERROR_POSTCONDITION_FAILED) was accepted STRUCTURALLY rather than reproduced.
# Under unkeyed hashes a forged ERROR is indistinguishable from a real one, so a
# run that leans on that structural acceptance must NOT report the same verdict
# as a strictly re-derived run.
VERDICT_PASS_STRICT = "PASS_STRICT"
VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS = "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS"
VERDICT_FAIL = "FAIL"
VERDICT_REPLAY_INCOMPATIBLE = "REPLAY_INCOMPATIBLE"

# Verdicts for which the process exit code is 0 (the run is accepted).
_OK_VERDICTS = frozenset({VERDICT_PASS_STRICT, VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS})


class ReplayResult:
    """Outcome of a replay.

    Backward-compatible: unpacks as the historical ``(ok, report)`` 2-tuple and
    is truthy when accepted, so existing callers keep working. New callers read
    ``.verdict`` for the v0.2.2 category.
    """
    __slots__ = ("ok", "verdict", "report")

    def __init__(self, ok: bool, verdict: str, report: str):
        self.ok = ok
        self.verdict = verdict
        self.report = report

    def __iter__(self):
        # Preserves `ok, report = replay_from_path(...)`.
        return iter((self.ok, self.report))

    def __bool__(self):
        return self.ok

    def __repr__(self):
        return f"ReplayResult(ok={self.ok!r}, verdict={self.verdict!r})"


def _fail(report: str) -> ReplayResult:
    return ReplayResult(False, VERDICT_FAIL, report)


def _incompatible(report: str) -> ReplayResult:
    return ReplayResult(False, VERDICT_REPLAY_INCOMPATIBLE, report)


# Decisions that imply the parent directory existed at original time.
_IMPLIES_PARENT_EXISTED = frozenset({
    INTENT_CREATE_DIRECTORY, ALLOW_CREATE_DIRECTORY,
    DRY_RUN_CREATE_DIRECTORY, BLOCK_TARGET_ALREADY_EXISTS,
})


def replay_from_path(path: str, allow_open: bool = False,
                     max_receipts: int = MAX_REPLAY_RECEIPTS) -> "ReplayResult":
    if not os.path.exists(path):
        return _fail(f"Run file not found: {path!r}")
    try:
        if os.path.getsize(path) > MAX_RUN_FILE_BYTES:
            return _fail(f"Run file exceeds MAX_RUN_FILE_BYTES={MAX_RUN_FILE_BYTES}")
    except OSError as e:
        return _fail(f"Failed to stat run file: {e}")
    try:
        raw_data = load_run_file(path)
    except ManifestError as e:
        return _fail(f"Failed to load run file: {e}")
    return _replay_data(raw_data, path, allow_open=allow_open, max_receipts=max_receipts)


def _sandbox_path_for(sandbox_root: str, original_root: str, target_path: str) -> str:
    """Map an original target into the sandbox, preserving relative structure.

    Relative targets keep their structure under the sandbox root. Absolute
    targets are mapped by their position relative to the ORIGINAL manifest
    root (an absolute target outside the original root maps outside the
    sandbox too, reproducing the original block decision).
    """
    if os.path.isabs(target_path):
        rel = os.path.relpath(os.path.normpath(target_path), os.path.normpath(original_root))
    else:
        rel = os.path.normpath(target_path)
    return os.path.normpath(os.path.join(sandbox_root, rel))


def _reconstruct_context(sandbox_root: str, original_root: str, saved_receipt) -> None:
    """Make the sandbox consistent with one saved receipt's recorded decision.

    Uses ONLY the recorded decision to recreate pre-existing external structure
    that the manifest does not capture (e.g. a parent directory that existed on
    the original machine but was not created by Sentinel). This deliberately
    trusts the recorded decision for context reconstruction; tamper-evidence is
    handled separately in job (A), so a forged decision is already rejected
    there before this runs.
    """
    req = saved_receipt.request
    if type(req) is not dict or req.get("action_type") != ACTION_CREATE_DIRECTORY:
        return
    target = req.get("target_path", "")
    if target == "":
        return
    full_target = _sandbox_path_for(sandbox_root, original_root, target)
    parent = os.path.dirname(full_target)

    if saved_receipt.reason_code in _IMPLIES_PARENT_EXISTED:
        os.makedirs(parent, exist_ok=True)
    if saved_receipt.reason_code == BLOCK_TARGET_ALREADY_EXISTS:
        os.makedirs(parent, exist_ok=True)
        os.makedirs(full_target, exist_ok=True)


def _replay_data(raw_data: dict, source_label: str, allow_open: bool,
                 max_receipts: int) -> "ReplayResult":
    lines = []
    # -- Job (A): manifest + seal + chain integrity --
    try:
        manifest = validate_manifest(raw_data)
    except ReplayIncompatible as e:
        return _incompatible(f"REPLAY_INCOMPATIBLE: {e}")
    except ManifestError as e:
        return _fail(f"Manifest validation failed: {e}")

    try:
        validate_run_seal(raw_data, require_closed=not allow_open)
    except ManifestError as e:
        return _fail(f"Run seal validation failed: {e}")

    run_id = manifest["run_id"]
    original_root = manifest["allowed_root"]
    mode = "open/debug" if allow_open else "closed/audit"
    lines.append(f"Replaying run: {run_id}  (source: {source_label}, mode: {mode})")

    receipts_raw = raw_data.get("receipts", [])
    if len(receipts_raw) > max_receipts:
        return _fail(f"Replay receipt limit exceeded: {len(receipts_raw)} > {max_receipts}")

    try:
        saved_chain = ReceiptChain.from_receipts_list(run_id=run_id, data=receipts_raw)
    except Exception as e:
        return _fail(f"Failed to load saved receipt chain: {e}")

    saved_receipts = saved_chain.all()
    lines.append(f"Saved receipts: {len(saved_receipts)}")
    if not saved_receipts:
        return _fail("Saved chain is empty -- nothing to replay")

    ok, err = saved_chain.verify_chain(manifest=manifest)
    if not ok:
        return _fail(f"Saved chain structural verification failed: {err}")
    lines.append("Saved chain: verified OK (hashes, linkage, versions, INTENT/RESULT pairing)")

    # A run whose final receipt is an unresolved INTENT is incomplete
    # (RESULT_MISSING_AFTER_INTENT): the intent was recorded but the outcome was
    # not. Fail closed rather than treating it as a clean run.
    pending = saved_chain.unresolved_intent()
    if pending is not None:
        return _fail(f"RESULT_MISSING_AFTER_INTENT: run ends with an unresolved INTENT "
                     f"(#{pending.receipt_id}); the action's outcome was never recorded")

    # -- Job (B): active re-derivation through a fresh kernel --
    sandbox = tempfile.mkdtemp(prefix="sentinel_replay_")
    try:
        run_data = clone_manifest_run_data(manifest)
        run_data["manifest"]["allowed_root"] = sandbox
        run_data["manifest"]["manifest_hash"] = compute_manifest_hash(run_data["manifest"])

        fresh_chain = ReceiptChain(run_id=run_id)
        journal = Journal(VolatileTestBackend(), fresh_chain, run_data,
                          initial_session_state=manifest["initial_session_state"])
        kernel = Kernel(journal)

        from sentinel_core.reason_codes import STAGE_INTENT, STAGE_RESULT, STAGE_SESSION_CLOSE
        try:
            i = 0
            n = len(saved_receipts)
            while i < n:
                saved = saved_receipts[i]
                if saved.stage == STAGE_SESSION_CLOSE:
                    kernel.close_session()
                    i += 1
                    continue
                if saved.stage == STAGE_INTENT:
                    # An INTENT initiates a two-stage action; one process() call
                    # re-derives BOTH the INTENT and its RESULT. The saved RESULT
                    # that follows is consumed by this same call, so skip it.
                    _reconstruct_context(sandbox, original_root, saved)
                    kernel.process(saved.request)
                    i += 2  # consume INTENT + its RESULT
                    continue
                # A standalone RESULT (BLOCK / DRY_RUN): single process() call.
                _reconstruct_context(sandbox, original_root, saved)
                kernel.process(saved.request)
                i += 1
        except Exception as e:
            return _fail(f"Replay execution failed: {type(e).__name__}: {e}")

        fresh_receipts = fresh_chain.all()
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    if len(fresh_receipts) != len(saved_receipts):
        return _fail(f"Receipt count mismatch: saved={len(saved_receipts)} "
                     f"replayed={len(fresh_receipts)}")

    all_match = True
    env_exception_count = 0
    from sentinel_core.reason_codes import (
        ERROR as _ERROR, STAGE_RESULT as _SR,
        ERROR_EXECUTION_FAILED as _EEF, ERROR_POSTCONDITION_FAILED as _EPF,
    )
    for i, (saved, fresh) in enumerate(zip(saved_receipts, fresh_receipts)):
        # An execution/postcondition ERROR is environmental (e.g. a race, EACCES,
        # or a postcondition that did not hold). Replay in a clean sandbox cannot
        # reproduce that failure: the fresh kernel will usually succeed. So for a
        # saved ERROR-execution RESULT we verify structure only — it must be a
        # RESULT resolving the SAME INTENT — and accept that the freshly derived
        # outcome legitimately differs. This acceptance is NOT a strict
        # re-derivation: under unkeyed hashes a forged ERROR is indistinguishable
        # from a real one, so any run that relies on it is reported as
        # PASS_WITH_ENVIRONMENTAL_EXCEPTIONS, never PASS_STRICT. Tamper-evidence
        # for these receipts comes from the per-receipt self-hash and the
        # INTENT/RESULT pairing (already verified above), not re-derivation.
        # Documented in KNOWN_LIMITATIONS L10.
        non_reproducible_error = (
            saved.stage == _SR and saved.decision == _ERROR
            and saved.reason_code in (_EEF, _EPF)
            and saved.intent_receipt_id is not None
        )
        if non_reproducible_error:
            if fresh.stage == _SR and fresh.intent_receipt_id == saved.intent_receipt_id:
                env_exception_count += 1
                lines.append(f"  MATCH* #{i:04d}: {saved.stage} {saved.reason_code} "
                             f"(environmental ERROR: structurally verified, NOT re-derived)")
            else:
                all_match = False
                lines.append(f"  MISMATCH #{i:04d}: saved ERROR RESULT not re-derived as a "
                             f"RESULT resolving INTENT #{saved.intent_receipt_id}")
            continue

        same_intent_ref = (saved.intent_receipt_id == fresh.intent_receipt_id)
        if (saved.decision == fresh.decision
                and saved.reason_code == fresh.reason_code
                and saved.executed == fresh.executed
                and saved.stage == fresh.stage
                and same_intent_ref
                and saved.pre_session_state == fresh.pre_session_state
                and saved.post_session_state == fresh.post_session_state):
            lines.append(f"  MATCH  #{i:04d}: {saved.stage} {saved.decision} {saved.reason_code} "
                         f"[{saved.pre_session_state}->{saved.post_session_state}]")
        else:
            all_match = False
            lines.append(f"  MISMATCH #{i:04d}: "
                         f"saved={saved.stage}/{saved.decision}/{saved.reason_code}/"
                         f"exec={saved.executed}/ref={saved.intent_receipt_id}/"
                         f"{saved.pre_session_state}->{saved.post_session_state} "
                         f"fresh={fresh.stage}/{fresh.decision}/{fresh.reason_code}/"
                         f"exec={fresh.executed}/ref={fresh.intent_receipt_id}/"
                         f"{fresh.pre_session_state}->{fresh.post_session_state}")

    if not all_match:
        verdict = VERDICT_FAIL
        summary = (f"FAIL -- re-derivation divergence detected "
                   f"({len(saved_receipts)} receipts).")
    elif env_exception_count > 0:
        verdict = VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS
        summary = (f"PASS_WITH_ENVIRONMENTAL_EXCEPTIONS -- "
                   f"{len(saved_receipts)} receipts accepted, of which "
                   f"{env_exception_count} environmental ERROR receipt(s) were "
                   f"structurally verified but NOT strictly re-derived (see MATCH* "
                   f"above; KNOWN_LIMITATIONS L10/L4).")
    else:
        verdict = VERDICT_PASS_STRICT
        summary = (f"PASS_STRICT -- all {len(saved_receipts)} receipts strictly "
                   f"re-derived.")

    lines.append("REPLAY VERDICT: " + verdict)
    lines.append(summary)
    return ReplayResult(verdict in _OK_VERDICTS, verdict, "\n".join(lines))
