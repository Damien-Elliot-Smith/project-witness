# Changelog - Move 74 (CANDIDATE)

Move: 74
Name: Rust case manifest validator
Date: 2026-07-10
Status: CANDIDATE. ADOPTION BLOCKED until a real cargo build + cargo test
PASS transcript exists (sh tools/check_rust_workspace.sh PASS, exit 0, on
Cargo/Termux internal storage). The builder sandbox has no Rust
toolchain: this Rust has NOT been compiled. If cargo fails, paste the
error text back; the fix joins this move's record.
Base: adopted Move 73
(zip sha256 b6be02801ce2b512cacc47c401b2adcd55bc6c936a82f5ffcd8890daded428ae).

## Added

- rust/witness-verify/src/json.rs: minimal strict JSON parser, zero
  external crates. Deterministic strictness: duplicate object keys
  rejected, trailing content rejected, standard escapes only (including
  surrogate pairs), unescaped control characters rejected. Prefigures
  the Step 77 canonical JSON tool. Own unit tests.
- rust/witness-verify/src/manifest.rs: manifest-layer validator
  mirroring the STRUCTURAL layer of the Python verifier against the
  adopted Move 71 reference: required top files; unknown top-level
  entries forbidden; companion_report.json parses as an object; schema
  versions pinned to 0.3.0; all seventeen reference report fields
  required, unknown fields critical; coordinator_output_path and every
  path listed in companion_checksums.txt must exist (existence ONLY -
  hashing is Step 75); unsafe paths rejected. Deterministic reason
  codes: MANIFEST_MISSING, REQUIRED_FILE_MISSING, BUNDLE_READ_ERROR,
  CRITICAL_UNKNOWN_TOP_LEVEL_ENTRY, MANIFEST_READ_ERROR,
  MANIFEST_JSON_INVALID, MANIFEST_NOT_AN_OBJECT,
  SCHEMA_VERSION_UNSUPPORTED, REQUIRED_FIELD_MISSING,
  CRITICAL_UNKNOWN_FIELD, REFERENCED_PATH_UNSAFE,
  REFERENCED_PATH_MISSING, MALFORMED_CHECKSUMS_LINE,
  CHECKSUMS_PATH_UNSAFE, REFERENCED_FILE_MISSING.
- 17 Rust unit tests total, covering every reviewer-required case:
  missing manifest, malformed JSON, unsupported schema, missing required
  field, critical unknown field, structurally valid manifest
  (INCONCLUSIVE), plus unknown top-level entry, missing referenced file,
  unsafe checksums path, JSON parser cases, and the PASS-unreachable
  property test.

## Grounding check and a caught correlated error (worth reading)

Before packaging, the exact Move 74 contract was executed in Python
against the frozen Move 71 reference bundle. It FAILED: the hand-
transcribed REPORT_FIELDS list had 16 of 17 fields (workflow_type
omitted) - and the Rust unit-test fixture omitted the SAME field, so
the Rust tests would have passed while the validator rejected every
genuine bundle. Same wrong list in code and tests: a live correlated-
error specimen of the class the Move 71 freeze record warns about.
Fixed in both places; the grounding check now passes (17 fields, exact
match); the incident is noted in a manifest.rs comment. Lesson encoded:
Rust contract constants must be validated against the frozen reference
by executable check, not by eye.

## Changed

- tools/check_rust_workspace.sh: stale "(Move 72)" banner fixed
  (external-review finding); contract rules updated to Move 74
  (INCONCLUSIVE-on-valid-structure, parser and validator modules
  present, unknown-field and schema-pinning rules).
- State model updated proactively: Move 73 recorded adopted; Move 74
  candidate; Steps 75-130 not started; markers rolled in all 18 docs;
  authoritative checker strings updated.

## Not changed / not claimed

Python src/ untouched. Move 71 freeze records untouched. NO file hash
verification (Step 75), NO receipt chains (Step 76), NO ZipGuard
(Step 78), NO full bundle verification claim. A structurally valid
manifest yields INCONCLUSIVE / MANIFEST_STRUCTURE_OK - never PASS.

## Move 74 candidate v2 addendum (2026-07-10)

External review of Move 74 candidate v1 found a stale checker:
tools/check_five_minute_demo_script.sh still required the demo script to
say "Part Two has not started" - enforcing a false old state after the
Move 72/73 adoptions (the same false-green checker class repaired in the
Move 72 rebuild). Repairs in v2:

- tools/check_five_minute_demo_script.sh now enforces the current honest
  state (Part Two started; Move 74 candidate only; no full-verification,
  production-ready, or external-truth claims) and forbids the stale
  claim; negative-tested.
- FIVE_MINUTE_DEMO_SCRIPT.md closing now carries the not-production-ready
  and does-not-prove-real-world-truth limits explicitly.
- rust/witness-verify/src/manifest.rs module header: stale "sixteen"
  corrected to seventeen (the constant and its comment were fixed in v1;
  the module docstring was missed).
- Builder process fix recorded: the v1 gauntlet ran a hand-picked
  six-checker list; every gauntlet from v2 onward runs the ENTIRE
  tools/check_*.sh family by glob, so a stale checker can never again
  sit unexecuted through a candidate build.

## Move 74 candidate v3 addendum (2026-07-10)

The v2 Termux cargo gate FAILED: error E0308, REPORT_FIELDS declared
[&str; 17] with 19 entries. Root cause, established by computation, not
narration: the frozen reference report has NINETEEN fields. The v1
array listed 18 entries under a declared length of 16 (authoring
miscount); the grounding check caught the missing workflow_type by SET
comparison (computed, real) but the "16 fields"/"17 fields" counts in
the changelog and comments were narrated, never computed; the v2 fix
added the field and incremented the imagined count 16 to 17; external
review echoed 17. rustc's fixed-length array type-check was the first
mechanical counter in the chain and failed the build correctly.

Repairs in v3:

- REPORT_FIELDS declared [&str; 19]; the 19 entries and the test
  fixture were already an exact set match with the reference and are
  unchanged.
- Every count narration corrected (manifest.rs docstring and constant
  comment, CURRENT_RELEASE_STATE.md); the manifest.rs NOTE now records
  the full count history as a warning against narrated numbers.
- Mechanical guard added to tools/check_rust_workspace.sh: a computed
  four-way alignment check (frozen reference keys, Rust array entries,
  declared array length, unit-test fixture keys - all must agree
  exactly). Runs in the structural section, so it gates packaging even
  on machines without cargo. Negative-tested in both directions
  (wrong declared length; missing array entry).
- The changelog claims above in the v1/v2 sections that say "seventeen"
  are preserved as history; this addendum is the correction of record.

Encoded lesson: counts are computed, never narrated. The alignment
guard makes this specific mismatch structurally impossible to package
again.
