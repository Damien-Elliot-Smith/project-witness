# KNOWN_LIMITATIONS — Case Bundle v0.2

## Scope is deliberately narrow

- Exactly **one Sentinel action case** only.
- Exactly **one Aletheia evidence case** only.
- Exactly **one ODIN reasoning case** only.
- One unified Project Witness case bundle out. No multiple actions, no multiple
  evidence files, no multiple reasoning runs.

## Metadata packaging only

- Case Bundle v0.2 performs **metadata packaging only**. It verifies and copies
  already-produced case records; it computes hashes and a manifest.
- It **does not execute actions** (no Sentinel action is run).
- It **does not run Aletheia** evidence bundling or interpretation.
- It **does not run ODIN reasoning**.

## It does not prove truth

- It **does not prove** the evidence contents are true.
- It **does not prove** that any ODIN claim is true.
- A recorded `CONTRADICTION_DETECTED` means ODIN found a structural contradiction
  among the claims; it does not establish that any claim is false. `CONSISTENT`
  does not establish that any claim is true.
- The bundle proves only that the three verified case records were bundled and
  checksummed, and that their internal integrity re-verifies.

## Explicitly out of scope

- **No natural-language interpretation.**
- **No LLM.**
- **No signing.**
- **No external anchoring.**
- **Not connected to Coordinator.**
- **Not connected to Companion.**

## Honesty boundary

Hashes here are unkeyed. They give tamper-**evidence** within the bundle: any edit
to a packaged file, the manifest, or the checksums is detected on verify. They do
**not** give tamper-**proofness**: a self-consistent whole-folder fabrication — one
where every file, every subcase checksum, the manifest, and the bundle checksums
are all rebuilt to agree — would re-verify. Defeating that requires signing or
external anchoring, which are out of scope here.

This is **not production evidence custody**.
