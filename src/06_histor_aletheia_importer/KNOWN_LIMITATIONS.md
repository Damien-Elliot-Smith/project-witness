# Known limitations — Histor-lite Aletheia Importer v0.1

The importer is a deliberately narrow connector. These limitations are explicit and
accepted for this milestone.

## L1 — One Aletheia evidence bundle only
One Aletheia Evidence Bundle v0.1 -> one evidence case record. No multiple evidence
files.

## L2 — Aletheia v0.1 only
It reads the Aletheia Evidence Bundle v0.1 manifest shape. No other evidence source.

## L3 — Metadata import only
It records integrity/presence metadata. It does not import or interpret the evidence
file's contents.

## L4 — Does not copy the evidence file
The evidence file itself is never copied into the case record. Only the manifest
metadata and hashes are recorded.

## L5 — Does not import ODIN reasoning
No ODIN claims, no reasoning. This importer is metadata-to-case only.

## L6 — Does not prove truth
The case record proves Aletheia integrity metadata was preserved. It does not prove,
and does not claim, that the evidence contents are true, accurate, authentic, or
real.

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
This is a Histor-lite-style evidence case record, not a Case Bundle v0.2 export.

## L14 — Not production evidence custody
This is a prototype. It must not be relied on as a chain-of-custody, legal evidence,
or production custody system.
