# Move 83 — Rust Verifier Report Output (`witness-report/1`)

Move 83 adds structured report generation to the Rust verifier under two
new invocations, and a fail-closed validator for the resulting records.

## Scope (Reading C, as ruled)

The change to `rust/src` is strictly additive and reachable only through
the new invocations:

- `witness-verify report-bundle <bundle-dir>`
- `witness-verify report-archive <archive.zip>`

`verify` and `inspect-archive` are untouched: the same code runs, the same
single legacy line is emitted, the same exit codes are returned, and the
adopted usage text is unchanged — deliberately not extended to mention the
new commands, because its exact stderr bytes are part of the adopted CLI
contract the Move 82 gate asserts.

Exactly one inherited file is modified, `rust/witness-verify/src/main.rs`,
in two hunks: a `mod report;` declaration, and the two new arms placed
after both adopted arms and before the usage fallback. The inherited
checker proves the modification is **strictly additive** — every adopted
line must still be present, in order — so nothing adopted can be altered
or removed under cover of an addition.

## Execution honesty

The adopted evaluation short-circuits: it returns on the first failing
check, so later checks genuinely never run. The report preserves that
exactly. It calls the same check functions in the same adopted order,
stops where the adopted verifier stops, and records every check that did
not execute as `NOT_RUN` with the reason it was skipped.

No `PASS`, `FAIL` or `INCONCLUSIVE` result is ever inferred, invented or
synthesised for a check that never ran. **The report is evidence of what
was executed, never a prediction of what would have happened.** The
validator enforces this: a `NOT_RUN` check may carry no `reason_code` and
no observation, must explain why it was skipped, and no check may report
an executed status after evaluation had already stopped.

## Archive evaluation

The adopted `evaluate_archive` performs exactly ONE check:
`zipguard::inspect_archive`. A missing or unreadable archive is reported
by zipguard with its own adopted reason code. v01 invented an
`archive_path_readable` check, recorded it FAILED, and then still ran and
recorded the safety check — reporting an executed result after evaluation
had already stopped, and inventing a reason code that is not in the
adopted vocabulary. Both are gone: the archive report has one check, and
Move 83 creates no reason code.

## Input digest

`input_digest` covers the **complete** input and says so explicitly in its
own `scope` field:

- for a bundle, sha256 over an **injective** serialization of **every
  entry** in the tree, with a distinct tag per Unix type: 1 regular file,
  2 directory (including empty), 3 symbolic link, 4 FIFO, 5 socket,
  6 block device, 7 character device, 8 unrecognised. The domain prefix is
  `witness-bundle-digest/3`, followed by an entry count, then per entry in
  raw-path-then-kind order: a 4-byte little-endian kind tag, the
  length-prefixed raw relative-path bytes, the actual Unix mode masked
  with `0o7777`, and a length-prefixed payload — a file's content SHA-256
  in hex, a symlink's raw target bytes, a device's 8-byte little-endian
  `rdev`, or empty. So an empty directory changes the digest; a FIFO and a
  socket at the same path with the same mode are distinguished; and two
  device nodes differing only in `rdev` are distinguished. Symbolic links
  are never followed. `file_count` counts regular files only and
  `non_regular_entry_count` counts links, FIFOs, sockets, devices and
  unrecognised entries — directories are bound but counted by neither;
- for an archive, sha256 over the complete archive file bytes.

If the digest cannot be measured, `input_digest.state` is `UNMEASURABLE`
and the value and counts are null. A measurement failure is a digest
state, never a verifier reason code. The validator rejects any
contradiction between state and value or counts.

## Classification

The verifier reports what it EXECUTED. `final_reason_class` and
`final_stage` are defined by the adopted `reason_map.json`, which the
verifier does not and must not read, so the binary emits the CORE record
(`record_type: verification_report_core`) and a completion step looks the
classification up from the adopted bytes and emits
`record_type: verification_report` with exactly two fields added. No
mapping is restated in Rust, in the validator or in the tests — a test
derives every adopted class and stage from the map itself and fails if
any appears as a literal in production code.

A partial digest is never described as representing the whole bundle; the
validator rejects a bundle scope that does not state which files it
covers.

## Focused-suite result validation

`check_focused_result.py` establishes that the suite genuinely succeeded:
the process exited 0, stdout carries exactly one `Ran <N> tests` line
matching the pinned count, the final non-empty line is a valid unittest
success summary, no failure summary appears, and stderr is empty. The
accepted grammar is `OK`, `OK (skipped=N)`, `OK (expected failures=N)` and
the combined form — nothing broader. `unexpected successes` is excluded
because `wasSuccessful()` is False when any occur. Anchoring to the final
line means an `OK` in a test name or in injected output cannot spoof
success.

Skips are reported, never suppressed. The device-node cases legitimately
skip on an unprivileged Android filesystem.

## Fixture mode normalisation

Fixture pairs that claim to differ in exactly one property must establish
that, not assume it. `set_mode()` chmods an entry, reads the mode back
with `lstat` and raises if the filesystem did not take it; it is applied
to every created regular file, FIFO, socket, directory and device node.
Creation defaults, the process umask, Python defaults and platform
behaviour are never relied on — a genuine Termux run created a FIFO at
0600 and a socket at 0644 from calls requesting the same mode. Each test
re-reads both modes and asserts equality before making any type claim. A
symlink's mode cannot be set portably, so it is recorded as absent and no
equality is claimed for it.

## Rust source sanity

`rust_source_check.py` catches gross string-literal and prose-outside-
source corruption cheaply, before the long gate. It requires every
`const NAME: &str = ...;` to hold exactly one literal with no stray tokens
before the semicolon, no surviving quote after literal stripping, and no
run of three or more consecutive non-keyword identifiers outside a
literal.

**It is not a compiler and does not establish buildability.** Only the
gate's clean `cargo build --release`, clean `cargo build` and `cargo test`
do that. A passing Python focused suite says nothing about whether the
Rust builds.

## Report byte contract

One contract governs the report bytes everywhere — production Rust output,
the Rust unit tests, the Python completion layer, the schema validator,
the focused tests and the gate equivalence checks. Reports are canonical
compact JSON with sorted keys, exactly one object, exactly one trailing
newline, no additional stdout and empty stderr. Beyond that, **no
comma-space and no colon-space appears anywhere in the line** — separator
or content — so every report string value is written with semicolons and
sentence breaks instead. A non-canonical core report is rejected outright;
the completion layer never silently reformats it.

## Report schema

`witness-report/1` is a **separate** schema. It does not extend or modify
`witness-verdict/1`, and the validator rejects any record carrying Move 81
verdict fields or Move 82 provenance fields. Reports are canonical JSON:
sorted keys, compact separators, exactly one object, exactly one trailing
newline, no timestamps and no host-dependent values. The bytes themselves
are compared against the canonical re-serialisation, so non-canonical
formatting cannot pass.

## Cross-check against the adopted legacy line

For every case the gate runs the adopted legacy invocation and the new
report invocation on the same input, and requires the report's
`final_verdict`, `final_reason_code`, `exit_code` and `verifier_version`
to agree with the legacy verdict line exactly. Both candidate profiles
must produce byte-identical reports. A report can therefore never
contradict the evaluation it claims to describe.

## Proving the digest binds what it claims

The gate builds paired bundle trees that differ in exactly ONE bound
property and runs the REAL compiled binary over each side with both
profiles:

- `0644` vs `0755` (the case an earlier `readonly()` approximation could
  not distinguish);
- `0600` vs `0644`;
- a mode change on an empty file;
- a mode change at a nested path;
- a content-only difference;
- an identical control pair, which must produce an identical digest.

Each differing pair must produce different digests and each profile must
agree with the other. Hostile filenames — containing a newline, and two
distinct invalid-UTF-8 names — are digested and required not to collide.
The Python serialization model in the focused suite is a supplementary
cross-check of the documented algorithm and is explicitly **not** the
production authority.

## Canonical gate identity

There is exactly one Move 83 gate: `tools/check_move83_report_adoption.sh`.
Its self-binding check requires that exact canonical path, and its marker
family is `MOVE_83_REPORT_ADOPTION_GATE` on every exit path, with
`MOVE_83_REPORT_ADOPTION_GATE: PASS` as the terminal success marker. No
alias, duplicate, symlink or wrapper exists. The Move 82 child gate keeps
its own correct name and markers, because those are its identities, not
this move's.

## Production dependencies

Every local helper this gate invokes is present in the reviewed candidate
before the run; none is created during it. A pre-flight stage requires
each to exist, to be a regular file rather than a symlink, and to be
inside the verified candidate tree.

The build, inspection, provenance and equivalence helpers are ADOPTED
Move 82 files, inherited byte-identical, and are reused at their real
adopted paths under `verify/portable_build_v01/`. They are deliberately
not copied into `verify/report_v01/`: duplicating reviewed code invites
the copies to drift. They therefore appear in neither the addition nor the
modification allowlist.

## Move 82 child run directory

The adopted Move 82 gate derives its run directory from the directory
containing the candidate zip it is given, and requires its output
directory to be inside that run directory yet outside the extracted source
root. The Move 83 gate therefore builds a purpose-made private child run
directory holding the staged (and re-verified) adopted zip, the extracted
adopted source, and a fresh empty `move82_output/`. The adopted
output-directory checker is run against those exact paths before the child
is invoked. It is used as-is and never weakened.

## Regression chain

Move 83's sole inherited baseline is adopted **Move 82 v07**. The gate
privately extracts that verified archive and reruns the complete,
unchanged Move 82 adoption gate from it, supplying that gate's own
mandatory input contract: the verified candidate archive and its adopted
hash, a fresh empty gate-owned output directory outside the extracted
source root, and the `REAL_MOVE81`, `REAL_MOVE80`, `REAL_MOVE79`,
`REAL_MOVE78` and `REAL_705` dependencies it requires. **Move 81 v08 is a
dependency of that child, not the Move 83 baseline** — the gate's labels
and diagnostics say so.

The Rust unit suite is executed by the gate with `cargo test` after the
clean build, with stdout, stderr and exit status preserved separately and
a successful non-empty result line required. A Python source-shape test is
never a substitute for running it.

## What is NOT established off device

This packaging environment has no Rust toolchain, so the report module is
not compiled or executed here. The focused suite exercises the validator,
the inherited-baseline checker and structural properties of the Rust
change. The genuine report bytes are produced and checked only by the
adoption gate on device.
