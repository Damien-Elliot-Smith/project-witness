# Project Witness — Handoff for Moves 71–85 (Rust hardening block)

## Read this first: what this document is, and is not

This is a **supplemental handoff for the Moves 71–85 Rust-hardening
block only**.

The inherited Part One documents — `START_HERE.md`, `README.md`,
`CURRENT_RELEASE_STATE.md` and `MOVE_INDEX.md` — describe the **earlier
adopted state** of the project. They predate this block and none of them
mentions any Move in the 80s.

**They have deliberately not been rewritten.** They are adopted bytes and
Move 85 modifies no inherited file. This document does **not**
retroactively alter their historical claims; where it and they differ
about the current state, this document covers Moves 71–85 and they cover
what came before.

---

## 1. What you have received

A source archive. **No executable is included** — the archive contains
zero ELF members. The verifier is built from source by the adoption gate,
which also produces its provenance record and publishes both alongside the
audit pack. If you were handed a binary, it did not come from inside this
archive.

## 2. Which baseline this derives from

The Move 85 candidate derives from exactly one adopted artifact:

```
project-witness-MOVE_84_candidate_v07.zip
SHA-256: 0c06017a871adc23b50bdfda272a30fb6843dbb50fbb4632284b037090e7e880
```

Every one of that artifact's 907 files is preserved byte-identically; Move
85 adds ten files and modifies none. The chain behind it is
84 → 83 → 82 → 81 → 80 → 79, each move adopted only after a genuine
first-run gate on a real device, and each gate rerunning its predecessor.

## 3. How to verify the hashes you were given

Recompute, then compare against the value supplied to you **separately**
from the artifact:

```
sha256sum project-witness-MOVE_85_candidate_vNN.zip
```

A hash that travels inside the thing it describes proves nothing. Every
identity in this project is supplied externally and checked against a
recomputation — that is why the adoption gates take the expected hash as
an input rather than reading it from the candidate.

## 4. How to run the supported verifier

The gate builds it; to build it yourself, from the `rust/` workspace:

```
cargo build --release
```

Zero external crates are required. Four invocations exist, each taking
exactly one argument:

```
witness-verify verify <bundle-directory>
witness-verify inspect-archive <archive.zip>
witness-verify report-bundle <bundle-directory>
witness-verify report-archive <archive.zip>
```

`verify` accepts directories only. `inspect-archive` is read-only.

## 4a. What the Move 85 gate publishes

The Move 85 adoption gate publishes `audit_pack_v1/` into its output
directory. **That audit pack is the Move 85 roadmap deliverable.** It
contains the clean, tampered and corrupted bundles, both lanes' captured
outputs, instructions and known limits, with `SHA256SUMS` covering every
published file.

The same directory also receives the standalone `witness-verify` binary
and its build-provenance record. Those are **supporting measurement
machinery** — how the pack's measurements were taken. The audit pack is
the deliverable; the binary is not the deliverable.

## 5. How to reproduce the demonstration

The Move 84 tamper-and-detect demonstration lives in `verify/demo_v01/`.
Build the fixtures, establish expectations from an adopted verifier, then
demonstrate against your build; `verify/demo_v01/README.md` gives the
exact commands. The audit pack published by the Move 85 gate contains the
same three cases with both lanes' captured bytes and instructions for
reproducing each measurement.

## 6. What successful execution actually means

The demonstration exiting 0 means **only** that every expected observation
was genuinely reproduced.

It does **not** mean the tested bundle is universally valid, that the Rust
verifier detects every tamper, or that the Rust verifier passed. It cannot
pass — see section 7.

## 7. PASS, FAIL and INCONCLUSIVE

The two lanes do not share a verdict vocabulary.

| Lane | Clean bundle | Detected tamper |
|---|---|---|
| Python companion | `PASS`, exit 0 | fails, exit 1 |
| Rust `witness-verify` | `INCONCLUSIVE`, exit 3 | `FAIL`, exit 1 |

**`INCONCLUSIVE` is not `PASS`.** It is the Rust verifier's honest ceiling
for a clean bundle: no single stage makes a bundle valid, so no stage
reports one as valid.

Two distinct statements are made about PASS, and they are deliberately not
merged:

- **Source-level contract.** The adopted Rust source declares exactly two
  verdict constants, `VERDICT_FAIL` and `VERDICT_INCONCLUSIVE`. There is
  no PASS verdict constant. This is machine-checked from adopted bytes.
- **Empirical.** No Rust PASS was observed across the adopted tested
  corpus and the audit-pack surfaces.

Neither establishes that no reachable PASS-producing path exists anywhere
in the program. Finite execution cannot establish global reachability, and
**no such proof is claimed**.

## 8. What the Rust verifier does and does not verify

**Does:** manifest structure, then the declared hashes of the eight
top-level declared files, then the receipt chain — stopping at the first
failure. For archives, one archive-safety check.

**Does not:** nested component checksum files. This matters concretely.
The genuine evidence payload
`coordinator_output/aletheia_bundle/evidence/evidence_001.bin` is declared
in a **nested** checksum file, not among the top-level declared files.
**A single-byte tamper there is not detected by the Rust verifier**, and
its output is byte-identical to the clean bundle. The Python lane does
detect it.

This is a real, currently unrepaired limit. The audit pack includes that
case deliberately, and the adoption gate **fails if the blindness is not
observed** — so it cannot quietly disappear from the record.

## 9. Known divergences

Python and Rust are **not** behaviourally equivalent, and this is not
treated as a defect to hide. Two adopted divergence IDs remain, read at
run time from the adopted Move 79 gate rather than from any list written
by this move:

```
stage_manifest_json_invalid
stage_report_field_missing_repaired
```

The generic markers also remain visible in every gate transcript:

```
SYSTEM_AGREEMENT_RESULT: FAIL
SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED
```

That is expected. It is not an adoption failure.

## 10. Which platform has genuinely been tested

| Platform | Status |
|---|---|
| Android / Termux AArch64 | **Build- and runtime-tested** |
| Linux x86_64 | **Unestablished** |
| Linux AArch64 | **Unestablished** |
| Windows x86_64 | **Unestablished** |

**An Android/Termux AArch64 binary is not a generic Linux AArch64
binary.** They are different targets. Nothing here establishes that the
verifier builds or runs anywhere but the tested platform.

Build provenance records measured facts about **one** build. It does not
establish reproducible builds, and no reproducibility claim is made.

## 11. Distinguishing tested facts from unestablished claims

Every public-facing claim carries a status in
`verify/audit_pack_v01/adopted_facts.json`, drawn from a fixed vocabulary:

- `historically_established` — established by adopted evidence in an
  earlier move; Move 85 does not re-establish it;
- `freshly_reproduced_by_move_85` — measured again by this move's gate;
- `established_android_termux_aarch64_only` — measured, on that platform
  only;
- `source_level_contract` — a structural property of adopted source,
  machine-checkable, **not** a runtime or reachability proof;
- `known_limitation` — a real limit, deliberately preserved and visible;
- `unestablished` — not established by any evidence this project holds;
- `not_claimed` — deliberately not asserted.

**That file is a claim manifest, never an authority.** Each entry names
the external authority that establishes it and how the gate checks it. The
gate compares the manifest against those authorities — externally supplied
artifacts with externally pinned hashes, adopted gate and source bytes, or
fresh execution — never the reverse. Nothing is established merely because
that file, or this document, says so.

If you want to know whether something is true here, run the gate. The
documents report; the gates establish.
