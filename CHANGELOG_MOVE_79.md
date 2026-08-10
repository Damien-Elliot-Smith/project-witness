# Changelog — Move 79 (CANDIDATE v27)

## AUTHORITATIVE CURRENT STATE (v27) — read this first

<!-- RUST_TEST_COUNT: 124 -->
<!-- ARCHIVE_REASON_CODE_COUNT: 25 -->
Current Rust markers: 124 tests, 25 archive codes. CHANGELOG_MOVE_78.md is an
ADOPTED historical record (123 tests) and is hash-pinned as immutable; it is
never edited to satisfy a current check.

COUNTS: 85 corpus cases (70 archive, 15 bundle); 74 AGREEMENT,
9 SINGLE_IMPLEMENTATION, 2 KNOWN_DIVERGENCE. Move 79 harness Python tests:
63 harness self-tests (self_tests.py) + 73 adoption-gate unit tests
(gate_unit_tests.py) + 33 adoption-gate integration tests
(gate_integration_tests.py) = 169. The named gate runs self_tests.py AND
gate_unit_tests.py unconditionally, AFTER establishing a trusted execution
environment with NO inherited-PATH command executed beforehand; the recursive
integration tests (controlled complete-gate success fixture, hostile
fully-fake-environment regression, fake-dirname redirection regression, and
TERM/INT interruption tests) are run manually, never by the gate.

TWO AXES, never conflated: harness status (did the instrument MEASURE the
systems correctly and reproducibly?) vs agreement status (do Python and Rust
AGREE?). Two real divergences exist, so a full Rust run exits 1. The
instrument may still be adopted — that is the adoption gate's decision, not a
conversion of disagreement into agreement.

Status: CANDIDATE, NOT ADOPTED. No three-way agreement has been executed on a
real toolchain in this build environment; the real cargo build and the three
real agreement measurements run under the Termux gate. This changelog records
only what was behaviourally verified locally (see the v12 section).


## v27 repairs (corpus-fixture isolation + error-envelope-safe gate)

MILESTONE: v26 ran the ENTIRE production pipeline on real Termux — trusted
bootstrap, cargo/rustc 1.96.0, TERMUX_NESTED_EXEC_CHECK: PASS, 62/62 harness,
73/73 gate-unit, adopted immutability, source/release identity,
current-release-state, package hygiene before and after, a clean Rust target, a
fresh Cargo build of witness-verify 0.0.8-step79-diagnostics, and THREE fresh
measurement processes returning IDENTICAL canonical responses with empty stderr.
The measurements executed. The remaining failure was one un-isolated corpus
fixture plus a gate JSON-robustness gap — neither a Rust production defect.

Root cause: the tamper_top_level_report fixture (from the frozen generator)
appended one byte to companion_report.json but did NOT repair the declared hash,
so Rust rejected at the SHARED declared-hash stage (DECLARED_HASH_MISMATCH)
instead of reaching the intended canonical-report stage. The harness reported
this honestly as an error envelope (reason CAPABILITY_GAP_CASE_NOT_ISOLATED, no
summary), and the gate then assumed every response had a top-level summary and
raised KeyError('summary').

1. STAGE-TARGETED FIXTURE, ISOLATED (v27). corpus/build_bundle_cases.py gains a
   stage-targeted builder for tamper_top_level_report: it appends the one
   noncanonical byte to companion_report.json AND repairs every declared hash to
   a fixpoint, then registers under BUILDERS["tamper_top_level_report"]. Because
   build_bundle_cases.build runs after the frozen generator, it replaces the
   legacy directory in place without editing the frozen generator. The rebuilt
   companion_report.json is noncanonical yet valid JSON and its declared hash
   matches its actual bytes (SHA256 521a78a0...), so the shared declared-hash
   stage passes and the case reaches its intended stage: Python rejects at
   report-canonicality (REPORT_NOT_CANONICAL / canonical_report, FAIL/1) and Rust
   reaches its documented out-of-scope INCONCLUSIVE completion (OK / complete,
   exit 3). bundle_cases.json provenance is updated to state the repair honestly;
   the corpus-lock file pins for the two edited corpus files are refreshed. The
   85-case count, IDs, category counts, and the two divergence IDs are unchanged.

2. ERROR-ENVELOPE-SAFE GATE (v27). tools/gate_flow.sh no longer assumes a
   summary. Before extracting summary fields it classifies the measurement
   response: a complete summary is parsed as before; an error envelope
   (overall_status/reason_code/detail with no complete summary) or malformed
   JSON or an incomplete summary is failed CLOSED with
   MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (measurement) and exit 1, preserving
   the reason_code/detail and emitting no traceback, no KeyError, and no
   misleading "expected 85, got ?" cascade. The per-measurement semantic hash is
   likewise hardened against malformed JSON.

Tests: a direct fixture-isolation self-test proves the rebuilt report is
noncanonical, still valid JSON, and carries a matching declared hash (so the
shared stage passes); three controlled full-gate tests prove an error envelope,
malformed JSON, and an incomplete summary each fail closed with the measurement
marker and no traceback/KeyError/count-cascade, while the clean summary still
reaches instrument PASS / system FAIL. The Python-FAIL/Rust-INCONCLUSIVE
behavioural outcomes for the case are asserted against bundle_cases.json by the
full corpus run on Termux.

All prior repairs are retained: early pure-shell missing-preload classification;
the shared no-Cargo fixture and absence of /system/bin and /product/bin
enumeration; genuine Termux preload capture/validation/restoration;
TERMUX_NESTED_EXEC_CHECK; BusyBox and GNU timeout parsing; the production timeout
probe; applet entrypoint/canonical-target separation; canonical named-gate
resolution; the literal Termux prefix; real Move 78 provenance; post-preflight
hygiene; exact workspace marker/exit; the clean Rust build; measurement stderr
rejection; signal termination and cleanup; the 85-case corpus with its two
divergences; and instrument PASS separated from system-agreement FAIL.

### What remains for the Termux gate (not claimed here)

Two properties require a real toolchain and the real adopted artifact and were
NOT executed in this build environment:
- one clean `cargo build` producing the real `witness-verify`, and the three
  real order-specific agreement measurements against it;
- the gate's provenance derivation run against the genuine
  `project-witness-MOVE_78_candidate_v10.zip` (SHA
  `6030148c…c3a45252`), supplied as `REAL_MOVE78`.
The gate's DECISION LOGIC for both was proven locally with a stub compiler and
controlled baselines. The end-to-end PASS/FAIL/INCONCLUSIVE run belongs to
Termux.


## Superseded candidate history (v1–v26) — REJECTED, not current truth

These candidates were rejected before adoption and are retained only as audit
history. None is an adopted release. Their detailed per-version repair
narratives are intentionally NOT reproduced here as current state.

- v1: false agreement — verdicts ignored, scope not enforced, exits ignored.
- v2: normalized outcome decorative; divergence hidden as out-of-scope.
- v3: expected divergence still allowed global PASS; corpus incomplete.
- v4: gate could not separate instrument correctness from disagreement;
  bytecode shipped.
- v5: checker regenerated bytecode; Move 78 history altered; no separate
  instrument-adoption gate.
- v6: checker still wrote bytecode; exits ignored; unsafe shell arg
  construction.
- v7: unclosed corpus-lock/adopted-pin reads (ResourceWarning); overstated
  timing.
- v8: warning-clean claim was false (leaked handles in check_corpus_lock and
  the pin check); no source-bound provenance.
- v9: gate accepted any RUST_BIN on trust (no provenance); then over-corrected
  to demand byte-identical binaries, which is unsatisfiable for honest builds.
- v10: introduced the source pin but self-certified it; pin covered
  rust/README.md, which the workspace checker REQUIRES to change every move —
  a rule mandating what another rule forbade.
- v11: pin recorded baseline hashes but the gate never verified them against
  the real adopted artifact (falsifiable to zeros); no-cargo test inherited
  PATH; any exit 0 accepted as PASS; leaked archive handle; RUST_BIN still in
  the gate; GATE_SELFTEST bypass; gate-execution tests replaced by
  pin-structure tests.
- v12: CARGO was a live production builder override (fake compiler could
  manufacture the binary and reach PASS); warning text was masked as
  INCONCLUSIVE; baseline behaviour scope was not enumerated (unpinned baseline
  file passed); recorded pin metadata (artifact/sha/count) was not verified;
  the named gate ran only self_tests.py; REAL_705 was not validated up front.
- v13: the production builder resolved cargo from caller PATH
  (command -v cargo), so a fake cargo first on PATH still built the binary and
  reached PASS; measurement stderr was captured but never checked, so a
  ResourceWarning or a post-report traceback (with exit 1) was accepted as
  expected disagreement; the integration suite had no complete successful-gate
  path to catch either.
- v14: the trust anchor remained caller-controlled — preflights and
  provenance ran before any trusted-command bootstrap, and the toolchain
  resolver began from the inherited PREFIX. A fully-fake environment (fake
  python3/sh/cargo/rustc + a caller-created PREFIX + dummy non-ZIP archives)
  fabricated every stage and the named gate returned PASS/exit 0. FLOW_H
  remained a live production harness override; repeated toolchain resolution
  leaked the first temporary CARGO_HOME; and the required post-preflight
  package-hygiene check was absent.
- v15: the trusted bootstrap was real but incomplete — `dirname` (ROOT) and
  `tr` (resolver) ran from the inherited PATH before trust existed, so a fake
  `dirname` redirected ROOT to a fabricated tree and the named gate returned
  PASS/exit 0; the HUP/INT/TERM traps cleaned but did not terminate, so an
  interruption continued into the next measurement; and the provenance,
  workspace, and measurement stdout/stderr temps were not tracked for cleanup.
- v16: ROOT was derived from the textual directory portion of $0. A symlink
  alias to the genuine gate in an attacker tree (cd -P resolves directory
  symlinks but not the $0 script file) left ROOT pointing at that tree, so the
  gate sourced fake adjacent bootstrap/lib/flow modules and returned PASS/exit
  0. The fake-dirname test did not cover a real $0 symlink.
- v17: reached the real Termux gate and failed safely (exit 1, no PASS). Its
  bootstrap invoked the canonical multicall targets directly (readlink -f
  resolved the applet entrypoints to .../bin/coreutils and the gate stored and
  ran that), losing the Termux coreutils applet identity so that `mktemp -d`
  became `coreutils -d`. An invocation-model incompatibility with the genuine
  Termux environment, not an untrusted-environment attack.
- v18: got past bootstrap on real Termux, then failed in preflight because
  gate_sanitize_env removed the legitimate Termux libtermux-exec.so preload
  from child environments, so nested trusted subprocesses failed with
  PermissionError/EACCES. The ADOPTED HISTORY MUTATED report was a false
  failure from a denied nested Python, not an actual permission or
  adopted-history mutation.
- v19: added a correct preload validator but the named gate still unset
  LD_PRELOAD at the top (v17 sanitisation) BEFORE capturing it, so the
  validator always received an empty value, accepted it, and restored nothing.
  The production path therefore did not preserve the Termux exec preload; the
  changelog claim that it did was false for the named gate's control flow.
- v20: the production preload repair PASSED on real Termux (bootstrap + nested
  exec). Rejected only because two TEST FIXTURES were not Android/Termux
  portable: the no-cargo helper enumerated the non-listable /system/bin, and the
  multicall fixture was a shell dispatcher that lost libtermux-exec before its
  nested exec. Neither was a production-gate failure.
- v21: cleared bootstrap, the nested-exec probe, and all 62 harness tests on
  real Termux, failing only one gate-unit assertion whose final step required a
  COPIED timeout applet to nested-exec a COPIED readlink applet in an artificial
  temp prefix under the no-preload sanitised environment. That is a stronger
  claim than production makes and Android need not permit it; the production
  trusted nested-exec probe itself passed.
- v22: passed bootstrap, the probe, all 62 harness tests, and the new real
  production-timeout test, failing only one gate-unit assertion: the timeout
  identity check inspected only the first line of `timeout --help`, so BusyBox's
  multi-call banner (which names the applet only on a later Usage line) was
  wrongly rejected even though the fixture deliberately accepts BusyBox.
- v23: cleared bootstrap, the probe, all 62 harness tests, and adopted
  immutability on real Termux, failing two gate-unit tests on host assumptions:
  one inferred the literal Termux prefix was absent (true on desktop, false on
  Termux, giving the wrong expected code), and a DUPLICATE no-Cargo fixture in
  gate_unit_tests.py still enumerated inherited PATH and crashed on the
  non-listable /product/bin. Neither was a production defect.
- v24: passed bootstrap, the probe, all 62 harness tests, adopted immutability,
  source matching, current-release-state, and both hygiene checks on real
  Termux, failing one gate-unit test that required the incidental helper stdout
  marker TERMUX_EXEC_PRELOAD_CHECK: FAIL even though the production missing-
  preload decision correctly returned FAIL/1 with the precise stderr reason.
- v25: passed the genuine-preload production path on real Termux (bootstrap +
  nested exec + all preflights) but failed one gate-unit test because
  missing-preload classification occurred AFTER an external trusted-readlink
  invocation; on real Termux that readlink required the very preload being
  tested as missing, causing "Permission denied" before GATE_PRELOAD_FAIL could
  be set. A bootstrap-ordering defect, not a production-bootstrap failure.
- v26: ran the entire production pipeline on real Termux (bootstrap, fresh Cargo
  build, three identical canonical measurements) but failed on one un-isolated
  corpus fixture: tamper_top_level_report appended a byte without repairing the
  declared hash, so Rust died at the shared DECLARED_HASH_MISMATCH stage; the
  resulting error envelope then hit a gate that assumed a summary and raised
  KeyError. A corpus-fixture + gate-robustness issue, not a Rust defect.

Base: adopted Move 78 v10
(sha256 6030148c2c1bb373ad69393563e8e2e3078dff93e9f446d728edd18ea3c45252).
Boundaries held: adopted runtime Python unchanged; corpus cases, expectations,
and the known-divergence set unchanged; Move 78 ZipGuard verdict logic and
precedence unchanged; adopted Move 78 history unchanged. Move 80 not started.
