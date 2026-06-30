# Aletheia Evidence Bundle v0.1

A deterministic tool that bundles **one local file** as evidence: it hashes the
file, records metadata in a canonical manifest, writes a checksums file, and can
verify the bundle later. It is the first small piece of Aletheia in Project
Witness.

It proves **preservation and hash integrity only**. It does **not** prove that the
file's contents are true, accurate, safe, or authentic. It makes exactly four
statements: this file was bundled; this is its hash; this is the recorded
metadata; this bundle verifies (or does not).

## What it is

```
local evidence file
  → Aletheia Evidence Bundle
    → evidence_manifest.json   (canonical JSON metadata + hashes)
    → evidence_checksums.txt   (sha256 of the manifest and the bundled file)
    → evidence/evidence_001.bin (a byte copy of the source file)
  → verify bundle
```

This component is **not connected to the workflow** yet. It prepares the stack for
a later path (Companion / Coordinator → Aletheia evidence bundle → ODIN claims →
Histor / Case Bundle), but v0.1 stands alone.

## What it does NOT do

- No directories, no web fetching, no sensors, no image analysis, no OCR.
- No LLM interpretation and no truth claims about file contents.
- No signing, no external anchoring.
- One local file per bundle, up to a **10 MB** size limit (documented, enforced).

## How to build a bundle

```bash
python3 aletheia.py bundle-file \
  --file /path/to/evidence.txt \
  --case-id case_001 \
  --evidence-id evidence_001 \
  --out /path/to/evidence_bundle
```

The source file must be a regular file (not a directory or symlink), within the
size limit, and `case_id` / `evidence_id` must be safe single-segment names. The
output directory must be empty or absent. The copied evidence file is always named
`evidence/evidence_001.bin`; the original filename is preserved in metadata only.
At bundle time the copy's hash must equal the source's hash, or the build is
refused.

## How to verify a bundle

```bash
python3 aletheia.py verify --bundle /path/to/evidence_bundle
```

Verification checks (in order): required files exist; no unknown extra files; the
manifest is valid **and canonical** JSON; the checksums file parses strictly
(required keys exactly once, no unknown keys, well-formed digests); the recomputed
manifest and evidence-file hashes match the checksums file; the manifest's
`bundled_file_sha256` matches the actual bundled file; and the manifest's
`source_file_sha256` equals its `bundled_file_sha256`. Only then does it return
`VERIFIED_PRESENT`.

`VERIFIED_PRESENT` is an **integrity** verdict, not a truth verdict. It means the
bundle is internally consistent and the evidence file is preserved unchanged since
bundling — nothing about whether the contents are true.

## Evidence statuses

`VERIFIED_PRESENT`, `FAILED_MISSING_FILE`, `FAILED_HASH_MISMATCH`,
`FAILED_MANIFEST_INVALID`, `FAILED_CHECKSUMS_INVALID`,
`FAILED_NON_CANONICAL_MANIFEST`. None of these assert truth.

## How to run the release commands

See [RELEASE_COMMANDS.md](RELEASE_COMMANDS.md). The freeze gate is the explicit
list of individual commands plus the static `verify_release_manifest.py`:

```bash
python3 -m compileall -q .
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 selfcheck.py
python3 -O selfcheck.py
python3 -W error::ResourceWarning -m unittest discover -s tests
sha256sum -c aletheia_evidence_bundle_v01.sha256
python3 verify_release_manifest.py
```

There is no wrapper orchestrator in the freeze gate. The build/verify smoke test
is a manual check, not part of the gate.

## Not production evidence custody

This is a local deterministic prototype. Because nothing is signed or anchored, a
whole bundle can be fabricated consistently and still verify. It is tamper-
**evidence** within a bundle, not tamper-**proofness**, and must not be relied on
as a chain-of-custody or production evidence system.
