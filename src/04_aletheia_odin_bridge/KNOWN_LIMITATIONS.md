# Known limitations — Aletheia -> ODIN Bridge v0.1

The bridge is a deliberately narrow connector. These limitations are explicit and
accepted for this milestone.

## L1 — One evidence bundle only
One Aletheia Evidence Bundle v0.1 -> one ODIN claim set. No multiple evidence files,
no directories.

## L2 — Aletheia v0.1 only
It reads the Aletheia Evidence Bundle v0.1 manifest shape. No other evidence source.

## L3 — ODIN v0.1 only
It generates ODIN Claim Reasoner v0.1-compatible claims and (optionally) validates
them with frozen ODIN v0.1. No other reasoner.

## L4 — Integrity/presence claims only
It generates exactly `evidence.present` and `evidence.integrity_verified`. No other
predicates. It will never emit a truth/authenticity claim about contents.

## L5 — No truth verification
The bridge does not prove, and does not claim, that the evidence contents are true,
accurate, authentic, or real. `CONVERTED` is an integrity-conversion verdict only.

## L6 — No natural language
No natural-language parsing, generation, or interpretation.

## L7 — No LLM
No language model is involved anywhere.

## L8 — No signing
Nothing in the output is cryptographically signed.

## L9 — No external anchoring
No hash is anchored to an external log, timestamp authority, or notary.

## L10 — Not connected to the main Companion workflow yet
The bridge stands alone. It is not wired into Companion, Coordinator, Histor, or
Case Bundle.

## L11 — Does not copy or re-verify the evidence bytes itself
v0.1 copies the manifest, not the evidence file. It trusts frozen Aletheia's verify
result for the bundle and the manifest's self-reported `evidence_status`; re-run
Aletheia verification separately if independent confirmation is required.

## L12 — Hash-based integrity only; whole-folder fabrication remains possible
Integrity rests on unkeyed SHA-256 within the output folder. A fully reconstructed,
internally self-consistent output can pass `verify`. This is tamper-evidence, not
tamper-proofness, and needs signing + anchoring (out of scope).

## L13 — Not production evidence custody
This is a prototype. It must not be relied on as a chain-of-custody, legal evidence,
or production custody system.
