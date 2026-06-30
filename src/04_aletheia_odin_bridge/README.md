# Aletheia -> ODIN Bridge v0.1

A deterministic bridge that converts a **verified Aletheia Evidence Bundle v0.1**
into an **ODIN Claim Reasoner v0.1** claim set. It is Move 13 of Project Witness:
the first piece that connects two frozen components.

The bridge reads Aletheia's integrity **metadata only** and creates ODIN structured
claims about **preservation and integrity**. It does **not** interpret the evidence
file contents, and it does **not** prove the contents are true.

## What it is

```
Aletheia evidence bundle
  -> verify the bundle with frozen Aletheia
  -> read evidence_manifest.json (require evidence_status = VERIFIED_PRESENT)
  -> create ODIN-compatible odin_claims.json (integrity/presence claims only)
  -> optionally validate the claims with frozen ODIN
  -> write bridge_report.json + bridge_checksums.txt + aletheia_manifest_copy.json
  -> verify bridge output later
```

This is only the **conversion bridge** — not the full evidence-reasoning demo, and
not connected to the Companion workflow yet.

## It creates only these claims

- `evidence.present`
- `evidence.integrity_verified`

It will **never** generate claims like `contents.true`, `file.authentic`,
`source.trusted`, `statement.proven`, or `image.real`. A guard in the claim builder
refuses any predicate containing a truth/authenticity token, and `verify` rejects
any such predicate if one is ever injected into the output.

## What it does NOT do

- No multiple evidence files, no directories, no web evidence, no sensors, no OCR.
- No LLM, no natural-language parsing.
- No truth claims about evidence contents.
- No signing, no external anchoring.
- It does not copy the evidence file itself (this is claim conversion, not evidence
  custody).

## How to run convert

```bash
python3 bridge.py convert \
  --aletheia-root /path/to/aletheia_evidence_bundle_v01 \
  --odin-root /path/to/odin_claim_reasoner_v01 \
  --bundle /path/to/aletheia_bundle \
  --out /path/to/bridge_output
```

The bridge checks the Aletheia root, ODIN root, and bundle exist; runs frozen
Aletheia verification on the bundle and refuses if it fails; loads the manifest and
requires `evidence_status = VERIFIED_PRESENT`; generates the two integrity/presence
claims; optionally runs frozen ODIN `validate-claims` over them (when `--odin-root`
is given) and refuses if validation fails; then writes the output folder. The output
directory must be empty or absent. `--odin-root` is optional; if omitted, ODIN
validation is skipped and `odin_validation_status` is recorded as `SKIPPED`.

## How to run verify

```bash
python3 bridge.py verify --run /path/to/bridge_output
```

Verification checks: required files exist; no unknown extra files; all three JSON
files are valid **and canonical**; the checksums file parses strictly and matches
recomputed hashes; the report `case_id` matches the claims; the report `evidence_id`
matches the copied manifest; the claims contain only the two allowed predicates and
no truth-like predicate; each support `source_sha256` matches the manifest
`bundled_file_sha256`; and the report `odin_claim_count` equals the actual claim
count. `CONVERTED` is an integrity-conversion verdict, not a truth verdict.

## Output folder

`odin_claims.json`, `bridge_report.json`, `bridge_checksums.txt`,
`aletheia_manifest_copy.json`. The evidence file is intentionally **not** copied.

## How to run the release commands

See [RELEASE_COMMANDS.md](RELEASE_COMMANDS.md). The freeze gate is the explicit list
of individual commands plus the static `verify_release_manifest.py`. The default
unit suite uses in-process fakes for the Aletheia/ODIN boundaries, so the gate
spawns no subprocesses. There is no wrapper orchestrator in the gate.

## Boundaries and honesty

The bridge relies on frozen Aletheia v0.1 to verify the bundle and (optionally)
frozen ODIN v0.1 to validate the claims; at runtime these are invoked via
subprocess. It converts **integrity metadata only**. Because nothing is signed or
anchored, a self-consistent whole-folder fabrication remains possible — this is
tamper-evidence within the output, not tamper-proofness, and not production evidence
custody.
