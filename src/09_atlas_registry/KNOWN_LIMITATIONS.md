# KNOWN_LIMITATIONS — Atlas Registry v0.1

## Read-only registry only

- Atlas Registry v0.1 is a **read-only registry only**.
- It **does not run workflows.**
- It **does not validate live component outputs** — it records vocabulary and
  metadata, not the results of any run.
- It **does not replace Coordinator.**
- It **does not replace Companion.**

## It does not prove truth

- It **does not prove truth.**
- It **does not verify external reality.**
- It refuses any status or predicate that claims truth (`truth_claim: true`, a
  truth-like name, or a truth-like predicate) with `FAILED_TRUTH_CLAIM`. Every
  recorded status and predicate carries `truth_claim: false`.

## Not connected yet

- **Not connected to Coordinator yet.**
- **Not connected to Companion yet.**
- Atlas does not feed its vocabulary into any other component in v0.1; later moves
  may wire it in.

## Explicitly out of scope

- **No natural language.**
- **No LLM.**
- **No signing.**
- **No external anchoring.**
- No queue, no concurrency, no automatic schema migration, no plugin system, no
  ontology expansion.

## Honesty boundary

Atlas records the vocabulary the stack already uses and verifies that the registry is
structurally valid and truth-free. Its export checksums give tamper-evidence within
an export folder, not tamper-proofness: a self-consistent rebuilt export would
re-verify. Defeating that requires signing or external anchoring, which are out of
scope here. This is not production evidence custody.
