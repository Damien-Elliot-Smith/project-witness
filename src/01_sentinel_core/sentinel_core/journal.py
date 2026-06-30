# sentinel_core/journal.py
# Owns authoritative session state, the receipt chain, and run-file data.
#
# The single invariant this module exists to enforce: a receipt is durably
# persisted BEFORE it is committed to the in-memory chain or before session
# state advances. commit() writes via the backend first; only if that write
# returns without raising does it append to the chain and update session state.
# If the write raises PersistenceFailure, nothing is committed and the caller
# sees the failure.

from sentinel_core.errors import PersistenceFailure, require
from sentinel_core.persistence import PersistenceBackend
from sentinel_core.receipts import Receipt, ReceiptChain
from sentinel_core.run_seal import RUN_SEAL_FIELD, OPEN_RUN_SEAL, build_run_seal
from sentinel_core.session import SESSION_OPEN, SESSION_CLOSED


class Journal:
    def __init__(self, backend: PersistenceBackend, chain: ReceiptChain,
                 run_data: dict, initial_session_state: str = SESSION_OPEN):
        self._backend = backend
        self._chain = chain
        self._run_data = run_data
        self._session_state = initial_session_state

    @property
    def chain(self) -> ReceiptChain:
        return self._chain

    @property
    def session_state(self) -> str:
        return self._session_state

    @property
    def manifest(self) -> dict:
        return self._run_data["manifest"]

    @property
    def manifest_hash(self) -> str:
        return self.manifest["manifest_hash"]

    def is_volatile(self) -> bool:
        return self._backend.is_volatile()

    def commit(self, receipt: Receipt, candidate_session_state: str) -> None:
        """Persist the receipt, then commit in-memory state.

        Order is load-bearing: build the next run-file snapshot, write it
        durably, and only on success append to the chain and advance session
        state. A persistence failure leaves the chain and session untouched.
        """
        # Build the candidate snapshot that INCLUDES this receipt.
        candidate_receipts = [r.to_dict() for r in self._chain.all()] + [receipt.to_dict()]
        candidate_data = dict(self._run_data)
        candidate_data["receipts"] = candidate_receipts
        candidate_data[RUN_SEAL_FIELD] = OPEN_RUN_SEAL
        if candidate_session_state == SESSION_CLOSED:
            candidate_data[RUN_SEAL_FIELD] = build_run_seal(candidate_data["manifest"], candidate_receipts)

        # PERSIST FIRST. If this raises, we have NOT mutated any in-memory state.
        self._backend.write(candidate_data)

        # COMMIT ONLY AFTER a successful write.
        self._chain.append_trusted(receipt)
        self._session_state = candidate_session_state
        self._run_data["receipts"] = candidate_receipts
        self._run_data[RUN_SEAL_FIELD] = candidate_data[RUN_SEAL_FIELD]
