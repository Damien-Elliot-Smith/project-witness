# sentinel_core/kernel.py
# Central action gate. Single entry point for all action requests.
#
# Flow for one request (process), v0.2 two-stage INTENT/RESULT model:
#   1. If the session is closed -> raise SessionClosedError (no receipt).
#   2. Refuse if a prior INTENT is unresolved (RESULT_MISSING_AFTER_INTENT).
#   3. Pure decision (schema + action-type + path policy, read-only).
#   4. For BLOCK / DRY_RUN: a single self-contained RESULT receipt; no
#      filesystem mutation, no INTENT (nothing was approved for execution).
#   5. For ALLOW (two stages):
#        a. Build + persist + commit an INTENT receipt BEFORE any mkdir. If
#           INTENT persistence fails, the journal raises: no mkdir, no side
#           effect, nothing further committed.
#        b. Execute mkdir.
#        c. Verify the postcondition.
#        d. Build + persist a RESULT receipt that references the INTENT
#           (intent_receipt_id + intent_hash):
#             - mkdir failed        -> ERROR_EXECUTION_FAILED   (executed=False)
#             - postcondition failed -> ERROR_POSTCONDITION_FAILED (executed=False)
#             - success             -> ALLOW_CREATE_DIRECTORY   (executed=True)
#
# Persistence-before-commit holds for EACH stage: in-memory chain/session state
# advances only after the run file containing that stage's receipt is durably
# written (see journal.py). The remaining honest window — mkdir succeeds but the
# RESULT write then fails — leaves a detectable RESULT_MISSING_AFTER_INTENT run
# (the INTENT is committed, no RESULT is); the failure is raised, never
# swallowed, and the append loader / close / replay all fail closed on it.
# Proven in tests/test_two_stage.py.

from sentinel_core.decision import evaluate as evaluate_decision
from sentinel_core.errors import PersistenceFailure, SessionClosedError, require
from sentinel_core.journal import Journal
from sentinel_core.persistence import execute_create_directory
from sentinel_core.receipts import build_receipt, Receipt
from sentinel_core.reason_codes import (
    ALLOW, BLOCK, DRY_RUN, ERROR,
    BLOCK_SESSION_CLOSED, ERROR_POSTCONDITION_FAILED, ERROR_EXECUTION_FAILED,
)
from sentinel_core.session import SESSION_OPEN, SESSION_CLOSED
import os

_SANITIZE_MAX_DEPTH = 32
_SANITIZE_MAX_STR = 1024


def _sanitize_for_record(obj, depth=0):
    """Convert an arbitrary Python object into JSON-native data for a receipt.

    Used ONLY for requests that already failed schema validation: the receipt
    must still record what was submitted, but the input may contain values the
    canonical encoder rightly rejects (sets, custom objects, NaN, non-str keys,
    absurd nesting). Unrepresentable values are replaced with a tagged string
    so the record is faithful about what arrived without crashing.
    """
    if depth > _SANITIZE_MAX_DEPTH:
        return "<unrepresentable: nesting depth exceeded>"
    if obj is None or isinstance(obj, bool) or isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        import math
        if math.isnan(obj) or math.isinf(obj):
            return f"<unrepresentable float: {obj!r}>"
        return obj
    if isinstance(obj, str):
        if len(obj) > _SANITIZE_MAX_STR:
            return obj[:_SANITIZE_MAX_STR] + "<truncated>"
        return obj
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_record(v, depth + 1) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return f"<unrepresentable: {type(obj).__name__} of {len(obj)} item(s)>"
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = k if isinstance(k, str) else f"<non-str key: {repr(k)[:64]}>"
            out[key] = _sanitize_for_record(v, depth + 1)
        return out
    return f"<unrepresentable: {type(obj).__name__} {repr(obj)[:128]}>"


class Kernel:
    def __init__(self, journal: Journal):
        self._journal = journal

    @property
    def session_state(self) -> str:
        return self._journal.session_state

    @property
    def manifest(self) -> dict:
        return self._journal.manifest

    def session_open(self) -> bool:
        return self._journal.session_state == SESSION_OPEN

    def _emit(self, pre_session_state, post_session_state, stage, request,
              decision, reason_code, detail, executed,
              intent_receipt_id=None, intent_hash=None) -> Receipt:
        receipt = build_receipt(
            receipt_id=self._journal.chain.next_id(),
            prior_hash=self._journal.chain.next_prior_hash(),
            run_id=self._journal.chain.run_id,
            manifest_hash=self._journal.manifest_hash,
            pre_session_state=pre_session_state,
            post_session_state=post_session_state,
            stage=stage,
            request=request,
            decision=decision,
            reason_code=reason_code,
            detail=detail,
            executed=executed,
            intent_receipt_id=intent_receipt_id,
            intent_hash=intent_hash,
        )
        self._journal.commit(receipt, post_session_state)
        return receipt

    def process(self, raw_request) -> Receipt:
        """Process one structured action request.

        Returns the RESULT receipt (the final receipt of the request). For an
        ALLOW path this is the second of a two-receipt INTENT->RESULT pair; the
        INTENT is already durably persisted and committed before any mkdir runs.
        For BLOCK/DRY_RUN it is a single self-contained RESULT (nothing was ever
        approved for execution, so no intent durability is needed).
        """
        if not self.session_open():
            raise SessionClosedError(f"Session is closed: {self.session_state}")
        # Refuse to process on top of an unresolved INTENT (a prior
        # RESULT_MISSING_AFTER_INTENT must be resolved first; the loader already
        # refuses to open such a run, but guard here too).
        require(self._journal.chain.unresolved_intent() is None,
                "Cannot process: a prior INTENT is unresolved (RESULT_MISSING_AFTER_INTENT)",
                SessionClosedError)

        from sentinel_core.reason_codes import (
            STAGE_RESULT, STAGE_INTENT, INTENT_CREATE_DIRECTORY,
        )

        pre_session = SESSION_OPEN
        # The boundary is AUTHORITATIVE: from the run manifest, never the request.
        decision = evaluate_decision(raw_request, self._journal.manifest["allowed_root"])

        if decision.normalised_request is not None:
            recorded_request = decision.normalised_request
        else:
            recorded_request = _sanitize_for_record(raw_request)

        if decision.decision in (BLOCK, DRY_RUN):
            # Self-contained RESULT. No INTENT, no filesystem mutation.
            return self._emit(pre_session, SESSION_OPEN, STAGE_RESULT, recorded_request,
                              decision.decision, decision.reason_code, decision.detail, False)

        # ── ALLOW: two-stage INTENT -> (mkdir) -> RESULT ─────────────────────
        # Step 1-2 (schema + policy) already done in evaluate_decision.
        # Step 3-4: build + persist the INTENT receipt BEFORE any mkdir. If
        # INTENT persistence fails, the journal raises and NOTHING is committed
        # and NO mkdir runs.
        intent = self._emit(pre_session, SESSION_OPEN, STAGE_INTENT, recorded_request,
                            ALLOW, INTENT_CREATE_DIRECTORY, dict(decision.detail), False)

        # Step 5: only after durable INTENT, execute mkdir.
        resolved_target = decision.resolved_target
        try:
            execute_create_directory(resolved_target)
        except PersistenceFailure as e:
            # mkdir failed after INTENT persisted -> RESULT/ERROR. Session stays
            # open, run stays replayable (the INTENT has a matching RESULT).
            detail = dict(decision.detail)
            detail["execution_error"] = str(e)
            return self._emit(pre_session, SESSION_OPEN, STAGE_RESULT, recorded_request,
                              ERROR, ERROR_EXECUTION_FAILED, detail, False,
                              intent_receipt_id=intent.receipt_id, intent_hash=intent.canonical_hash)

        # Step 6: verify postcondition.
        if not (os.path.isdir(resolved_target) and os.path.exists(resolved_target)):
            detail = dict(decision.detail)
            detail["postcondition_error"] = "target is not a directory after mkdir"
            return self._emit(pre_session, SESSION_OPEN, STAGE_RESULT, recorded_request,
                              ERROR, ERROR_POSTCONDITION_FAILED, detail, False,
                              intent_receipt_id=intent.receipt_id, intent_hash=intent.canonical_hash)

        # Step 7-9: build + persist the success RESULT, then commit. If RESULT
        # persistence fails here, the directory exists and the INTENT is
        # committed but no RESULT is -> the run is left in a
        # RESULT_MISSING_AFTER_INTENT state that the loader/replay detect and
        # fail closed on (see KNOWN_LIMITATIONS / docs). The failure is raised,
        # never swallowed.
        return self._emit(pre_session, SESSION_OPEN, STAGE_RESULT, recorded_request,
                          ALLOW, decision.reason_code, decision.detail, True,
                          intent_receipt_id=intent.receipt_id, intent_hash=intent.canonical_hash)

    def close_session(self) -> Receipt:
        """Close the session with a final SESSION_CLOSE receipt.

        Refuses to close while an INTENT is unresolved (the outcome of an
        approved action must be recorded before the run can be sealed).
        """
        if not self.session_open():
            raise SessionClosedError(f"Session is closed: {self.session_state}")
        require(self._journal.chain.unresolved_intent() is None,
                "Cannot close: a prior INTENT is unresolved (RESULT_MISSING_AFTER_INTENT)",
                SessionClosedError)
        from sentinel_core.reason_codes import (
            ALLOW_SESSION_CLOSE, CLOSE_SESSION_REQUEST, STAGE_SESSION_CLOSE,
        )
        return self._emit(SESSION_OPEN, SESSION_CLOSED, STAGE_SESSION_CLOSE,
                          dict(CLOSE_SESSION_REQUEST), ALLOW, ALLOW_SESSION_CLOSE, {}, False)
