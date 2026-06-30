# sentinel_core/run_loader.py
# Validated open-for-append loader (the v0.1.2 repair).
#
# v0.1.1's CLI loader treated an existing run as appendable if "run_seal" was
# missing, and hardcoded the journal session state to OPEN. Two attacks broke
# that: (1) close a run, delete its run_seal, append — the close receipt was
# ignored and a real directory was created; (2) delete a receipt from an open
# run, append — the structurally broken chain was extended with duplicate IDs.
# Replay caught both LATER, but the filesystem side effect had already
# happened. Load-time validation must therefore be as strict as replay-time
# validation, BEFORE any kernel is constructed.
#
# open_run_for_append performs, in order:
#   1. load the run file (hostile-JSON-safe loader);
#   2. validate the manifest (hash + version vector);
#   3. load receipts (per-receipt self-hash recomputation; raises on tamper);
#   4. chain.verify_chain(manifest) — IDs, linkage, versions, session
#      continuity, closure placement;
#   5. reject if verification fails;
#   6. reject if ANY receipt has a non-OPEN post_session_state (a close
#      receipt means the run is closed, whether or not a seal survives);
#   7. reject if run_seal is present (sealed = closed);
#   8. (6) already covers the deleted-seal case: seal missing + close receipt
#      in the chain is refused by the close-receipt check, not by seal absence;
#   9. derive the journal session state from the chain head (or the manifest's
#      initial state for an empty chain) — never hardcode OPEN;
#  10. only then construct the Kernel.
#
# Any rejection raises BEFORE a Kernel exists, so no action — and no
# filesystem side effect — is possible against an invalid or closed run.

from sentinel_core.errors import ChainVerificationError, SessionClosedError
from sentinel_core.journal import Journal
from sentinel_core.kernel import Kernel
from sentinel_core.manifest import load_run_file, validate_manifest
from sentinel_core.persistence import AtomicFileBackend, PersistenceBackend
from sentinel_core.receipts import ReceiptChain
from sentinel_core.run_seal import RUN_SEAL_FIELD
from sentinel_core.session import SESSION_OPEN


def open_run_for_append(run_path: str, backend: PersistenceBackend = None) -> Kernel:
    """Open an EXISTING run for append, validating it fully first.

    Raises ManifestError, ChainVerificationError, or SessionClosedError on any
    integrity or closure problem. Returns a ready Kernel only for a structurally
    valid, genuinely open run. Never mutates the run file or the filesystem.
    """
    # 1–2. Load and validate the manifest (fails closed on hostile JSON,
    #      hash mismatch, or version-vector mismatch).
    raw = load_run_file(run_path)
    manifest = validate_manifest(raw)

    # 3. Load receipts. from_receipts_list recomputes every receipt's
    #    canonical_hash and raises ChainVerificationError on any mismatch.
    receipts_raw = raw.get("receipts", [])
    chain = ReceiptChain.from_receipts_list(manifest["run_id"], receipts_raw)

    # 4–5. Full structural verification against the manifest: contiguous IDs
    #      from 0 (catches deleted-first/middle receipts and duplicates),
    #      prior_hash linkage, version fields, session continuity, closure
    #      placement.
    ok, err = chain.verify_chain(manifest=manifest)
    if not ok:
        raise ChainVerificationError(
            f"Existing run failed chain verification; refusing append: {err}")

    # 5a (v0.2). Refuse a run left in a RESULT_MISSING_AFTER_INTENT state: an
    #            INTENT was durably recorded but its RESULT was never persisted.
    #            Appending or closing on top of an unresolved intent would hide
    #            an action whose outcome is unknown.
    pending = chain.unresolved_intent()
    if pending is not None:
        raise ChainVerificationError(
            f"Run is incomplete (RESULT_MISSING_AFTER_INTENT): INTENT "
            f"#{pending.receipt_id} has no matching RESULT; refusing append.")

    # 6 + 8. A session-closing receipt anywhere in the chain means the run is
    #        closed — REGARDLESS of whether a run_seal survives. This is the
    #        deleted-seal attack: the seal is corroborating evidence of
    #        closure, never the sole witness of it.
    for r in chain.all():
        if r.post_session_state != SESSION_OPEN:
            raise SessionClosedError(
                f"Run contains a session-closing receipt "
                f"(#{r.receipt_id}, post_session_state={r.post_session_state!r}); "
                f"refusing append regardless of run_seal presence.")

    # 7. A present seal also means closed (and would normally accompany a
    #    close receipt; checked independently so a seal alone still refuses).
    if raw.get(RUN_SEAL_FIELD) is not None:
        raise SessionClosedError("Run is sealed (run_seal present); refusing append.")

    # 9. Derive the session state from the chain head, never hardcode it. After
    #    the closure checks above this is OPEN, but deriving keeps the loader
    #    correct if session states ever expand.
    head = chain.head()
    session_state = head.post_session_state if head is not None else manifest["initial_session_state"]

    # 10. Only now construct the journal and kernel.
    run_data = {"manifest": manifest, "receipts": receipts_raw,
                RUN_SEAL_FIELD: raw.get(RUN_SEAL_FIELD)}
    if backend is None:
        backend = AtomicFileBackend(run_path)
    return Kernel(Journal(backend, chain, run_data, session_state))
