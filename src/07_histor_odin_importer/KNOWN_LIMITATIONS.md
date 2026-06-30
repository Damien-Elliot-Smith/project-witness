# Known limitations — Histor-lite ODIN Importer v0.1

The importer is a deliberately narrow connector. These limitations are explicit and
accepted for this milestone.

## L1 — One ODIN reasoning output only
One ODIN Claim Reasoner v0.1 output -> one reasoning case record. No batching.

## L2 — ODIN v0.1 only
It reads the ODIN Claim Reasoner v0.1 output shape (reasoning_report.json,
proof_trace.json, claims_canonical.json). No other reasoner.

## L3 — Metadata import only
It records structural reasoning metadata and copies the ODIN files verbatim. It does
not re-derive, re-reason, or interpret anything.

## L4 — Does not import Aletheia evidence metadata
This importer is ODIN-only. It does not read or import Aletheia bundles or evidence
manifests.

## L5 — Does not import Sentinel action data
No Sentinel actions, no action gating, no workflow data.

## L6 — Does not prove truth
A recorded `CONSISTENT` or `CONTRADICTION_DETECTED` status is a structural reasoning
outcome. It does not prove, and does not claim, that any claim is true or false.

## L7 — No natural language
No natural-language parsing, generation, or interpretation.

## L8 — No LLM
No language model is involved anywhere.

## L9 — No signing
Nothing in the case record is cryptographically signed.

## L10 — No external anchoring
No hash is anchored to an external log, timestamp authority, or notary. A
self-consistent whole-folder fabrication remains possible.

## L11 — Not connected to Coordinator
The importer stands alone. It is not wired into the Coordinator workflow.

## L12 — Not connected to Companion
The importer is not wired into the Companion CLI.

## L13 — Not Case Bundle v0.2
This is a Histor-lite-style reasoning case record, not a Case Bundle v0.2 export.

## L14 — Not production evidence custody
This is a prototype. It must not be relied on as a chain-of-custody, legal evidence,
or production custody system.
