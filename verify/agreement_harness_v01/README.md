# Move 79 — Python/Rust Agreement Harness (verification-only)

## TWO AXES, NEVER CONFLATED

- **harness status** — did the instrument correctly and reproducibly
  MEASURE the systems?
- **agreement status** — do Python and Rust actually AGREE?

The instrument can be adopted while the systems **disagree**. Two genuine
divergences exist today, so a full run **exits 1**. That is the correct,
honest result — not a bug to be smoothed away.

## The oracle is NOT a trusted verifier

`oracles/zipguard_oracle.py` is a TEST ORACLE. It is never imported by
Companion or any production path; deleting it changes no runtime
behaviour. Agreement between two implementations is never sufficient —
every case carries an **independently declared expectation** with
provenance, and the comparison is three-way.

## Case categories (declared in the frozen corpus BEFORE execution)

- `AGREEMENT_CASE` (79) — both in scope; expected == python == rust
- `SINGLE_IMPLEMENTATION_CASE` (4) — one in scope; the other is
  OUT_OF_SCOPE, run as an **observation** with a complete declared spec,
  never counted as agreement
- `KNOWN_DIVERGENCE_CASE` (2) — both in scope, both reject, but at
  DIFFERENT stages. Documented, counted, and **never passing**.
- `UNSUPPORTED_CASE` (0)

Corpus totals are **locked** (`corpus_lock.json`): 85 cases (70 archive,
15 bundle), exact ID set, exact divergence IDs, required fixtures, and
SHA256 pins on the corpus-defining files. A deleted or renamed case fails
before execution.

## The two known divergences

| case | Python | Rust |
|---|---|---|
| `stage_report_field_missing_repaired` | REPORT_NOT_CANONICAL / canonical_report | REQUIRED_FIELD_MISSING / manifest |
| `stage_manifest_json_invalid` | REPORT_NOT_CANONICAL / canonical_report | MANIFEST_MALFORMED / manifest |

Both reject the same defect at different stages. Neither is wrong under
its adopted contract, so no implementation is reopened. They are
**reported**, never counted as agreement.

## Capability gaps (reported, not closed) — BOTH directions

- **1 Python-only**: report canonicality (`tamper_top_level_report`).
  The other five RT-004 deep-verification cases (nested checksums,
  Aletheia manifest binding, evidence-directory completeness, Sentinel
  source-run binding) were Python-only at Move 78 and are AGREEMENT_CASEs
  since Rust `nested.rs`.
- **3 Rust-only**: receipt-chain verification. Companion's bundle
  verifier contains **no receipt-chain logic** — with declared hashes
  repaired it accepts bundles whose chain is provably broken. Rust
  (Moves 76-77) rejects them. Discovered by this harness.

## Tests

- `self_tests.py` — 63 harness self-tests (fake responders proving the
  instrument fails closed on each false-green class; schema, corpus-lock,
  resource-hygiene, and the forced no-cargo workspace-checker test).
- `gate_test_fixtures.py` — shared, authoritative no-Cargo environment builder (allowlist only; never lists PATH directories), used by all test files
- `gate_unit_tests.py` — 73 adoption-gate UNIT tests (marker/exit matrix,
  warning precedence, build helper, trusted-toolchain resolution incl.
  under-prefix/version/env-sanitize and no-inherited-PATH-command, production builder using $TRUSTED_CARGO
  and ignoring PATH/CARGO, bootstrap trust incl. PREFIX-mismatch rejection and
  single-CARGO_HOME cleanup, measurement-stderr checks, a Termux multicall applet suite
  (entrypoint vs canonical target), Termux exec-preload validation, a
  nested-exec probe, and provenance against controlled baselines).
  Non-recursive.
- `gate_integration_tests.py` — 33 adoption-gate INTEGRATION tests: missing
  inputs (USAGE); the non-Termux INCONCLUSIVE path; the hostile
  fully-fake-environment regression; the fake-`dirname` ROOT-redirection
  regression; a real-symlink `$0`-alias regression proving no fabricated
  adjacent module is sourced, plus the canonicalisation-algorithm test; a
  named-gate preload-ordering fixture (capture-before-unset, validate the
  captured value, restore it, nested-exec PASS); TERM/INT interruption during a measurement (stops before the
  next order, temps cleaned, nonzero exit, no PASS); FLOW_H-cannot-redirect; no
  recursion; and a controlled COMPLETE-gate success fixture driving the real
  `gate_run_flow` (instrument PASS + system FAIL + two divergences, stderr
  rejection, no leaked temps). Recursive, so never run by the gate.

The named gate runs `self_tests.py` AND `gate_unit_tests.py` unconditionally,
warning-clean. It never runs the integration tests. Run all three for the full
Move 79 Python test family:

    python3 -B verify/agreement_harness_v01/self_tests.py
    python3 -B verify/agreement_harness_v01/gate_unit_tests.py
    python3 -B verify/agreement_harness_v01/gate_integration_tests.py

## Real archives are SUPPLIED, never assumed

The real archives are inputs you provide. `<path>` below is a placeholder
for wherever you keep them — they are not bundled and the harness never
searches for them. Each archive used for measurement is SHA256-pinned in
the corpus, so a wrong file fails REAL_CORPUS_HASH_MISMATCH and a missing
one yields INCONCLUSIVE / REQUIRED_CORPUS_UNAVAILABLE. Replace every
`<path>` before running; the commands are NOT copy-pasteable until you do.

## Running the ordinary harness

    # builder machine (no Rust): Python + expectation lanes only
    python3 -B verify/agreement_harness_v01/run_agreement.py \
        --real-705    <path>/project-witness-main-move-70-5.zip \
        --real-move78 <path>/project-witness-MOVE_78_candidate_v10.zip
    # -> INCONCLUSIVE / RUST_TOOLCHAIN_UNAVAILABLE, exit 3

    # full three-way (Termux): --real-v20 defaults to the in-repo copy
    python3 -B verify/agreement_harness_v01/run_agreement.py \
        --rust-bin    rust/target/debug/witness-verify \
        --real-705    <path>/project-witness-main-move-70-5.zip \
        --real-move78 <path>/project-witness-MOVE_78_candidate_v10.zip
    # -> FAIL / BEHAVIOURAL_DIVERGENCE_DETECTED, exit 1  (2 divergences)

`--rust-bin` belongs to the ordinary harness only. The adoption gate does
NOT accept a binary override (see below).

## The adoption gate (the Move 79 adoption decision)

    REAL_MOVE78=<path>/project-witness-MOVE_78_candidate_v10.zip \
    REAL_705=<path>/project-witness-main-move-70-5.zip \
        sh tools/check_move79_instrument_adoption.sh
    # -> MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS
    #    SYSTEM_AGREEMENT_RESULT: FAIL
    #    SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED

BOTH `REAL_MOVE78` and `REAL_705` are **mandatory and validated up front**:
a missing input yields `USAGE` / exit 2 before any preflight, so the gate
never launches measurements only to discover a required archive was never
supplied. `REAL_V20` is optional and defaults to the in-repo Move 70 v20 zip.
There is **no RUST_BIN, no CARGO override, and no PATH-based builder
selection**: the gate builds only with the CANONICAL toolchain
(`$PREFIX/bin/{cargo,rustc}` on Termux, resolved with `readlink -f`, required
beneath the prefix, versions pinned to 1.96.0), with build-affecting
environment variables sanitized and a fresh empty `CARGO_HOME`, and measures
only that clean build. Every measurement process must produce **zero bytes of
stderr**; any stderr (a warning, a post-report traceback) is an instrument
FAIL, never expected disagreement.

The gate first canonicalises its own script target: it sanitizes dangerous
inherited variables with built-ins, then resolves $0 with the LITERAL trusted
Termux readlink (`/data/data/com.termux/files/usr/bin/readlink -f -- "$0"`),
requires the real path to be `.../tools/check_move79_instrument_adoption.sh`,
and derives ROOT from that real path — so a symlink alias in an attacker tree
cannot redirect it to fake adjacent modules. Off Termux (that readlink absent)
it refuses at canonicalisation (INCONCLUSIVE) before sourcing anything. BEFORE
any preflight it runs `gate_bootstrap` (tools/gate_bootstrap.sh), having sourced
only that file from the canonical ROOT:
it resolves sh/python3/cargo/rustc/timeout/readlink/sha256sum/mktemp only from
beneath the LITERAL Termux prefix `/data/data/com.termux/files/usr` (never the
inherited PREFIX), pins cargo/rustc to 1.96.0, sanitizes interpreter/build
environment variables, replaces PATH with a minimal trusted PATH, creates one
CARGO_HOME, and installs a dedicated EXIT cleanup trap plus HUP/INT/TERM
handlers that terminate the active measurement child, remove every tracked
temp, and exit nonzero (an interruption cannot continue into the next
measurement). gate_lib.sh and gate_flow.sh are sourced only after trust exists. Off
Termux (no literal prefix) the gate reports INCONCLUSIVE and refuses to run; a
caller-created PREFIX that differs from the literal is rejected (FAIL). Then it
runs seven preflight stages with absolute trusted interpreters (package hygiene;
unconditional strict warning-clean self-tests; unconditional strict
warning-clean gate unit tests; adopted-immutable; src-matches-release;
current-release-state; and a REQUIRED post-preflight package-hygiene PASS),
then delegates the decisive path to `gate_run_flow` in `tools/gate_flow.sh`: source provenance
(structural pin cross-check plus derivation against the real adopted artifact,
with baseline/candidate scope enumerated and pin metadata checked); fail if
`rust/target` exists; resolve the canonical toolchain (unavailable -> exit 3);
run the workspace checker under it, rejecting any warning text; require the
exact PASS marker and exit 0; remove `rust/target` and confirm it is gone;
build once with the canonical cargo; require exactly
`rust/target/debug/witness-verify`; then run three order-specific measurements,
each of which must exit consistently AND produce empty stderr. The same
`gate_run_flow` is driven by a controlled fixture with injected seams (never a
production bypass) to test the complete successful path.

## Source-pin design (why documentation is NOT pinned, and how it is derived)

The gate binds to **behaviour-determining Rust source only** — `*.rs` and
`Cargo.toml` (10 files). `rust/README.md` and all documentation are
**deliberately excluded**, because `tools/check_rust_workspace.sh`
**requires** the rust README status line to name the current step, so it
MUST change every Rust move; pinning it would make one rule forbid what
another mandates. Documentation correctness is enforced by the workspace
checker, which is the right instrument for it.

The pin (`tools/rust_source_pin.json`) is **derived, not self-certified**.
It records, for every pinned file, its hash in the adopted Move 78 v10
baseline and its hash in this candidate. At adoption time the gate opens the
**real adopted artifact** (`REAL_MOVE78`), verifies its SHA256, derives the
baseline hashes from its actual bytes, and requires them to match the pin —
so a falsified baseline (for example hashes rewritten to zeros) fails. Eight
of ten files are byte-identical to the adopted baseline; the two that changed
carry the reviewed Move 79 delta (version bump plus the additive read-only
`entry_count` diagnostic — no verdict logic, precedence, or check ordering
altered). The recorded path list also makes the SCOPE auditable: adding or
removing a `.rs` file changes the recorded list, so scope cannot drift
silently.

## Hygiene

The instrument must not mutate the baseline it measures. Bytecode writing
is disabled in-process and in every subprocess; `tools/check_package_hygiene.sh`
runs before and after.
