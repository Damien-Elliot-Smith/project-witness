# Move 84 — Tamper-and-Detect Demonstration

## What this is

An executable, deterministic demonstration of what the **adopted**
verifier genuinely does when a bundle is tampered with — including an
important class of tampering it **does not detect**.

Every value in the transcript is produced by executing the adopted
binaries. Nothing is narrated, predicted or hand-written.

## How to run it

Two stages, in order.

1. **Build the fixtures** from the frozen reference bundle:

   ```
   build_demo_fixtures.py --source <frozen reference_bundle> \
       --outdir <fixture dir> --manifest-out <manifest.json>
   ```

2. **Establish the authority**, then **demonstrate** against it:

   ```
   demo.py --mode establish   --verifier <adopted verifier> ...
   demo.py --mode demonstrate --verifier <candidate verifier> \
       --expectations <from establish> --transcript-out <transcript>
   ```

`establish` runs every case against a verifier built from a privately
extracted, hash-verified copy of the adopted artifact and records its
exact stdout bytes, stderr bytes and exit code. `demonstrate` re-runs the
cases and compares byte-for-byte. Both stages also need `--python-bin` and
`--companion` for the Python lane.

## The three cases

| Case | Python lane | Rust lane |
|---|---|---|
| `clean` | accepts, exit 0 | `INCONCLUSIVE`, exit 3 |
| `toplevel_tamper` | detects, exit 1 | **detects**, `FAIL`, exit 1 |
| `nested_evidence_tamper` | detects, exit 1 | **does not detect**, `INCONCLUSIVE`, exit 3 |

**`clean`** — an unmodified bundle. The adopted Rust verifier has **no reachable PASS path**; `INCONCLUSIVE` with exit 3 is its honest
clean-bundle ceiling and is never described as a pass. The Python lane
does accept the bundle, and both results are shown side by side.

**`toplevel_tamper`** — one byte flipped in a top-level declared file
(`companion_steps.json`). That file set is covered by the adopted Rust
hash stage, so the Rust verifier detects the tamper and reports an exact
reason code. **The reason code is not written down anywhere in this
directory** — it is established by executing the adopted verifier.

**`nested_evidence_tamper`** — one byte flipped in the genuine nested
evidence payload
`coordinator_output/aletheia_bundle/evidence/evidence_001.bin`. The Python
lane detects it and fails at its nested-checksum stage. The adopted Rust
verifier **does not detect it**: it verifies top-level declared hashes
only, and that file is not among them, so its output is byte-identical to
the clean bundle. This is a real, currently unrepaired limit of the Rust
lane, and demonstrating it is a deliberate purpose of this move.

## Fixtures

Each case is copied from the frozen reference bundle and given exactly one
mutation — the frozen Move 71 byte-flip, offset 5, XOR 0xFF. After the
mutation the builder independently re-hashes the whole tree and requires
that the file set is unchanged and that exactly the declared file differs.
Construction is reproducible: the same inputs give the same tree digests.

## What exit 0 means

Exit 0 from `demonstrate` means **only** that every expected observation
was genuinely reproduced.

It does **not** mean the tested bundle is universally valid, that the Rust
verifier detects every tamper, or that the Rust verifier produced a pass.
It cannot produce a pass.

## Determinism

The transcript carries no timestamps, no hostnames, no absolute paths and
no durations. Bundles appear by case id and mutated files by their path
relative to the bundle root. Two runs over unchanged inputs produce
byte-identical transcripts, and the gate checks that.

## What is NOT established off device

This packaging environment has no Rust toolchain. The Python lane is
genuinely executed here; the Rust lane is exercised only through a
stand-in verifier, which tests the driver's logic and establishes nothing
about the adopted binary. The adopted binary is the authority only in the
on-device adoption gate. Android/Termux AArch64 is the only runtime this
project has established.
