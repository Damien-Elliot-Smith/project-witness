# Known limitations — Evidence Reasoning Demo v0.1

The demo is a deliberately narrow harness. These limitations are explicit and
accepted for this milestone.

## L1 — One evidence file only
One local evidence file -> one Aletheia bundle -> one bridge conversion -> one ODIN
reasoning run -> one demo report. No multiple files, directories, web, sensors, or
OCR.

## L2 — Aletheia v0.1 only
It drives the frozen Aletheia Evidence Bundle v0.1 CLI. No other evidence source.

## L3 — Aletheia -> ODIN Bridge v0.1 only
It drives the frozen Aletheia -> ODIN Bridge v0.1 CLI. No other bridge.

## L4 — ODIN v0.1 only
It drives the frozen ODIN Claim Reasoner v0.1 CLI. No other reasoner.

## L5 — Integrity/presence claims only
The chain surfaces exactly `evidence.present` and `evidence.integrity_verified`. No
other predicates.

## L6 — No truth verification
The demo proves the chain executes and verifies. It does not prove, and does not
claim, that the evidence contents are true, accurate, authentic, or real.

## L7 — No natural language
No natural-language parsing, generation, or interpretation.

## L8 — No LLM
No language model is involved anywhere.

## L9 — No action gating
The demo does not gate or trigger any action; it only runs and reports.

## L10 — Not connected to Companion
The demo stands alone. It is not wired into the Companion CLI.

## L11 — Not connected to Coordinator
The demo is not wired into the Coordinator workflow.

## L12 — No signing
Nothing in the demo output is cryptographically signed.

## L13 — No external anchoring
No hash is anchored to an external log, timestamp authority, or notary. A
self-consistent whole-folder fabrication remains possible.

## L14 — Not production evidence custody
This is a prototype demo harness. It must not be relied on as a chain-of-custody,
legal evidence, or production custody system.
