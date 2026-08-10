# Move 82 — Portable Binary Builds (v01)

This directory produces ONE target-specific standalone `witness-verify`
executable for the actual native Android/Termux AArch64 target detected
during the genuine adoption run, together with a machine-readable
build-provenance record.

It changes no verifier behaviour, adds no verification capability, creates
no Rust `PASS` path, changes no reason code, changes no structured-verdict
schema, changes no legacy stdout, and suppresses neither of the two
adopted Python/Rust divergences. Nothing under `rust/` or in the frozen
Python source is modified.

## What "standalone" means here

One target-specific executable that:

- runs without Python;
- runs without the Project Witness source tree;
- runs without Cargo or Rust installed;
- may depend on the target operating system's normal loader and system
  libraries, **but every such dependency is identified honestly** by
  parsing the binary itself;
- is **not** claimed to work on any other operating system or
  architecture.

The Move 82 Phase 1 inventory found the crate favourable to portability —
no host conditional compilation, no `unsafe`, stdlib-only with zero
external crates, read-only filesystem access, and no environment
dependence beyond `env::args()`. That is a favourable *source* property.
It is not a portability *claim*: only executed evidence on a target
supports one.

## Target evidence

| Target | Classification |
|---|---|
| Android/Termux AArch64 | `NATIVE_BUILD_AND_RUNTIME_TEST_PRACTICAL` |
| Linux x86_64 | `NOT_CURRENTLY_ESTABLISHABLE` |
| Linux AArch64 | `NOT_CURRENTLY_ESTABLISHABLE` |
| Windows x86_64 | `NOT_CURRENTLY_ESTABLISHABLE` |

The produced executable is an Android/Termux binary. It is **not a general
Linux binary**: Android uses Bionic, and `aarch64-linux-android` is a
different target from `aarch64-unknown-linux-gnu`. No runtime evidence
exists for any Linux or Windows target, and none is claimed. The three
unestablished targets are never described with runtime language.

Evidence levels used by this move, weakest to strongest: `compiled`,
`format_validated`, `smoke_tested`, `fixture_tested`, then
adoption-tested and publicly releasable. Only the first four may appear in
a build-provenance record — adoption status is established externally by a
complete successful gate run plus the preserved transcript and its
sidecar, and is never self-declared by a build record.

## No prebuilt executable is packaged

Every Move 82 addition in the candidate archive is text. No prebuilt
`witness-verify` executable is packaged. The release binary and its
provenance record are generated during the genuine Termux adoption run and
preserved separately from the source candidate, each with its own SHA-256
and each bound to the verified candidate hash.

## Components

- `build_binary.py` — invokes the explicitly supplied trusted toolchain.
  It never searches `PATH` and never chooses a default. The invocation is
  exactly the adopted `cargo build -q`, plus `--release` for the release
  profile. There is no `--locked`: the workspace has no dependencies and
  no committed `Cargo.lock`, so `--locked` would fail outright.
- `inspect_binary.py` — parses the executable itself: ELF class,
  endianness, type, `e_machine` architecture, `PT_INTERP` and `DT_NEEDED`
  (deterministically sorted). It depends on no PATH-resolved `file`,
  `readelf`, `objdump` or `ldd`, and Android compatibility is never
  inferred from a filename or from the Cargo command. It writes canonical
  JSON to an explicit `--json-out` file — exactly one object and one
  trailing newline — while the human-readable marker stays on stdout, so
  the gate can parse the file without ambiguity. Only `EXEC` and `DYN` are
  accepted; `REL`, `CORE` and unknown types are rejected. `DT_NEEDED`
  names are read strictly inside the declared dynamic string table
  (`DT_STRSZ` where present), so a malformed offset can never surface
  unrelated file bytes as a dependency name.
- `provenance.py` — the canonical `witness-build-provenance/1` record.
  Build facts only.
- `equivalence.py` — debug/release behavioural equivalence, the standalone
  execution proof, and the hostile numeric/length edge fixtures.
- `check_move82_inherited.py` — baseline immutability against the real
  adopted Move 81 v08 bytes, including safe extraction for the child gate.
- `portable_tests.py` — the focused suite (count pinned in
  `EXPECTED_TEST_COUNT.txt`).

## Debug and release

Every piece of adopted behavioural evidence before Move 82 came from a
**debug** build. The preserved portable artefact is a **release** build.
With no `[profile]` overrides the Cargo defaults differ on `opt-level`,
`debug-assertions` and — the one that matters — `overflow-checks`, which
is on for debug and off for release.

The gate therefore builds both profiles freshly from the same reviewed
source and requires, for every controlled case, an identical exit code and
byte-identical stdout and stderr, plus byte-identical canonical records
through the unchanged Move 81 adapter. The controlled cases include the
clean frozen bundle, the adopted Move 80 corrupted fixtures, archive
fixtures, existing usage behaviour, and hostile numeric and length edge
cases aimed at the ZIP offset/size/count and JSON number/length arithmetic
identified in Phase 1 — precisely where an overflow would panic under
debug and wrap silently under release. Each JSON edge case is built from a
valid frozen bundle by changing only the exact file and field required, and
declares the parser stage it must reach: a fixture answered at an early
stage (a missing manifest or required file) never exercised the targeted
arithmetic and fails the check.

Any divergence is a gate failure. It is not repaired, reinterpreted or
worked around inside the gate, and the release profile is not silently
adjusted to hide it.

## Determinism and reproducibility

Separate builds are **not** claimed to be byte-reproducible. Move 81
deliberately treated reviewed source identity plus a clean trusted build
as authoritative, and nothing here changes that. A binary SHA-256 recorded
in provenance is the identity of that specific produced artefact, not a
reproducibility guarantee.

## Source binding

The candidate archive's hash is verified against an externally supplied
value, and the LIVE tree is then proven byte-identical to that verified
archive in both directions: every packaged file present in the tree with
identical bytes, every live source file present in the archive, and
executable bits consistent. Hash-verifying the archive while only
path-checking the tree would let a modified allowlisted file through,
binding the generated binary to reviewed names rather than reviewed bytes.

## Controlled behaviour

Correctness is never derived from two newly built binaries agreeing. The
complete adopted corpus is the clean frozen bundle, all eight Move 80
fixtures, and all 70 adopted archive cases — 67 built by the adopted
`corpus/build_archives.py` after its `corpus_lock.json` pins are verified,
plus three cases whose input is a real supplied artifact. Every case
appears exactly once.

Each case is subject to three independent requirements: each candidate
profile must match the adopted SEMANTIC expectation from the frozen
corpora; each must match the adopted BASELINE authority's exact stdout
bytes, stderr bytes and exit code (a Move 81 v08 verifier freshly built
from a private extracted copy of the adopted archive); and the two
candidate profiles must match each other. Archive expectations are
compared as adopted reason CLASSES resolved through `reason_map.json`,
which is the vocabulary that corpus uses.

Every record is checked in full: adopted verifier identity, adopted
version, the exact field set with no extra or missing fields, the exact
verdict and reason, the exact exit code, single-object framing and zero
stderr bytes.

## Publication

On success the output directory contains exactly four files: the release
binary, its `.sha256` sidecar, the provenance record and its `.sha256`
sidecar, each sidecar in the standard `<sha256><two spaces><basename>`
form. Publication is failure-atomic: any copy, chmod, hashing, validation
or verification failure rolls back every partially published file, so a
failed gate leaves the output directory exactly as empty as it began.
After publication the binary hash is recomputed against `binary_sha256`,
both sidecars are verified, and the copied provenance is re-parsed and
re-validated.

## Standalone proof

The gate copies the generated release binary into a private directory
outside the candidate source tree, copies in only the controlled input
each invocation needs, executes the binary by absolute path with an empty
`PATH` and private `HOME` and `TMPDIR`, uses no source-relative paths, and
requires the exact adopted verdict, reason code and exit code, with
single-object stdout framing and completely empty stderr — the clean frozen
bundle must produce `INCONCLUSIVE` / `RECEIPT_CHAIN_HASHES_RECOMPUTED` /
exit 3. No Cargo, rustc, Python, shell script or Rust source is placed in
that directory. Trusted Python and shell surround the binary as test
instrumentation; the point is that the binary invocation itself does not
require them.

The adopted CLI grammar is used exactly as it stands. No `--version` flag
or any other new CLI behaviour is introduced: the emitted version and the
usage behaviour are established through the existing invocations.
