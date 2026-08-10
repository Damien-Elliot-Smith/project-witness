# sentinel_core/receipts.py
# Immutable, validated decision receipts with a hash chain.
#
# A receipt records one decision over one action request. Receipts are frozen
# after construction; the canonical_hash is computed once over a fixed payload.
# The chain links each receipt to the previous one via prior_hash, so deleting
# or reordering receipts is detectable on verification.

import hashlib
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from sentinel_core.canonical import canonical_json
from sentinel_core.errors import ReceiptError, ChainVerificationError, require
from sentinel_core.reason_codes import VALID_DECISIONS, valid_pairing, all_codes
from sentinel_core.session import SESSION_OPEN, SESSION_CLOSED, VALID_SESSION_STATES
from sentinel_core.versions import (
    CURRENT_VERSION_VECTOR, IMPL_VERSION, RECEIPT_SCHEMA_VERSION,
    ACTION_SCHEMA_VERSION, POLICY_VERSION, REASON_REGISTRY_VERSION, SESSION_VERSION,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _valid_hex64(s) -> bool:
    if type(s) is not str or len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class Receipt:
    receipt_id: int
    prior_hash: str
    run_id: str
    manifest_hash: str

    receipt_schema_version: str
    impl_version: str
    action_schema_version: str
    policy_version: str
    reason_registry_version: str
    session_version: str

    pre_session_state: str
    post_session_state: str

    stage: str
    intent_receipt_id: Any   # int for a RESULT that resolves an INTENT, else None
    intent_hash: Any         # 64-hex canonical_hash of the referenced INTENT, else None

    request: Any
    decision: str
    reason_code: str
    detail: Any
    executed: bool

    canonical_hash: str = field(init=False)

    def __post_init__(self):
        self._validate()
        object.__setattr__(self, "canonical_hash", self._compute_hash())

    def _validate(self):
        require(type(self.receipt_id) is int and self.receipt_id >= 0,
                f"receipt_id must be non-negative int, got {self.receipt_id!r}", ReceiptError)
        require(self.prior_hash == "GENESIS" or _valid_hex64(self.prior_hash),
                f"prior_hash must be 'GENESIS' or 64-char hex, got {self.prior_hash!r}", ReceiptError)
        require(_valid_hex64(self.manifest_hash), "manifest_hash must be 64-char hex", ReceiptError)
        require(type(self.run_id) is str and self.run_id != "", "run_id must be non-empty str", ReceiptError)
        require(self.decision in VALID_DECISIONS, f"Unknown decision: {self.decision!r}", ReceiptError)
        require(self.reason_code in all_codes(), f"Unknown reason_code: {self.reason_code!r}", ReceiptError)
        require(valid_pairing(self.decision, self.reason_code),
                f"Invalid decision/reason pairing: {self.decision}/{self.reason_code}", ReceiptError)
        require(type(self.executed) is bool, "executed must be a boolean", ReceiptError)

        for name in ("receipt_schema_version", "impl_version", "action_schema_version",
                     "policy_version", "reason_registry_version", "session_version"):
            value = getattr(self, name)
            require(type(value) is str and value != "", f"{name} must be non-empty str", ReceiptError)

        require(self.pre_session_state in VALID_SESSION_STATES,
                f"Invalid pre_session_state: {self.pre_session_state!r}", ReceiptError)
        require(self.post_session_state in VALID_SESSION_STATES,
                f"Invalid post_session_state: {self.post_session_state!r}", ReceiptError)

        # ── Session-transition grammar (v0.1.3) ──────────────────────────────
        # Every receipt begins OPEN. Only a real ALLOW_SESSION_CLOSE receipt
        # may end CLOSED_BY_OPERATOR; every other receipt must end OPEN. This is
        # enforced here (at construction AND on load, since loading reconstructs
        # the receipt) so a forged closure — e.g. a CREATE receipt whose
        # post_session_state was edited to CLOSED and rehashed — fails closed.
        from sentinel_core.reason_codes import (
            ALLOW, ALLOW_SESSION_CLOSE, CLOSE_SESSION_REQUEST, is_session_close_shape,
        )

        require(self.pre_session_state == SESSION_OPEN,
                f"Receipt pre_session_state must be OPEN, got {self.pre_session_state!r}",
                ReceiptError)

        close_shape = is_session_close_shape(
            self.decision, self.reason_code, self.request, self.executed)

        if self.post_session_state == SESSION_CLOSED:
            # Closure is permitted ONLY for the exact close shape.
            require(close_shape,
                    "Only an ALLOW_SESSION_CLOSE receipt (decision=ALLOW, "
                    "reason_code=ALLOW_SESSION_CLOSE, "
                    "request={'action_type': 'CLOSE_SESSION'}, executed=False) "
                    "may transition OPEN -> CLOSED_BY_OPERATOR", ReceiptError)
        else:
            # A non-closed post-state. A close-reason receipt may not hide here,
            # and no receipt may end in the ERROR session state in this version.
            require(self.post_session_state == SESSION_OPEN,
                    f"Non-close receipt post_session_state must be OPEN, "
                    f"got {self.post_session_state!r}", ReceiptError)
            require(self.reason_code != ALLOW_SESSION_CLOSE,
                    "ALLOW_SESSION_CLOSE receipt must end CLOSED_BY_OPERATOR",
                    ReceiptError)

        # If the close reason is present at all, the full close shape AND the
        # canonical request object must hold (independent of post-state, so a
        # half-forged close receipt cannot pass either branch above).
        if self.reason_code == ALLOW_SESSION_CLOSE:
            require(self.decision == ALLOW and self.executed is False,
                    "ALLOW_SESSION_CLOSE must be decision=ALLOW, executed=False",
                    ReceiptError)
            require(self.request == CLOSE_SESSION_REQUEST,
                    "ALLOW_SESSION_CLOSE request must be {'action_type': 'CLOSE_SESSION'}",
                    ReceiptError)

        # Only ALLOW with execution may set executed=True.
        if self.executed:
            require(self.decision == ALLOW, "Only ALLOW receipts may have executed=True", ReceiptError)

        # ── Stage grammar (v0.2) ─────────────────────────────────────────────
        from sentinel_core.reason_codes import (
            STAGE_INTENT, STAGE_RESULT, STAGE_SESSION_CLOSE, VALID_STAGES,
            INTENT_REASON_CODES, stage_for_reason, ERROR, BLOCK, DRY_RUN,
        )
        require(self.stage in VALID_STAGES, f"Invalid stage: {self.stage!r}", ReceiptError)
        # The stage must match the reason's mandated stage exactly, so a receipt
        # cannot mislabel its stage (e.g. tag an executed RESULT as INTENT).
        require(self.stage == stage_for_reason(self.reason_code),
                f"stage {self.stage!r} does not match reason {self.reason_code!r} "
                f"(expected {stage_for_reason(self.reason_code)!r})", ReceiptError)

        if self.stage == STAGE_INTENT:
            # An INTENT is approved-but-not-executed and references no INTENT.
            require(self.decision == ALLOW and self.reason_code in INTENT_REASON_CODES,
                    "INTENT stage requires decision=ALLOW and an INTENT reason code",
                    ReceiptError)
            require(self.executed is False, "INTENT receipt must have executed=False", ReceiptError)
            require(self.post_session_state == SESSION_OPEN,
                    "INTENT receipt must end OPEN", ReceiptError)
            require(self.intent_receipt_id is None and self.intent_hash is None,
                    "INTENT receipt must not reference another INTENT", ReceiptError)
        elif self.stage == STAGE_SESSION_CLOSE:
            require(self.intent_receipt_id is None and self.intent_hash is None,
                    "SESSION_CLOSE receipt carries no intent reference", ReceiptError)
        else:  # STAGE_RESULT
            # A RESULT either resolves an INTENT (ALLOW/ERROR execution path) or
            # is self-contained (BLOCK / DRY_RUN, which never approved an action).
            resolves = self.intent_receipt_id is not None
            if resolves:
                require(type(self.intent_receipt_id) is int and self.intent_receipt_id >= 0,
                        "intent_receipt_id must be a non-negative int", ReceiptError)
                require(_valid_hex64(self.intent_hash),
                        "intent_hash must be a 64-char hex digest", ReceiptError)
                require(self.intent_receipt_id == self.receipt_id - 1,
                        "A resolving RESULT must immediately follow its INTENT "
                        "(intent_receipt_id == receipt_id - 1)", ReceiptError)
                require(self.decision in (ALLOW, ERROR),
                        "A resolving RESULT must be decision ALLOW or ERROR", ReceiptError)
            else:
                # Self-contained RESULT: BLOCK or DRY_RUN only, no intent hash.
                require(self.intent_hash is None,
                        "Self-contained RESULT must not carry an intent_hash", ReceiptError)
                require(self.decision in (BLOCK, DRY_RUN),
                        "A RESULT with no INTENT must be a BLOCK or DRY_RUN decision",
                        ReceiptError)
            require(self.post_session_state == SESSION_OPEN,
                    "RESULT receipt must end OPEN", ReceiptError)

    def _hashable_payload(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "prior_hash": self.prior_hash,
            "run_id": self.run_id,
            "manifest_hash": self.manifest_hash,
            "receipt_schema_version": self.receipt_schema_version,
            "impl_version": self.impl_version,
            "action_schema_version": self.action_schema_version,
            "policy_version": self.policy_version,
            "reason_registry_version": self.reason_registry_version,
            "session_version": self.session_version,
            "pre_session_state": self.pre_session_state,
            "post_session_state": self.post_session_state,
            "stage": self.stage,
            "intent_receipt_id": self.intent_receipt_id,
            "intent_hash": self.intent_hash,
            "request": self.request,
            "decision": self.decision,
            "reason_code": self.reason_code,
            "detail": self.detail,
            "executed": self.executed,
        }

    def _compute_hash(self) -> str:
        return _sha256(canonical_json(self._hashable_payload()))

    def verify_self_hash(self) -> bool:
        return self._compute_hash() == self.canonical_hash

    def to_dict(self) -> dict:
        d = self._hashable_payload()
        d["canonical_hash"] = self.canonical_hash
        return d

    def summary_line(self) -> str:
        rid = self.request.get("request_id", "?") if type(self.request) is dict else "?"
        ref = f" <-#{self.intent_receipt_id:04d}" if self.intent_receipt_id is not None else ""
        return (f"#{self.receipt_id:04d} {self.stage:13s} {self.decision:7s} {self.reason_code} "
                f"req={rid} exec={self.executed}{ref} hash={self.canonical_hash[:12]}...")


def build_receipt(
    receipt_id: int,
    prior_hash: str,
    run_id: str,
    manifest_hash: str,
    pre_session_state: str,
    post_session_state: str,
    stage: str,
    request,
    decision: str,
    reason_code: str,
    detail,
    executed: bool,
    intent_receipt_id=None,
    intent_hash=None,
) -> Receipt:
    return Receipt(
        receipt_id=receipt_id,
        prior_hash=prior_hash,
        run_id=run_id,
        manifest_hash=manifest_hash,
        receipt_schema_version=RECEIPT_SCHEMA_VERSION,
        impl_version=IMPL_VERSION,
        action_schema_version=ACTION_SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        reason_registry_version=REASON_REGISTRY_VERSION,
        session_version=SESSION_VERSION,
        pre_session_state=pre_session_state,
        post_session_state=post_session_state,
        stage=stage,
        intent_receipt_id=intent_receipt_id,
        intent_hash=intent_hash,
        request=request,
        decision=decision,
        reason_code=reason_code,
        detail=detail,
        executed=executed,
    )


_RECEIPT_FIELDS = frozenset({
    "receipt_id", "prior_hash", "run_id", "manifest_hash",
    "receipt_schema_version", "impl_version", "action_schema_version",
    "policy_version", "reason_registry_version", "session_version",
    "pre_session_state", "post_session_state", "stage",
    "intent_receipt_id", "intent_hash", "request", "decision",
    "reason_code", "detail", "executed", "canonical_hash",
})


def _receipt_from_dict(item) -> Receipt:
    require(type(item) is dict, "Receipt must be an object", ReceiptError)
    keys = set(item.keys())
    require(keys == _RECEIPT_FIELDS,
            f"Receipt field mismatch: missing={sorted(_RECEIPT_FIELDS - keys)}, "
            f"extra={sorted(keys - _RECEIPT_FIELDS)}", ReceiptError)
    r = Receipt(
        receipt_id=item["receipt_id"],
        prior_hash=item["prior_hash"],
        run_id=item["run_id"],
        manifest_hash=item["manifest_hash"],
        receipt_schema_version=item["receipt_schema_version"],
        impl_version=item["impl_version"],
        action_schema_version=item["action_schema_version"],
        policy_version=item["policy_version"],
        reason_registry_version=item["reason_registry_version"],
        session_version=item["session_version"],
        pre_session_state=item["pre_session_state"],
        post_session_state=item["post_session_state"],
        stage=item["stage"],
        intent_receipt_id=item["intent_receipt_id"],
        intent_hash=item["intent_hash"],
        request=item["request"],
        decision=item["decision"],
        reason_code=item["reason_code"],
        detail=item["detail"],
        executed=item["executed"],
    )
    # The stored hash must match the recomputed hash exactly.
    if item["canonical_hash"] != r.canonical_hash:
        raise ChainVerificationError(
            f"Receipt #{r.receipt_id} canonical_hash mismatch on load (tampered)"
        )
    return r


class ReceiptChain:
    def __init__(self, run_id: str):
        self._run_id = run_id
        self._receipts: List[Receipt] = []

    @property
    def run_id(self) -> str:
        return self._run_id

    def next_id(self) -> int:
        return len(self._receipts)

    def next_prior_hash(self) -> str:
        return "GENESIS" if not self._receipts else self._receipts[-1].canonical_hash

    def append_trusted(self, receipt: Receipt) -> None:
        self._receipts.append(receipt)

    def all(self) -> Tuple[Receipt, ...]:
        return tuple(self._receipts)

    def head(self) -> Optional[Receipt]:
        return self._receipts[-1] if self._receipts else None

    def format_history(self) -> str:
        if not self._receipts:
            return "[No receipts in chain]"
        lines = [f"Run: {self._run_id}  ({len(self._receipts)} receipt(s))", "-" * 72]
        lines.extend(r.summary_line() for r in self._receipts)
        return "\n".join(lines)

    def verify_chain(self, manifest: Optional[dict] = None) -> Tuple[bool, Optional[str]]:
        receipts = self._receipts
        if not receipts:
            return True, None

        manifest_hash = manifest.get("manifest_hash") if manifest else None

        for i, r in enumerate(receipts):
            if r.receipt_id != i:
                return False, f"Receipt ID gap: expected {i}, got {r.receipt_id}"
            if r.run_id != self._run_id:
                return False, f"Receipt #{i} run_id mismatch"
            if manifest_hash and r.manifest_hash != manifest_hash:
                return False, f"Receipt #{i} manifest_hash mismatch"
            if not r.verify_self_hash():
                return False, f"Receipt #{i} canonical_hash recomputation mismatch (tampered)"
            if i == 0 and r.prior_hash != "GENESIS":
                return False, "Receipt #0 prior_hash is not 'GENESIS'"
            if i > 0 and r.prior_hash != receipts[i - 1].canonical_hash:
                return False, f"Receipt #{i} prior_hash linkage broken"

            if manifest is not None:
                for fieldname in ("receipt_schema_version", "impl_version", "action_schema_version",
                                  "policy_version", "reason_registry_version", "session_version"):
                    if getattr(r, fieldname) != CURRENT_VERSION_VECTOR[fieldname]:
                        return False, f"Receipt #{i} {fieldname} mismatch with current vector"
                    if getattr(r, fieldname) != manifest.get(fieldname):
                        return False, f"Receipt #{i} {fieldname} differs from manifest"

        # Session continuity: each receipt's post state is the next pre state.
        for i in range(len(receipts) - 1):
            if receipts[i].post_session_state != receipts[i + 1].pre_session_state:
                return False, f"Session continuity broken between #{i} and #{i+1}"

        # Closure rule: a closed session must be the final receipt, and the
        # ONLY receipt permitted to declare closure is a real
        # ALLOW_SESSION_CLOSE (v0.1.3). This duplicates the per-receipt
        # construction check on purpose: defence in depth for any path that
        # verifies an already-constructed chain.
        from sentinel_core.reason_codes import is_session_close_shape, ALLOW_SESSION_CLOSE
        for i, r in enumerate(receipts):
            if r.post_session_state == SESSION_CLOSED:
                if i != len(receipts) - 1:
                    return False, f"Receipt exists after session closure at #{i}"
                if not is_session_close_shape(r.decision, r.reason_code, r.request, r.executed):
                    return False, (f"Receipt #{i} declares closure but is not a valid "
                                   f"ALLOW_SESSION_CLOSE receipt")
            else:
                if r.reason_code == ALLOW_SESSION_CLOSE:
                    return False, f"Receipt #{i} is ALLOW_SESSION_CLOSE but does not close the session"
            if r.pre_session_state != SESSION_OPEN:
                return False, f"Receipt #{i} begins after session closure"

        # ── INTENT/RESULT pairing invariants (v0.2) ──────────────────────────
        from sentinel_core.reason_codes import (
            STAGE_INTENT, STAGE_RESULT, STAGE_SESSION_CLOSE,
        )
        # Map every resolving RESULT to the INTENT it claims.
        intent_ids = [r.receipt_id for r in receipts if r.stage == STAGE_INTENT]
        resolved = {}
        for i, r in enumerate(receipts):
            if r.stage == STAGE_RESULT and r.intent_receipt_id is not None:
                tid = r.intent_receipt_id
                # The referenced INTENT must exist, be an INTENT, immediately
                # precede this RESULT, and hash-match the recorded intent_hash.
                if tid != r.receipt_id - 1:
                    return False, f"RESULT #{i} does not immediately follow its INTENT"
                target = receipts[tid] if 0 <= tid < len(receipts) else None
                if target is None or target.stage != STAGE_INTENT:
                    return False, f"RESULT #{i} references non-INTENT receipt #{tid}"
                if r.intent_hash != target.canonical_hash:
                    return False, f"RESULT #{i} intent_hash does not match INTENT #{tid}"
                if tid in resolved:
                    return False, f"INTENT #{tid} resolved by more than one RESULT"
                resolved[tid] = r.receipt_id
        # Every INTENT must be resolved by exactly one RESULT, EXCEPT possibly a
        # trailing unresolved INTENT (a RESULT_MISSING_AFTER_INTENT state). That
        # trailing case is reported explicitly via unresolved_intent(); here we
        # reject any NON-trailing unresolved INTENT as structurally broken.
        for iid in intent_ids:
            if iid not in resolved and iid != receipts[-1].receipt_id:
                return False, (f"INTENT #{iid} has no matching RESULT and is not the "
                               f"final receipt (broken pairing)")
        # A SESSION_CLOSE must not sit on top of an unresolved INTENT.
        if receipts[-1].stage == STAGE_SESSION_CLOSE:
            for iid in intent_ids:
                if iid not in resolved:
                    return False, f"Session closed while INTENT #{iid} is unresolved"

        return True, None

    def unresolved_intent(self):
        """Return the trailing unresolved INTENT receipt, or None.

        A run whose final receipt is an INTENT with no following RESULT is in a
        RESULT_MISSING_AFTER_INTENT state: the intent was durably recorded but
        the outcome was not. Such a run is NOT complete and must not be appended
        to, closed, or accepted as a clean replay.
        """
        from sentinel_core.reason_codes import STAGE_INTENT
        if self._receipts and self._receipts[-1].stage == STAGE_INTENT:
            return self._receipts[-1]
        return None

    @classmethod
    def from_receipts_list(cls, run_id: str, data) -> "ReceiptChain":
        if type(data) is not list:
            raise ChainVerificationError("receipts must be a list")
        chain = cls(run_id=run_id)
        for item in data:
            chain._receipts.append(_receipt_from_dict(item))
        return chain
