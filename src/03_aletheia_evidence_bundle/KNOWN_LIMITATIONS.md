# Known limitations — Aletheia Evidence Bundle v0.1

Aletheia Evidence Bundle v0.1 is a deliberately narrow prototype component. The
following limitations are explicit and accepted for this milestone.

## L1 — One local file only
A bundle holds exactly one local evidence file. No multi-file bundles.

## L2 — No directories
Directory sources are refused. Only a single regular file.

## L3 — No web evidence
No URLs, no fetching, no network access of any kind.

## L4 — No sensors
No camera, microphone, location, or other sensor capture.

## L5 — No OCR
The file is treated as opaque bytes; no text is extracted from images or scans.

## L6 — No LLM interpretation
No language model is involved. Contents are never interpreted, summarised, or
classified.

## L7 — No truth verification
The bundle proves the file was preserved and its hash is consistent. It makes **no
claim** that the contents are true, accurate, complete, safe, or authentic.
`VERIFIED_PRESENT` is an integrity verdict only.

## L8 — No signing
Nothing in the bundle is cryptographically signed.

## L9 — No external anchoring
No hash is anchored to an external log, timestamp authority, or notary.

## L10 — Hash-based integrity only
Integrity rests on unkeyed SHA-256. This gives tamper-evidence for point mutations
within the bundle; it does not authenticate origin.

## L11 — Whole-bundle fabrication remains possible
Because nothing is signed or anchored, a fully reconstructed, internally consistent
bundle (manifest + checksums + evidence file all recomputed) will verify. This is a
known and disclosed limitation, not a defect of v0.1.

## L12 — File size limit
v0.1 refuses source files larger than 10 MB (10 * 1024 * 1024 bytes).

## L13 — Not production evidence custody
This is a prototype. It must not be relied on as a chain-of-custody, legal
evidence, or production custody system.
