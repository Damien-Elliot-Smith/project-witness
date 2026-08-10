# Changelog - Move 78 (CANDIDATE)

## AUTHORITATIVE CURRENT STATE (v10) — read this first

Everything below the superseded-history boundary describes EARLIER
candidates and is NOT current truth. Several earlier sections contain a
FALSE claim that the real project archives have zero extra fields; that
claim is corrected here and retained below only as history.

GROUNDING (re-done from actual bytes in v6): both real archives DO carry
extra fields on every entry. v20 release: 970 entries; Move 70.5 repo:
819 entries. Each entry has central 0x5455 Extended Timestamp (len 5,
flags 0x03, mtime only) and 0x7875 Unix UID/GID (len 11, version 1,
4-byte uid/gid); each local header has 0x5455 (len 9, mtime + atime) and
0x7875 (len 11). Creator host is 3 (Unix) throughout. The central and
local Extended Timestamp forms legitimately DIFFER in length, so raw
byte/length equality must NOT be required.

CURRENT CONTRACT:
- ZipGuard parses the central directory AND every referenced local header,
  requiring agreement on filename, raw flags, method, version-needed,
  CRC-32 and both sizes, and agreement on the VALUES shared by the two
  extra-field forms (mtime, uid, gid) rather than raw bytes.
- Extra fields: strict ALLOWLIST. 0x5455 and 0x7875 are strictly parsed
  and validated. 0x7075 Unicode Path, 0x0001 ZIP64, unknown tags,
  duplicate tags and malformed records all fail closed.
- Archive body layout: the validated local-entry ranges must tile
  [0, central_directory_offset) exactly. Prefix/SFX bytes, interior gaps,
  overlaps, orphan local headers and trailing unreferenced bytes fail
  closed (ARCHIVE_UNREFERENCED_DATA / ARCHIVE_LOCAL_LAYOUT_INVALID).
- Creator host: only system 3 (Unix) is supported; anything else fails
  closed. Unix file type must be regular or directory (zero/ambiguous
  type rejected); directory entries must carry no data.
- All non-ASCII filenames fail closed; Windows-hostile names fail closed;
  traversal/absolute/UNC/drive/backslash, duplicates, symlinks, special
  file types, parent-prefix and case collisions all fail closed.
- Clean archive -> INCONCLUSIVE / ARCHIVE_SAFETY_OK, exit 3. PASS
  unreachable. Archive safety does NOT prove archive-content validity.

PROVEN: the v6 logic accepts the real v20 (970), Move 70.5 (819) and the
Move 78 candidate (935) archives — verified by an executable mirror of the
full decision logic run against the actual bytes.

Computed current counts (mechanically checked):
<!-- RUST_TEST_COUNT: 123 -->
<!-- ARCHIVE_REASON_CODE_COUNT: 25 -->
Rust tests: 123. Archive reason codes: 25.

## Move 78 candidate v6 addendum

Fourth hostile-review round found a FOUNDATIONAL grounding error: v5
claimed "both real archives have zero extra fields" and built a
reject-all extra-field policy on it. The claim was never computed — my
grounding script checked names, symlinks, duplicates and encodings but
never parsed extra fields. The v5 policy would have rejected all 1,789
real entries. Repairs:

1. EXTRA FIELDS: re-grounded from actual bytes; strict allowlist parser
   for 0x5455 (central mtime-only / local mtime+atime forms) and 0x7875
   (version 1, length-prefixed uid/gid). Shared VALUES compared, not raw
   bytes. All other tags, duplicates and malformed records fail closed.
2. UNREFERENCED DATA: local-entry ranges must now tile the archive body
   exactly from byte 0 to the central directory. Orphan local headers,
   SFX stubs, gaps and trailing junk fail closed.
3. CREATOR HOST: version-made-by is parsed; only host 3 (Unix) supported;
   zero/ambiguous Unix file types rejected; directories must carry no data.
4. TRUTH-STATE: this authoritative v6 header replaces the stale v4 one;
   the false zero-extra-fields claim is corrected and checker-forbidden.

Counts: tests 115, archive codes 25.


## Move 78 candidate v7 addendum

Fifth hostile-review round found a GUARANTEED COMPILE ERROR: the v6
builder rewrite added a new entry_local_extra method while the stale v5
copy remained in the same impl Zw block — a duplicate inherent method,
which rustc rejects before any test runs. My v6 self-checks could not see
it: every guard verified that things were PRESENT, none verified they were
present exactly ONCE.

Repairs (no production ZipGuard behaviour changed by the duplicate fix):
1. Stale duplicate entry_local_extra removed (the one that wrongly gave
   the central header no extras, contradicting the v6 grounded model).
   Full-tree duplicate sweep run: the only same-impl duplicate was this
   one (fail/find_eocd appear in different modules, which is legal).
2. New guards: exactly one entry_local_extra in the Zw impl, and no
   duplicate method definitions anywhere in main.rs.
3. Stale module doc corrected: extra fields are an ALLOWLIST (0x5455,
   0x7875 strictly parsed), not reject-all. Stale wording checker-forbidden.
4. Central/local Extended Timestamp FLAGS are now compared, not just
   mtime — verified against real bytes first: all 970 + 819 real entries
   have matching central/local UT flags (0x03), so they remain accepted.
   Negative test added: same mtime, different flags -> MISMATCH.

Counts: tests 116, archive codes 25.


## Move 78 candidate v8 addendum

The v7 Termux gate: cargo BUILD passed and both real-archive bonus checks
passed (v7 candidate 935 entries and canonical v20 970 entries, both
INCONCLUSIVE / ARCHIVE_SAFETY_OK, exit 3) — the v6 grounding correction is
confirmed on real hardware. But cargo TEST failed to compile: inside
impl Zw, real_central_extra/real_local_extra called ut_central, ut_local
and ux without the Self:: qualifier, which Rust rejects.

Repairs (production ZipGuard behaviour unchanged except the dead-field
removal):
1. The two call sites now use Self::ut_central / Self::ut_local / Self::ux.
   Full-impl sweep confirms no other unqualified associated-fn calls.
2. New guard proves it mechanically: it parses the impl Zw block and fails
   on any unqualified associated-fn call. Negative-tested - reintroducing
   the exact v7 bug makes the checker FAIL.
3. tools/check_rust_workspace.sh now prints real compiler output on a
   cargo test failure (errors, warnings, panics, test result lines) instead
   of only "FAIL cargo test".
4. The grep "stray \ before n" warning is fixed (a double-escaping bug in
   the duplicate-method guard's grep pattern).
5. Dead Entry fields name_len and extra_len removed (stored, never read).

Counts: tests 116, archive codes 25.


## Move 78 candidate v9 addendum

The v8 Termux gate: cargo build PASS, 116 tests ran, 112 passed, 4 failed.
Every failure was a reason-code precedence/taxonomy issue — all four
archives were still correctly REJECTED, only the code reported was wrong.

TWO GENUINE PRECEDENCE BUGS (production fixed):
1. "a/./b" reported ARCHIVE_WINDOWS_NAME_UNSAFE because the Windows
   trailing-dot rule fired before the "." component check. Now "." and
   ".." components are detected BEFORE the Windows name rules, so
   "a/./b" -> PATH_TRAVERSAL while "file." -> WINDOWS_NAME_UNSAFE.
2. "//server/share" reported ARCHIVE_ABSOLUTE_PATH because the generic
   absolute rule fired first (a UNC path also starts with '/'). UNC is now
   checked BEFORE generic absolute.

TWO STALE TESTS (taxonomy settled, tests updated — production behaviour
was already sound):
3. Overlapping valid ranges: OFFSET_INVALID is reserved for an offset that
   is ITSELF invalid (out of range, duplicated). Two individually valid
   ranges that conflict are a LAYOUT problem -> ARCHIVE_LOCAL_LAYOUT_INVALID.
4. Unknown local extra tag: an unknown tag is an UNSUPPORTED FEATURE, not
   a central/local mismatch. MISMATCH is reserved for SUPPORTED fields
   whose parsed values disagree.

The taxonomy is now documented in the zipguard module docstring and in
rust/README.md, and checker-enforced.

GREP WARNING: my v8 claim that this was fixed was FALSE — I never checked
stderr in isolation. The real cause was a dead no-op line
(grep -q 'read-only ZIP
 ...' ... then :; fi) containing a literal 
 in a
basic-regex grep. Removed. Verified by running the checker with stderr
isolated: zero stderr lines.

Seven neighbouring-distinction tests added ('.', trailing dot, UNC,
absolute, out-of-range offset, supported-value disagreement, malformed
local extra).

Counts: tests 123, archive codes 25.


## Move 78 candidate v10 addendum

The v9 Termux gate: cargo build PASS, 123 tests, 122 passed, 1 failed
(inspection_creates_no_files). An immediate --test-threads=1 rerun passed
123/123, which is the signature of a test race, not a ZipGuard defect.

ROOT CAUSE (my test, not production): inspection_creates_no_files created
its fixture directly in std::env::temp_dir() and then counted every entry
in that SHARED root before and after inspection. Other tests create and
delete their own fixtures there in parallel, so the count changed
underneath it.

REPAIR (production ZipGuard behaviour unchanged):
- The test now creates a DEDICATED directory (process id + AtomicUsize
  sequence, zero crates), writes its fixture inside it, and snapshots only
  that directory.
- It now proves more than before: no new entry appears in the dedicated
  directory; no archive member (a.txt) is extracted; and the archive bytes
  are byte-identical after inspection.
- The directory is removed after the assertions.
- New guard: no test may read_dir() a .parent() or env::temp_dir()
  directly, and the racy p.parent() idiom is forbidden. Negative-tested.

PACKAGING DEFECT FOUND AND FIXED: while repairing this, I discovered the
v9 PACKAGE shipped without the v9 taxonomy checker rules - I edited the
checker in my working copy but the packaged zip did not contain those
edits. The rules (dot-vs-windows precedence, UNC-vs-absolute precedence,
taxonomy documented in code and README) are now present and verified in
the packaged tree.

Counts: tests 123, archive codes 25.

--- superseded history ---" marker is retained for
provenance but describes EARLIER candidates and is NOT current truth. The
current Move 78 v4 contract is:

- ZipGuard parses the ZIP central directory AND every referenced local
  file header, requires them to agree (filename, raw flags, method,
  version-needed, CRC-32, compressed and uncompressed sizes), and
  validates archive structure. It never extracts, executes, or writes.
- Fails closed on: traversal, absolute/UNC/Windows-drive paths,
  backslash separators, duplicates, symlinks, file/dir and parent-prefix
  collisions (case-folded), control/bidi characters, ALL non-ASCII names
  (no Unicode normalization/case-fold implemented), Windows reserved
  names / trailing dot-space / ADS, zip64, encryption, unsupported
  compression, multi-disk, data-descriptor flag, any unsupported
  general-purpose flag bit, overlapping/embedded local entry ranges, and
  malformed structure.
- Clean archive -> INCONCLUSIVE / ARCHIVE_SAFETY_OK, exit 3. PASS
  unreachable. Archive safety does NOT prove archive-content validity.

Computed current counts (mechanically checked):
Rust tests: 103. Archive reason codes: 23.

--- superseded history (earlier candidates; NOT current truth) ---


Move: 78
Name: Rust ZipGuard / archive-safety checker
Date: 2026-07-11
Status: CANDIDATE. ADOPTION BLOCKED until a real cargo build + cargo test
PASS transcript exists (sh tools/check_rust_workspace.sh PASS, exit 0, on
Cargo/Termux internal storage). This Rust has NOT been compiled.
Base: adopted Move 77 v3
(zip sha256 7a5fbeaf9e4bcd4c59adc6e297fadc5d9bd58d183f42ab48464e0eafa20b28a8).

## Grounding (before any Rust)

ZipGuard is the stack's FIRST automated archive-safety check: the Python
runtime only touches zipfile in one synthetic test helper, and extraction
safety today is manual quickstart guidance. So the contract comes from the
roadmap definition plus the real archives, not a Python layer. Both real
project zips were computationally characterised (v20 release: 970 entries;
70.5 repo: 819) and are CLEAN on every axis: no symlinks, duplicates,
traversal, absolute/UNC/drive paths, non-ASCII names, control/RTL chars,
case or NFC collisions, no zip64, no UTF-8 flag. ZipGuard must accept both
and reject synthetic malicious archives.

## Decision: NO new dependency

Stdlib-only is honest here. ZipGuard parses ONLY the ZIP central directory
(EOCD + central headers) - no decompression, extraction, execution, or
writes. It reads names, flags, method, and external attributes.

## Fail-closed boundaries (never a safe verdict on an unchecked property)

- zip64 structures, encryption, unsupported compression, multi-disk, and
  version-needed > 45 -> ARCHIVE_UNSUPPORTED_FEATURE
- non-ASCII name WITHOUT the UTF-8 flag -> ARCHIVE_UNICODE_NAME_UNSAFE
  (intended encoding is ambiguous, so normalization/case safety cannot be
  checked honestly)
- names with combining marks -> ARCHIVE_UNICODE_NAME_UNSAFE (full NFC/NFD
  normalization is not implemented in stdlib; rather than fake a
  collision check, such names fail closed)

## Added

- rust/witness-verify/src/zipguard.rs: central-directory parser + name
  safety analyzer.
- witness-verify inspect-archive <archive.zip>: new command. The existing
  verify <bundle-dir> command and all Move 77 behaviour are preserved.
- Clean archive -> INCONCLUSIVE / ARCHIVE_SAFETY_OK, exit 3 (this proves
  nothing about bundle CONTENTS). Unsafe -> FAIL, exit 1, precise code.
  PASS unreachable.
- 17 archive reason codes (computed): ABSOLUTE_PATH, BACKSLASH_PATH,
  BIDI_CHARACTER, CASE_COLLISION, CONTROL_CHARACTER, DUPLICATE_NAME,
  FILE_DIRECTORY_COLLISION, IO_ERROR, MALFORMED, NORMALIZED_NAME_COLLISION,
  PATH_TRAVERSAL, SAFETY_OK, SYMLINK_ENTRY, UNC_PATH, UNICODE_NAME_UNSAFE,
  UNSUPPORTED_FEATURE, WINDOWS_DRIVE_PATH.
- 21 zipguard unit tests with an in-memory store-only ZIP builder whose
  byte layout was validated in Python against the parser during grounding.
  Covers all 20 required fixtures including no-extraction proof (temp-dir
  entry count unchanged across inspection).

## Counts (computed mechanically, never narrated)

Rust test count: 60. Archive reason-code count: 17.

## Changed

- tools/check_rust_workspace.sh: banner rolled to Move 78; alignment
  guard extended with computed test-count and archive-code markers;
  structural rules (zipguard module, inspect-archive command, verify
  preserved, no-extraction stated, ARCHIVE_SAFETY_OK stays INCONCLUSIVE).
- State model + coupled checkers rolled to Move 78 candidate.

## Not changed / not claimed

Python src/ untouched. Move 71 freeze records untouched. NO extraction,
NO signing, NO Move 79 agreement harness, NO Move 80 pack, NO
manifest/seal recomputation beyond Move 77, NO archive-content validity
claim, PASS unreachable.

## Move 78 candidate v2 addendum (2026-07-11)

Hostile review found a ZipGuard false-negative class before the Cargo
gate. Repaired:

PRIMARY - central-directory-only parsing. The inspector trusted central
names and never read local file headers, so an archive with central
name "safe.txt" and local name "../x.txt" (equal length) returned
ARCHIVE_SAFETY_OK. Now each local header is parsed at its central offset
and compared: filename bytes, flags, method, version-needed. New codes
ARCHIVE_LOCAL_HEADER_MISMATCH, ARCHIVE_LOCAL_HEADER_MALFORMED,
ARCHIVE_LOCAL_HEADER_OFFSET_INVALID. Offsets are bounds-checked and
de-duplicated.

EXTRA-FIELD - the parser noticed only zip64 tag 0x0001 and ignored the
rest. Now every extra-field record is boundary-validated, and a Unicode
Path extra field (tag 0x7075, which can carry an alternate filename) is
not merged but fails closed as ARCHIVE_UNSUPPORTED_FEATURE.

PATH NORMALIZATION - collision keying now runs validate_path_components,
rejecting "." components, empty interior components (repeated
separators), empty filenames, and repeated trailing slashes, with
consistent directory-suffix handling. Non-ASCII names still fail closed
before any case fold, so ASCII lowercase is a complete fold for
everything that reaches keying.

ZIP STRUCTURE - EOCD disk numbers must be zero; EOCD comment length must
reach exactly end-of-file; central directory must not overlap the EOCD;
extra-field records must stay within their declared bounds.

STALE TRUTH TEXT - main.rs module docstring (was "Step 74") and
rust/README.md ("receipt chains are not implemented") corrected to the
Move 78 state; both are now FORBIDDEN by tools/check_rust_workspace.sh.

Counts recomputed: tests 60 -> 68, archive codes 17 -> 20. Rust source
grew (this is a real fix, not a v1 repackage), so the tree hash changes
by design.


## Move 78 candidate v3 addendum (2026-07-11)

Hostile code review of v2 found TWO Rust tests that would have failed on
the Cargo gate, plus remaining parser gaps. All repaired.

BLOCKER 1 - non-ASCII: my own test expected ARCHIVE_UNICODE_NAME_UNSAFE
for "E.txt" (precomposed U+00C9) but the code only rejected combining
marks, so it ACCEPTED the precomposed form and then case-compared with
ASCII-only lowercase - which does not fold U+00C9 to U+00E9. The test was
right; the implementation was unsound. v3 fails closed on EVERY non-ASCII
filename while Unicode normalization and case folding are unimplemented.
Four tests: precomposed upper, precomposed lower, decomposed (NFD),
Greek + Cyrillic. The combining-mark heuristic is deleted and its absence
is checker-enforced.

BLOCKER 2 - collision order: collision_key strips the directory suffix,
so "x" and "x/" shared a key and ARCHIVE_CASE_COLLISION fired before the
file/dir check. v3 runs exact file-vs-directory detection BEFORE the
general case/normalized check; the test now gets
ARCHIVE_FILE_DIRECTORY_COLLISION as intended.

LOCAL-HEADER GAPS: version-needed is now compared exactly between local
and central. Local extra fields are parsed (they were not): malformed
local extra length -> ARCHIVE_LOCAL_HEADER_MALFORMED; local Unicode Path
extra -> ARCHIVE_UNSUPPORTED_FEATURE; central/local disagreement on
filename-affecting extras -> ARCHIVE_LOCAL_HEADER_MISMATCH; local zip64
extra -> ARCHIVE_UNSUPPORTED_FEATURE.

ZIP STRUCTURE: the parser must consume exactly the declared
central-directory size; the central directory must end exactly at the
EOCD (any intervening unparsed record fails closed); every entry
disk-start field must be zero.

STALE DOCS: zipguard.rs and rust/README.md said ZipGuard parses ONLY the
central directory. It now parses BOTH header sets and requires agreement;
both documents corrected and the stale wording is checker-forbidden.

Counts recomputed: tests 68 -> 74, archive codes unchanged at 20.

## Move 78 candidate v4 addendum (2026-07-11)

Second hostile-review round found five more archive-safety gaps. All repaired.

1. RAW FLAGS: Entry stored only two reconstructed booleans; central_flags()
   rebuilt just bits 0x0800/0x0001, so a central/local disagreement in bit 3
   was invisible. v4 stores the raw central flags u16, compares it exactly
   to the local flags, defines SUPPORTED_FLAG_MASK (0x0800|0x0001), and
   fails closed on every other bit. central_flags() removed.

2. PARENT-PREFIX COLLISIONS: v3 caught only "x" vs "x/". v4 tracks every
   path prefix (ASCII case-folded): no file may be an ancestor of another
   entry; a file may not replace an already-required directory prefix.
   Catches "a" then "a/b", "a/b" then "a", and "A" then "a/b".

3. CRC/SIZE + RANGES: Entry now retains CRC-32, compressed and uncompressed
   sizes; validate_local_header compares all three local-vs-central, fails
   closed on the data-descriptor flag (bit 3), computes each entry's byte
   range (header+name+extra+data), requires it to end at/before the central
   directory, and rejects overlapping/embedded ranges.

4. WINDOWS HIDDEN OVERWRITE: fail closed on trailing dot/space, reserved
   DOS device names (CON/PRN/AUX/NUL/CLOCK$/COM1-9/LPT1-9, with or without
   extension) via ARCHIVE_WINDOWS_NAME_UNSAFE, and colon/ADS syntax via
   ARCHIVE_ALTERNATE_DATA_STREAM.

5. TRUTH-STATE: CURRENT_RELEASE_STATE.md now says central-directory AND
   local-header inspection; an authoritative current-state summary was
   prepended to this changelog and the earlier sections labelled superseded.

Counts recomputed: tests 74 -> 92, archive codes 20 -> 22. New codes:
ARCHIVE_WINDOWS_NAME_UNSAFE, ARCHIVE_ALTERNATE_DATA_STREAM.

## Move 78 candidate v5 addendum (2026-07-11)

Third hostile-review round. Repaired:

PRIMARY (reason-code order, same class as v3): the unsupported-flag-mask
gate ran BEFORE validate_local_header, so a central/local flag mismatch
returned ARCHIVE_UNSUPPORTED_FEATURE instead of ARCHIVE_LOCAL_HEADER_MISMATCH.
The mask gate now runs AFTER local/central raw-flag agreement is checked.
All four flag tests satisfied (verified by decision-order mirror).

MISSING STRUCTURAL TESTS: added direct tests for entry data extending into
the central directory, overlapping local-entry ranges, nonzero disk-start,
central directory not ending at EOCD, and EOCD comment-length mismatch
(byte-patch offsets pre-verified in Python).

EXTRA-FIELD POLICY: chose policy B - fail closed on EVERY non-empty extra
field, central and local, with central/local extra-length agreement
required. No allowlist retained. Both real archives have zero extra fields.
Tests for unknown central and local extra fields.

SPECIAL FILE TYPES: the Unix-mode check rejected only symlinks. Now every
non-regular, non-directory type (FIFO, socket, block/char device) fails
closed with ARCHIVE_SPECIAL_FILE_TYPE, and trailing-slash-vs-mode
disagreement fails as ARCHIVE_FILE_DIRECTORY_COLLISION. Tests for FIFO,
char device, slash+file-mode, dir-mode-no-slash.

STALE COMMENT: the module docstring wrongly said the UTF-8 flag itself
yields UNSUPPORTED. Corrected: UTF-8 flag permitted on ASCII names; all
non-ASCII names fail closed; unsupported flag bits fail closed.

Counts recomputed: tests 92 -> 103, archive codes 22 -> 23 (added
ARCHIVE_SPECIAL_FILE_TYPE).
