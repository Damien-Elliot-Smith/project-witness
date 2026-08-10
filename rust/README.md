# Witness Rust Workspace (Part Two, Steps 72-85)

Purpose: an INDEPENDENT, read-only verification layer for completed
Witness case bundles. Rust verifies first; it replaces nothing.

Boundaries (from the Part Two roadmap and Move 71 freeze):

- read-only: no action surface, no autonomy, no hidden decision logic
- zero external crates: stdlib only, like the Python stack
- the behavioural reference is freeze_record/python_behaviour_freeze_v01/
  (adopted Move 71): reference bundle, ten recorded verdicts, 302 reason
  codes, nondeterminism registry
- agreement criteria are the FROZEN properties only: internal hash
  consistency of a bundle, verdict + reason per corpus case, reason-code
  vocabulary. Byte-equality across runs is NOT a criterion (see the
  nondeterminism registry for why)
- any Python/Rust mismatch is a failure until explained
- kept outside src/: the Roadmap One build and its source-match checker
  are untouched by this workspace

Build and test (requires a Rust toolchain; Termux: pkg install rust):

    cd rust
    cargo build
    cargo test

Step 79 status: manifest structure (Move 74), top-level hashes
(Move 75), receipt chain structure (Move 76), canonical JSON +
receipt hash recomputation (Move 77), plus a ZipGuard archive-safety
checker (Move 78, adopted). New command: witness-verify
inspect-archive <archive.zip> - read-only, parses the ZIP central
directory AND every referenced local file header and requires them to
agree; never extracts/executes/writes. Clean archive ->
INCONCLUSIVE / ARCHIVE_SAFETY_OK; unsafe -> FAIL with a precise code.
Move 79 adds one read-only diagnostic field (entry_count) to accepted
archive output so the agreement harness never parses counts from free
text. It adds no check and changes no verdict, reason code, precedence
or ordering.

Reason-code taxonomy: OFFSET_INVALID = an offset that is itself invalid;
LOCAL_LAYOUT_INVALID = valid ranges that overlap; UNREFERENCED_DATA =
body bytes no entry accounts for; UNSUPPORTED_FEATURE = a ZIP feature we
do not interpret, including unknown extra tags in either header;
LOCAL_HEADER_MISMATCH = supported fields whose values disagree between
central and local; LOCAL_HEADER_MALFORMED = structurally broken local
header/extras. Path-name precedence: most specific wins (UNC before
absolute; '.'/'..' components before Windows-hostile names).
Fails closed on zip64, encryption, unsupported compression, multi-disk
metadata, Unicode Path extra fields, and ALL non-ASCII filenames
(Unicode normalization and case folding are not implemented, so
collision safety cannot be proven for them). Manifest/seal recomputation, nested checksums
and manifest bindings remain unimplemented; verdict stays INCONCLUSIVE.
Usage: witness-verify verify <bundle-dir>
Output: one JSON object per run with verifier, version, verdict,
reason_code, detail. Verdicts FAIL / INCONCLUSIVE only - no code path
can emit PASS; nested component checksums, manifest bindings and
receipt chains ARE implemented (Moves 76-77). Exit codes: 1 FAIL, 2 usage
error, 3 INCONCLUSIVE; 0 is reserved for a real PASS and is
unreachable at this stage.
NOTE: this status section is checked mechanically against the crate
VERSION by tools/check_rust_workspace.sh; update both together.

Termux note (from the Move 72 adoption run): build and run from Termux
internal storage (e.g. ~/), not Android shared storage under
/storage/emulated/0/ - Android blocks executing binaries from shared
storage, which fails cargo test with a permission error that is an
environment issue, not a code failure.

