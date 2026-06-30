# Histor-lite Aletheia Importer v0.1

A deterministic importer that takes a **verified Aletheia Evidence Bundle v0.1** and
records it as a Histor-lite-style **evidence case record**. It is Move 16 of Project
Witness.

It reads Aletheia's integrity metadata, preserves Aletheia's integrity status
exactly, and writes a small case folder (summary + manifest copy + replay report +
checksums) that can be verified later.

> Histor-lite Aletheia Importer v0.1 records verified Aletheia evidence integrity
> metadata only. It does not prove the evidence contents are true.

## What it is

```
Aletheia evidence bundle
  -> verify the bundle with frozen Aletheia
  -> read evidence_manifest.json (require evidence_status = VERIFIED_PRESENT)
  -> write evidence_case_summary.json
  -> write aletheia_manifest_copy.json
  -> write aletheia_replay_report.txt
  -> write evidence_case_checksums.txt
  -> verify the imported evidence case
```

## Which frozen component it reads from

The frozen **Aletheia Evidence Bundle v0.1**. The importer verifies the bundle with
Aletheia (via subprocess at runtime) before reading the manifest, and never modifies
it.

## What it imports

Integrity/presence metadata only: the case_id, evidence_id, Aletheia evidence
status (`VERIFIED_PRESENT`), source file name/size, source and bundled SHA-256
hashes, and the manifest hash. It records this as a Histor-lite-style evidence case.

## What it does NOT import

- It does **not** copy the evidence file itself.
- It does **not** interpret the evidence contents or prove they are true.
- It does **not** import ODIN reasoning.
- It is **not connected to Coordinator or Companion yet**.
- One Aletheia evidence bundle only; no signing, no external anchoring.

## How to run `import-evidence`

```bash
python3 histor_aletheia.py import-evidence \
  --aletheia-root /path/to/aletheia_evidence_bundle_v01 \
  --bundle /path/to/aletheia_bundle \
  --out /path/to/evidence_case
```

The importer checks the Aletheia root and bundle exist; runs frozen Aletheia verify
and refuses if it fails; reads the manifest and requires
`evidence_status = VERIFIED_PRESENT` (refusing any other status); refuses a
non-empty output directory; then writes exactly four files. On success the case
folder contains `evidence_case_summary.json`, `aletheia_manifest_copy.json`,
`aletheia_replay_report.txt`, and `evidence_case_checksums.txt`.

## How to run `verify-case`

```bash
python3 histor_aletheia.py verify-case --case /path/to/evidence_case
```

Verification checks: required files exist; no unknown extra files; the summary and
manifest copy are valid **and canonical**; the checksums file parses strictly
(lowercase digests only) and matches recomputed hashes; case_id and evidence_id
match across the summary and manifest copy; `source_evidence_status =
VERIFIED_PRESENT`; `import_status = IMPORTED_VERIFIED_ALETHEIA`; the source and
bundled SHA-256 hashes in the summary match the manifest copy; and no truth-like
claim appears in the summary or replay report.

## How to run selfcheck

```bash
python3 histor_aletheia.py selfcheck
```

In-process invariant gates only (uses an in-process fake verifier); it never
launches the unit suite or any subprocess.

## How to run the release commands

See [RELEASE_COMMANDS.md](RELEASE_COMMANDS.md). The freeze gate is the explicit list
of individual commands plus the static `verify_release_manifest.py`. The default
unit suite uses an in-process fake Aletheia verifier, so the gate spawns no
subprocesses. There is no wrapper orchestrator in the gate.

## Honesty boundary

The importer records integrity metadata only. Because nothing is signed or anchored,
a self-consistent whole-folder fabrication remains possible — this is
tamper-evidence within the case record, not tamper-proofness, and not production
evidence custody. It does not prove the evidence contents are true.
