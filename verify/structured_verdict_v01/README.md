# Move 81 — Structured-Verdict Output (v01)

This directory adds a deterministic, machine-readable structured-verdict
output boundary around the adopted Project Witness verification lanes. It
is additive: it changes no adopted verifier, no default command output, no
verdict behaviour, and adds no verification capability.

## What Move 81 is

Move 81 upgrades the verification OUTPUT CONTRACT so it can represent the
complete `PASS` / `FAIL` / `INCONCLUSIVE` vocabulary with deterministic
structured reason codes aligned to Witness language. A verdict is only
ever emitted for a lane that has an adopted evidential basis for it.

- The legacy Rust `witness-verify` binary's default JSON output is NOT
  changed. Move 81 does not modify `rust/` or the frozen Python source.
- No Rust `PASS` path is introduced. A healthy Rust bundle remains
  `INCONCLUSIVE` (exit 3); archive-safety success remains `INCONCLUSIVE`
  (exit 3). If the adapter ever observes a Rust `PASS`, it is treated as
  an impossible verdict/exit pairing and reported as a measurement error,
  never as a verdict.
- Rust gains no new verification capability.

The adapter (`adapter.py`) invokes the existing adopted commands exactly
as adopted, captures their output internally, validates it, and emits one
canonical structured record. `schema.py` defines only fixed structural
constants and allowed-value enums. Adopted reason-code and stage
resolution comes exclusively from the inherited frozen reason map
(`verify/agreement_harness_v01/reason_map.json`), supplied at run time via
an explicit `--reason-map` path; this directory does not copy or
re-maintain those mappings. That map is validated COMPLETELY when it is
loaded — before any verifier is invoked — covering entry shape, a known
`match_type`, a non-empty string `value`, compilable `regex` values, and
non-empty string `class` and `stage`. An unusable `--reason-map` is
adapter CLI misuse: exit 2, no record, deterministic usage text on stderr,
and no verifier is ever launched.

The same tool also performs the Stage F baseline extraction: given
`--extract-to`, it hash-verifies the adopted baseline, fully safety-
inspects it (duplicates, traversal, absolute paths, backslash ambiguity,
symlinks, special files, encryption, single canonical root, CRC) before a
single byte is written, extracts into a private gate-owned directory with
every member re-checked against the destination boundary, and prints the
single extracted root. The complete unchanged Move 80 adoption gate is run
from that extracted root rather than from the Move 81 candidate root,
because the Move 80 gate validates its own tree against Move 79 and
permits only the Move 80 addition set — so the legitimate Move 81
additions would otherwise appear undeclared.

Every launch-time failure of an underlying implementation — a missing
file, a permission refusal, an invalid executable format, or any other
OS-level refusal to start the process — becomes a single canonical
`measurement_error` with `ADAPTER_INVOCATION_ERROR` and adapter exit 1. No
`exit_code` is recorded in that case, because the process never completed
normally and no exit status is honestly established.

## Trust model

The adapter never searches `PATH` and never chooses defaults. Every
implementation and authority path is supplied explicitly as an absolute
path and validated (`--python-bin`, `--python-entry`, `--rust-bin`,
`--reason-map`). The adapter executes what it is explicitly given; it does
not itself assert those paths are trusted. The Move 81 adoption gate is
responsible for resolving and validating trusted paths — the trusted
Python binary, the freshly built Rust binary of the exact expected
version, the inherited Python entry point, and the inherited frozen reason
map — and passing those exact absolute paths to the adapter.

## Record types

Every record carries the mandatory envelope: `record_type`,
`schema_version` (`witness-verdict/1`), `producer`
(`witness-structured-verdict-adapter`), and `producer_version`
(`0.0.1-step81-structured-verdict`).

- `verdict` — a completed lane verdict.
- `comparison` — both complete lane records plus a separate
  `comparison_status`; never a merged verdict. The status is derived from
  the frozen comparison authority (`bundle_cases.json`), not guessed: the
  adapter is given a `--case-id` and a `--comparison-contract`, runs each
  in-scope lane, and compares the actual lane records against that case's
  adopted expected outcomes. A lane that is `out_of_scope` for the case is
  legitimately `null` (its `comparison_status` is `LANE_NOT_APPLICABLE`);
  an attempted lane that fails is preserved as its full `measurement_error`
  record and is never `null`.
- `measurement_error` — an adapter-layer failure; never a fabricated
  verdict, reason code, or stage. The comparison authority itself can
  raise one: an invalid contract or an unknown case id emits a single
  top-level `measurement_error` with `operation` = `compare` and the code
  `ADAPTER_COMPARISON_CONTRACT_INVALID` or `ADAPTER_UNKNOWN_CASE_ID`,
  carrying `input_type` = `bundle_dir` — never a comparison record with
  both lanes null.

Before either lane runs, the supplied comparison contract is completely
validated, structurally and semantically. Structural: top-level object;
the corpus lane identifier (so a bundle comparison cannot silently use the
archive corpus); `cases` a list; every case an object with a unique,
nonempty, non-whitespace safe `case_id`; a per-case `lane` matching the
corpus; a valid `category`; valid `python_scope`/`rust_scope`; an
`expected` object. Semantic: category/scope consistency; a well-formed
expected record for every in-scope lane with correct types, an adopted
`(verdict, exit_code)` pairing, no usage exit 2, and only verdicts that
lane can currently reach (so a Python `INCONCLUSIVE` or a Rust `PASS`
expectation is rejected); a valid `normalized_outcome` consistent with
every in-scope lane's verdict under the adopted agreement semantics; for a
`KNOWN_DIVERGENCE_CASE` a present `expected_divergence` whose class and
stage values exactly match the expected lane records; and a well-formed
out-of-scope observed record when one is present. Category semantics are
enforced too: an `AGREEMENT_CASE` must agree on both the reason class and
the decisive stage across the lanes, while a `KNOWN_DIVERGENCE_CASE` must
actually diverge on at least one of those and must remain a REJECTED
outcome. Any failure fails closed deterministically with no traceback and
no stderr.

## capability_scope values

`capability_scope` is a fixed, per-lane honest statement of what a lane
can currently establish. It is never computed from untrusted input.

- `python_reference_pass_fail` — the Python reference lane emits only its
  currently reachable `PASS` / `FAIL` outcomes. It does not emit
  `INCONCLUSIVE`; that verdict is simply never produced by this lane (it
  is not forced).
- `rust_read_only_no_pass` — the Rust bundle verifier is read-only and
  cannot emit `PASS`; its reachable verdicts are `FAIL` and
  `INCONCLUSIVE`, where a healthy bundle is `INCONCLUSIVE` (exit 3).
- `archive_safety_only` — the archive lane performs archive-safety
  inspection only; its reachable verdicts are `FAIL` and `INCONCLUSIVE`,
  where a safe archive is `INCONCLUSIVE` (exit 3).

## Verifier version identity

`verifier_version` comes only from the executing verifier's own
authoritative version constant, never from the input bundle (which is
untrusted).

- Rust lane: the version the executing binary embeds in its own emitted
  output line. The adapter also requires that line to self-identify as
  `witness-verify`; an absent, empty, or different `verifier` field is a
  measurement error (`ADAPTER_VERIFIER_IDENTITY_MISMATCH`), never inferred
  from the selected lane.
- Python lane: the adopted implementation exposes an authoritative
  version constant, `COMPANION_CLI_VERSION` in
  `src/12_companion_cli_v031/companion_lib/versions.py`. The adapter reads
  this constant from the implementation's own source tree (the sibling of
  the supplied `--python-entry`), never from the bundle being verified. If
  a Python implementation without such a constant were supplied,
  `verifier_version` would be omitted for that lane (never emitted as
  `"unknown"`, and never a reason to fail an otherwise valid verdict).

## detail field

`detail` is optional. It is included only when a deterministic safety
check proves it contains no absolute paths, temporary-directory names,
host-specific values, timestamps, random values, nondeterministically
ordered data, or input-derived path disclosure; otherwise it is omitted.
Underlying raw stdout and stderr are preserved separately as test/gate
evidence when needed, and never contaminate the canonical record.

## Exit contract

- Verdict record: `PASS` → 0, `FAIL` → 1, `INCONCLUSIVE` → 3.
- Underlying measurement failure (malformed, incomplete, contaminated,
  timed-out, signalled, usage-exit, or otherwise unusable underlying
  output): one `measurement_error` record, adapter exit 1. An underlying
  exit 2 is `ADAPTER_INVOCATION_ERROR`, not a verifier verdict, and it
  takes PRECEDENCE over all output framing: a lane that completes normally
  with exit 2 is reported as an invocation failure with `exit_code` 2
  preserved, and its stdout/stderr is never parsed or reinterpreted as a
  verifier result — so ordinary usage text on stderr never surfaces as
  `ADAPTER_UNEXPECTED_STDERR`, and an empty stdout never surfaces as
  `ADAPTER_INCOMPLETE_RESULT`.
- Adapter's own command-line usage error: exit 2, no record emitted,
  deterministic usage text to stderr.

`exit_code` is recorded on a record only when the underlying process
completed normally. On signal termination the adapter emits
`ADAPTER_SIGNAL_TERMINATION` and exits 1 with NO `exit_code` field: a
negative subprocess return code is signal metadata, not a process exit
code, and is never reported as one.
- Comparison record: `AGREEMENT` / `DECLARED_DIVERGENCE` /
  `LANE_NOT_APPLICABLE` → 0; `UNEXPECTED_DIVERGENCE` / `MEASUREMENT_ERROR`
  → 1. The status is decided against the frozen comparison authority:
  `AGREEMENT` when both in-scope lanes match the case's adopted expected
  outcomes and the case is an agreement case; `DECLARED_DIVERGENCE` when
  both match and the case is a known-divergence case;
  `LANE_NOT_APPLICABLE` when the sole out-of-scope lane is null and the
  in-scope lane matches its expected outcome; `UNEXPECTED_DIVERGENCE` when
  an in-scope lane does not match its adopted expected outcome; and
  `MEASUREMENT_ERROR` when an attempted lane could not be measured. It is
  never a merged verifier verdict, and the separate lane verdicts and exits
  remain intact inside the object.

## Comparison error semantics (exact)

There are two distinct failure shapes, and they are not interchangeable.

**A. Invalid comparison contract, or unknown case ID — before any lane
runs.** The authority itself could not be established, so no comparison
exists to report:

- `record_type` = `measurement_error` (top level)
- NO `comparison_status` field
- `operation` = `compare`
- `input_type` = `bundle_dir` (the input directory is validated before
  authority lookup, so its type is honestly established)
- `measurement_error_code` = `ADAPTER_COMPARISON_CONTRACT_INVALID` or
  `ADAPTER_UNKNOWN_CASE_ID`
- adapter exit 1, and neither verifier lane is invoked
- no lane fields and no fabricated lane verdicts

**B. A valid case where an attempted lane cannot be measured.** The
comparison genuinely happened, so a comparison record is emitted:

- `record_type` = `comparison`
- `comparison_status` = `MEASUREMENT_ERROR`
- the affected attempted lane contains its COMPLETE `measurement_error`
  record — never null, never elided
- the unaffected lane, if it completed normally, remains present as its
  complete verdict record
- `null` remains allowed ONLY for a genuine adopted out-of-scope lane
  under `comparison_status` = `LANE_NOT_APPLICABLE`

## Output discipline

One adapter invocation emits exactly one canonical top-level JSON object
followed by exactly one newline: UTF-8, sorted keys, `","`/`":"`
separators, no timestamps, no random identifiers, no absolute or temporary
paths, no host-specific details. Output is byte-identical for identical
input, implementation, version, and policy.

## Tests

`structured_tests.py` is the focused suite (count pinned in
`EXPECTED_TEST_COUNT.txt`). It uses a stdout-bound runner and is
warning-clean (empty stderr on success). It covers every schema field and
allowed value, canonical encoding and determinism, per-lane verdict
normalization, the rejection of an impossible Rust `PASS`, reason-map
derived stages, every fail-closed condition, the comparison statuses with
both lane records preserved, and the preservation of the legacy default
output.

The suite is target-portable: it assumes no desktop filesystem paths.
Both the interpreter and the shell it uses are resolved once at import,
before any test can alter `PATH`, and validated as absolute, canonical,
regular, executable files. The adoption gate supplies the exact trusted
shell via `MOVE81_TEST_SH="$TRUSTED_SH"`; off device, a single explicit
`shutil.which("sh")` fallback runs at import time and is then
canonicalized and validated. Every executable fixture is generated
through one helper that writes the exact resolved interpreter as its
shebang, so no fixture needs `/usr/bin/env` or a PATH lookup. Every test
subprocess carries an explicit timeout.
