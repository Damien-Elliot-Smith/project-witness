# CHANGELOG — Move 82: Portable binary builds

Status: CANDIDATE v07. Not adopted. Not run on Termux.

Move 82 produces ONE target-specific standalone `witness-verify`
executable for the actual native Android/Termux AArch64 target detected
during the genuine adoption run, together with a machine-readable
build-provenance record.

## Roadmap objective

Roadmap Two (`Project_Witness_Part_Two_Roadmap_Steps_71_to_130.pdf`,
Page 2, Phase One / Block A), Step 82:

> "Portable binary builds — Produce standalone binaries for Linux,
> Windows, and Termux/Android if practical."

The roadmap's own "if practical" is treated as a licence to report a
target as not currently establishable rather than to manufacture a claim.

## Adopted baseline

- `project-witness-MOVE_81_candidate_v08.zip`
- SHA-256:
  `7b49a3a5d1e1c6380b27c7b43aca721391189cffbecbf4f51a56c4d12c1d3d0d`
- Adoption transcript `MOVE_81_V08_TERMUX_GATE.txt`, SHA-256
  `5740f56790d2c2acda0738586e7676f3a00565de4341cc13238d8522dddbd31a`
- Moves 71–81 adopted.

## v07 changes (edge contract established from the adopted baseline)

Candidate v06
(8c861e78afbbdbab88a4b670cc6f94738ec8153f534fd8b857170a1ceb888e77)
reached a GENUINE first-run Termux adoption gate and is preserved
unchanged as rejected audit history, together with its first-run
transcript `MOVE_82_V06_TERMUX_GATE.txt`
(a8a37dfcce91a324127bf83733de82270774538a69ba856232aa2127228c12a7),
genuine gate exit code 1.

That run passed candidate identity and source binding, Move 81
inherited-byte immutability, native Android target detection, clean
release and debug Cargo builds, the fresh adopted Move 81 baseline
verifier build, the version probe, binary inspection, standalone
execution with an empty PATH, Move 80 fixture integrity, construction of
all ten hostile edge fixtures, the complete 79-case corpus equivalence,
and genuine Move 81 adapter byte equivalence across all 79 cases.

It failed only at edge equivalence, and for a defect that was entirely
mine. All three genuine verifier executions agreed that `edge_control.zip`
produces verdict `FAIL` and exit code 1 — the adopted baseline, candidate
release and candidate debug alike. The v06 fixture contract declared
`INCONCLUSIVE` and exit 3, because I had hand-written that expectation
from an assumption that a well-formed archive would be accepted. The gate
correctly refused to reconcile a contract I had invented with the
behaviour the adopted implementation actually has.

**The repair removes the category of error rather than the single wrong
value.** The fixture generator no longer declares any expectation at all:
`expect_verdict`, `expect_exit_code` and `expect_stage` are gone from it,
and a test scans the generator body to keep them gone. Each fixture now
records only its design INTENT — the arithmetic `surface` it targets and
the `stage_intent` it was built to reach — and intent is reported as
evidence, never enforced as an expectation.

`pin_edge_contract` establishes the complete contract from the adopted
Move 81 baseline verifier: verdict, process exit code, raw reason code,
reason class, stage, and a hash of the baseline stdout. It additionally
requires the baseline's own identity and version to be correct, its stderr
to be empty, its reason to resolve in the adopted reason map, and its
verdict to be one the adopted verifier can actually reach — a baseline
reporting `PASS` is refused rather than pinned. Both candidate profiles are
then checked independently against that established contract, and running
against a manifest with any pin missing is refused rather than silently
skipped.

Consequently `edge_control.zip` now carries exactly the result the genuine
Termux run produced — `FAIL`, exit 1, at the archive stage — because it is
read from the authority rather than guessed.

Everything else from v06 is retained unchanged: 876 inherited files
byte-identical to Move 81 v08, the exact 11-file allowlist, source binding,
clean release and debug builds, the genuine adopted baseline verifier
authority, binary inspection, standalone empty-PATH execution, Move 80
fixture-integrity checking, ten hostile edge fixtures, full 79-case corpus
equivalence, genuine Move 81 adapter equivalence for 79 cases, byte-exact
canonical JSON, exact stdout/stderr/exit checking, exact archive field
sets, restricted Android linker identities, no packaged verifier binary,
and unchanged `rust/Cargo.toml` and `rust/src`. Transcript identity is now
`MOVE_82_V07_TERMUX_GATE.txt`.

## v06 structure (retained)

## v06 changes (five blockers)

Candidate v05
(c516c0bac6abc5c32f7ccb27d11547e665faf63fe94c3a71d7d1541c82602acf) was
REJECTED pre-Termux and is preserved unchanged as audit history.

**Blocker 1 was decisive and self-inflicted: v05 did not implement the
adopted Move 81 adapter contract, it reimplemented an approximation of it
from memory.** Running the genuine inherited adapter here settles it. For a
clean bundle where the raw Rust result is `INCONCLUSIVE` /
`RECEIPT_CHAIN_HASHES_RECOMPUTED` / exit 3, the adopted adapter emits:

```
operation      verify_bundle
verdict        INCONCLUSIVE
reason_code    OK          <- NORMALIZED, not the raw Rust reason
stage          complete
```

v05's hand-written field list omitted `operation` entirely and compared the
adapter's normalized `reason_code` against the RAW Rust reason. Fed that
genuine adopted record, v05 produced exactly two rejections: *"has
unexpected operation"* and *"reason_code is 'OK', adopted is
'RECEIPT_CHAIN_HASHES_RECOMPUTED'"*. The v05 gate would therefore have
failed even with a correct verifier and a correct inherited adapter.

The repair does not write a better approximation. `ADAPTER_REQUIRED_FIELDS`,
`ADAPTER_CAPABILITY_SCOPE` and `ADAPTER_PRODUCER_VERSION` are deleted, and
a test asserts they never return. For every applicable bundle and archive
case the gate now runs the genuine inherited Move 81 adapter against the
adopted BASELINE verifier and preserves its exact stdout bytes, stderr
bytes and process exit as the authority; both candidate profiles run
through that same inherited adapter and must reproduce all three
byte-for-byte. Supplying no baseline is a hard error, because without it
there is no valid authority. This preserves the adopted handling of
`operation`, normalized `reason_code`, `stage`, `verifier_version`,
`detail`, the exact field set and the exact canonical bytes, because none
of it is restated anywhere.

2. **Synthetic records are no longer the authority for success.** The v05
   "good" record was not a genuine adopted record: it lacked `operation`,
   used the raw reason, and omitted applicable `verifier_version` and
   `detail` behaviour. Tests now derive valid expected output by executing
   the inherited adapter; synthetic records appear only as hostile
   variants after a genuine baseline is established.
3. **Canonical JSON is byte-exact.** v05 parsed and compared semantic
   values, permitting non-canonical formatting.
   `check_canonical_json_bytes` compares the bytes against the canonical
   re-serialisation and independently rejects non-canonical key order,
   alternate separators or spacing, leading or trailing spaces, duplicate
   keys, more than one JSON line, a missing or extra final newline, and any
   additional stdout.
4. **Stream and status checking completed.** The second Move 80 fixture
   generation now has its own stdout file and a separately checked exit
   status; inline build-facts extraction has its own checked stderr,
   status and a non-empty-output check. `uname -m` and the version probe
   keep their separate captures. No separate commands share a stderr file,
   and there is exactly one adapter invocation block.
5. **Archive field sets are exact.** v05 permitted `entry_count` on any
   archive record, so an invented `"entry_count": 999` rode along on a FAIL
   record. The adopted verifier emits the count only from
   `verdict_line_with_count` on an accepted archive, so the field is now
   permitted and required only when the expected verdict is
   `INCONCLUSIVE`, and rejected otherwise. Missing, wrong, string, float
   and boolean counts are rejected, as are extra or missing fields.

All v05 repairs are retained: nine edge surfaces, genuine Sentinel receipt
mutation, exact edge reason/class/stage/verdict/exit enforcement, real-v20
authority with pre-execution SHA-256 verification, adopted archive entry
counts, usage-contract execution, lstat source binding, exact path and mode
comparison, rejection of links, special files, caches and `rust/target`,
restricted Android linker identities, exact Move 80 generated-fixture
integrity checking, no packaged verifier binary, separate publication, and
unchanged `rust/Cargo.toml` and `rust/src`. Transcript identity is now
`MOVE_82_V06_TERMUX_GATE.txt`.

## v05 structure (retained)

## v05 changes (six binding repairs)

Candidate v04
(ac9c273f892caf7070f7858f78fa4ee1e933446377cd088ccf483c80fe33ccd5) was
REJECTED pre-Termux and is preserved unchanged as audit history. The v04
package was clean and its suite passed 131/131 twice, but direct
executable attacks proved the production gate still accepted incorrect
evidence. That is the important lesson here: my tests confirmed that the
intended statements existed rather than that the checkers enforced them.

1. **The edge contract is now enforced, not merely recorded.** v04
   recorded expected verdicts and exit codes and never compared them, so a
   stand-in emitting PASS with exit 0 was accepted as long as its reason
   mapped to the expected stage — and release and debug agreeing on that
   same false output was treated as evidence. `check_edge_contract` now
   compares, per fixture and per profile independently: surface, raw
   reason code, reason class, stage, verdict and binary exit code, plus
   the adopted verifier identity and version. Because a hostile input's
   raw reason cannot honestly be predicted off device, it is ESTABLISHED
   from the adopted baseline verifier by `pin_edge_contract`, which first
   enforces the invariants the fixture declares by construction, and is
   then pinned so both candidate profiles must match it independently.
   Re-running the exact v04 attack now produces 40 rejections.
2. **Real archive entry counts are preserved and enforced.**
   `load_archive_cases` took `case["expected"]["rust"]` and silently
   discarded the sibling `expected.entry_count`, so the checker could only
   require that some count existed — a real-v20 record claiming
   `"entry_count": 1` was accepted against the adopted 970. The loader now
   merges the adopted count into the expectation and prefers the corpus's
   own `expected_sha256`, and the checker rejects a missing, non-integer
   or wrong count, and refuses to pass an accepted archive for which the
   corpus declares no count. The adopted counts are real_v20 970,
   real_705 819, real_move78 935. The tests drive the genuine loader
   rather than injecting an expectation by hand, because hand-injection is
   exactly what hid this defect.
3. **Adapter equivalence validates the complete record.** v04 accepted a
   stand-in with wrong stage, record `exit_code`, `capability_scope`,
   `verifier` and version, because the process exit looked right and both
   profiles agreed. `check_adapter_record` now enforces the exact
   permitted field set with no extras or omissions, exact values for
   schema_version, record_type, producer, producer_version, lane,
   input_type, capability_scope and verifier identity, the adopted verdict,
   reason and stage, the record's own exit_code, the adapter process exit
   for the verdict, exactly one canonical line with one trailing newline,
   and empty stderr — each profile checked independently.
4. **Streams are separated everywhere.** The two remaining `2>&1` merges,
   on the complete Move 81 child gate and on package hygiene, are gone.
   Both now keep stdout and stderr apart, retain each between explicit
   markers, and require stderr to be byte-empty. No acceptance command in
   the gate merges streams.
5. **Tests exercise the real production path.** The hostile cases drive
   the actual `equivalence.py` CLI, the genuine corpus loader and the
   production checkers. Two mutation-resistance tests assert that the
   production checkers detect a wrong entry_count and a wrong edge verdict
   and exit code, so removing an exact comparison would fail the suite.
6. **v04's genuine improvements are retained** — all nine edge surfaces
   from the real frozen bundle, the genuine receipt mutation in
   `coordinator_output/sentinel_run/sentinel_run.json`, the correct
   real-v20 authority with pre-execution SHA-256 verification of all real
   archives, the executed usage cases, lstat-based source binding with
   symlink/special-file/cache/target rejection, complete path-set and
   exact mode comparison, restricted Android linker identities, the
   adopted Move 80 integrity check over the exact Stage G fixtures, no
   packaged executable, and separate preserved artefacts. The transcript
   identity is now `MOVE_82_V05_TERMUX_GATE.txt`, with a test rejecting
   every stale v01–v04 identity.

## v04 structure (retained)

## v04 changes (nine hostile-review blockers)

Candidate v03
(3a75608bdc87c8596240a7a66a4a4f6a98f3425759a69bbd44393747fa9b8850) was
REJECTED at hostile packaged-byte review before any Termux run and is
preserved unchanged as audit history. v04 is built from the exact v03
tree.

**Blocker 1 was the important one, and its cause was that I tested the
edge generator against a synthetic two-file bundle instead of the adopted
frozen one.** Against the real
`freeze_record/python_behaviour_freeze_v01/reference_bundle` the generator
silently produced only five surfaces, because it mutated a top-level
`case_manifest.json` that does not exist there, and its `receipt_index`
fixture was false: the file it edited carried no receipts, no extreme
index was inserted, and the fixture could not reach the receipts stage.

The generator now uses only files the adopted verifier genuinely reads,
established from `rust/witness-verify/src`:

- `manifest::MANIFEST_FILE` is `companion_report.json`, parsed at the
  MANIFEST stage;
- `receipts::RUN_RECORD` is
  `coordinator_output/sentinel_run/sentinel_run.json`, read at the
  RECEIPTS stage;
- stage order in `main.rs` is manifest → hashes → receipts.

The JSON numeric, JSON length, JSON depth and manifest-index surfaces
mutate `companion_report.json`, which the verifier parses before the hash
stage runs. The receipt-index surface mutates a REAL receipt in the real
run record, setting `receipt_id` to 2^63−1. `sentinel_run.json` is not one
of the eight files declared in `companion_checksums.txt`, so the hash
stage is undisturbed and the receipts stage is genuinely reached — a fact
a regression test asserts by comparing every declared checksummed file
byte-for-byte. The complete surface set is REQUIRED: if any fixture cannot
be created the generator raises rather than silently producing a short
set, and a regression test proves that using a bundle that lacks the real
files. Each fixture declares its surface, expected stage, expected verdict
and expected exit code; a fixture answered at any other stage fails, as
does a reason absent from the adopted map.

2. **real_v20 is the real archive.** The
   `--real-v20 "${REAL_V20:-$REAL_MOVE79}"` substitution is gone. The gate
   uses the inherited
   `releases/roadmap_one_complete/move_70_final/Project_Witness_WORKING_STACK_v20_MOVE_70.zip`,
   and all three external archive cases are hash-pinned
   (`real_v20` 1248bc46…, `real_705` 72e38ffd…, `real_move78` 6030148c…)
   and verified BEFORE any verifier executes. `check_exact_record` now
   requires `entry_count` on an accepted archive record and compares it
   when an expectation is supplied, rather than merely permitting the
   field.
3. **The adopted usage contract is executed.** No arguments, an unknown
   command and a wrong argument count each run through candidate release,
   candidate debug, the fresh adopted baseline binary and the staged
   standalone binary under an empty PATH, requiring identical stdout
   bytes, stderr bytes and exit codes.
4. **Adapter equivalence is exact.** The complete canonical Move 81 record
   contract is enforced: schema_version, record_type, producer,
   producer_version, implementation_lane, input_type, verdict,
   reason_code, stage, capability_scope, exit_code and verifier, with
   detail and verifier_version optional, no additional or missing fields,
   exactly one canonical line with one trailing newline, the exact adapter
   exit for the verdict, and empty stderr.
5. **Transcript identity corrected** to `MOVE_82_V04_TERMUX_GATE.txt`,
   with a test asserting no stale v01/v02/v03 identity remains and that
   the changelog declares the packaged candidate version.
6. **Warning-clean target and build streams.** `rustc -vV` is no longer
   parsed through an unchecked pipeline: its status and stderr are
   captured and checked before the host line is read, and the same applies
   to platform-machine detection. The release, debug and baseline builds
   each write to their own stdout/stderr files, each checked separately —
   v03 appended the debug build to an already-checked release stderr file.
7. **Exact source metadata.** Source binding and baseline immutability
   compare exact permission bits, so a packaged 0644 against a live 0600
   fails, and the complete path set is compared including directory
   entries, so an extra empty directory fails. Symlink, special-file,
   `__pycache__`, `.pyc` and `rust/target` rejection is retained.
8. **Exact Android linker identities.** The unrestricted
   `endswith("/linker64")` acceptance is removed, so an arbitrary path
   such as `/evil/custom/linker64` is rejected; only explicit Android
   linker identities are accepted, and glibc loaders and dependencies
   remain rejected. A synthetic-ELF regression test proves it.
9. **The exact Move 80 fixture instances are verified.** After Stage G
   generates the fixtures and before either binary executes, the adopted
   `integrity_check.py` runs against that exact output directory using the
   adopted two-generation interface, requiring matching hashes and empty
   stderr. The later child regression validates a different generation, so
   relying on it alone left this one unverified.

## v03 structure (retained)

## v03 changes (twelve hostile-review blockers)

Candidate v02
(2cfbccdf47985e3ddfd8d579a88fd64cfb0741870fe40fea373139e0c2aa60f0) was
REJECTED at hostile packaged-byte review before any Termux run and is
preserved unchanged as audit history. v03 is built from the exact v02
tree.

**Blocker 2 was a packaging defect of mine with an objectively checkable
cause.** Four inherited Move 81 entries were repackaged with 0644 instead
of the adopted 0755:
`tools/check_move81_structured_verdict_adoption.sh`,
`verify/structured_verdict_v01/adapter.py`,
`verify/structured_verdict_v01/check_move81_inherited.py` and
`verify/structured_verdict_v01/structured_tests.py`. The cause was
`zipfile.extractall()`, which does not restore executable bits, so my
candidate tree was built from a mode-flattened extraction. v03 extracts
the adopted baseline with its exact mode metadata preserved, and the
inherited comparison now checks executable bits against the real archive
as well as file contents — so this class of drift is detected rather than
repackaged.

1. **Warning-clean builds are now real.** `build_binary.py` previously
   captured Cargo stderr, copied it into stdout and still reported
   `BUILD: PASS`, which laundered exactly the evidence the contract exists
   to surface. Any stderr from `cargo build`, `cargo --version`,
   `rustc --version` or `rustc -vV` now fails the build,
   `build_stderr_bytes` is always 0, and nothing is moved into stdout.
   Warning-producing fake Cargo and Rustc tests prove it.
3. **Source binding rejects non-regular live files.** It uses `lstat`
   throughout, so a symlink whose target happens to contain matching bytes
   is no longer accepted as the reviewed file. Symlink files, symlink
   directories, FIFOs, sockets and devices are rejected, and
   `__pycache__`, `.pyc` and `rust/target` are REJECTED rather than
   ignored at this pre-build stage.
4. **Exact records, not three selected fields.** Every real verifier
   invocation is checked for the adopted verifier identity, the adopted
   version, the exact field set (no extra and no missing fields, with
   `entry_count` permitted only for archive invocations), the exact
   verdict, the exact reason, the exact exit code, single-object framing
   and zero stderr bytes.
5. **The corpus is complete.** The adopted corpus pins in
   `corpus_lock.json` are verified first; the adopted
   `corpus/build_archives.py` then builds all 67 synthesised archive
   fixtures, and the three remaining adopted archive cases
   (`real_705`, `real_move78`, `real_v20`) use the real artifacts supplied
   to the gate. Together with the clean frozen bundle and all eight Move 80
   fixtures that is the complete adopted set, every case appearing exactly
   once. Archive expectations are compared as adopted reason CLASSES
   resolved through `reason_map.json`, because that is the vocabulary the
   archive corpus uses.
6. **The standalone proof covers the whole corpus.** The staged release
   binary is run for every case from a private directory outside the
   source tree with an empty PATH and private HOME/TMPDIR, and its output
   must match both the adopted expectation and the in-tree run.
7. **Adapter equivalence covers every applicable case.** Both profiles run
   through the unchanged Move 81 adapter for every bundle and archive
   case, requiring byte-identical canonical records, the exact adapter
   exit for the verdict, the expected `record_type`, the adopted producer
   identity, and no Rust PASS. An identical `measurement_error` from both
   profiles is reported as a failure, not accepted as agreement.
8. **Target, loader and dependency cross-check.** `armv8l` is removed from
   the accepted AArch64 aliases (it denotes a 32-bit userland). Only `DYN`
   is accepted, which is what the native Termux PIE release build
   produces. `PT_INTERP` is validated against genuine Android/Termux
   linker identities and glibc loaders such as
   `/lib64/ld-linux-aarch64.so.1` are rejected; `DT_NEEDED` names must be
   Bionic-compatible, and glibc libraries such as `libc.so.6` are rejected
   outright. Strict bounds and terminator checks are retained.
9. **Provenance enforces the authorised target.** Cross-field consistency
   is required across `target_triple`, `rustc_host`, `architecture`,
   `executable_format`, `build_profile`, `reported_version`,
   `cargo_package_version`, plus little-endianness and `DYN`, so an
   x86_64 Linux record can no longer validate. Publication re-reads the
   COPIED provenance file from the output directory, requires it to equal
   the staged bytes, re-parses and re-validates it, and recomputes the
   copied binary's hash against `binary_sha256`.
10. **Edge fixtures declare exact stages.** Each fixture names the adopted
    stage it must be answered at, and a case answered at any other stage
    fails; a reason absent from the adopted map fails too. Fixtures now
    cover all six identified surfaces: ZIP offset, ZIP size/count, JSON
    numeric limits, JSON length/depth, manifest/index arithmetic and
    receipt-chain/index arithmetic.
11. **Output-directory rules are executable.** They are factored into a
    production helper (`--check-output-dir`) that the gate calls, and the
    suite exercises that same helper for the valid case, non-empty,
    symlink, lowercase Downloads, shared storage, inside-candidate-root,
    outside-run-directory, relative and missing-directory cases.
12. **Documentation corrected** — see the next section.

## What the evidence actually establishes

This section exists because v02's changelog contained claims its code did
not support. Stated precisely:

- **Inherited files.** No inherited file's CONTENT or MODE METADATA
  changes. v02 claimed "no existing file changed" while four executable
  bits had in fact changed; that is fixed and now checked.
- **Cache and build directories.** They are REJECTED before the build, not
  ignored. v02's source binding silently skipped them while the prose said
  they were required absent.
- **Inline Python in the gate.** The gate performs no inline provenance
  assembly and no inline publication — both go through `provenance.py`
  subcommands. THREE small inline `python3 -c` helpers remain, for a byte
  comparison, extracting the build-facts line, and reading the pinned test
  count. v02 claimed the gate ran no inline Python at all, which was
  false.
- **Executable versus source-scan tests.** The mandatory negative cases
  run the real tools and the factored production helpers. FOUR structural
  assertions still read the gate source — that the gate calls the output
  helper, the ordering of stages, that publication comes last, and that no
  acceptance stream discards stderr. Those are retained as an ADDITIONAL
  defence, not as the primary proof, and are described as such rather than
  as executable coverage.
- **Warning-clean.** Any toolchain stderr now fails. v02 accepted Cargo
  warnings and reported PASS.
- **Copied provenance.** The file re-read and re-validated is the COPY in
  the output directory. v02 validated the staged bytes it still held.
- **Edge-surface coverage.** All nine required surfaces are produced from
  the REAL adopted frozen bundle, and the generator fails rather than
  omitting any. v03 silently produced five against that bundle.
- **Receipt-index arithmetic.** A real receipt in the real run record
  carries the extreme index, and the declared checksummed files are proven
  undisturbed so the receipts stage is reachable. v03's fixture was false.
- **real_v20.** The inherited v20 archive is used and hash-pinned; Move 79
  can no longer be substituted.
- **Usage preservation.** Executed across both profiles, the baseline
  authority and the staged standalone binary — not asserted.
- **Exact source metadata.** Exact permission bits and the complete path
  set including directories.
- **What is NOT established off device.** The Rust builds, the real binary
  inspection, the standalone runs, the profile equivalence and the
  baseline byte authority are exercised only by the genuine Termux gate
  run. Off-device evidence covers the tooling logic through synthetic ELF
  images, fake toolchains and stand-in verifiers. No claim in this
  changelog asserts a real build result.

## v02 structure (retained)

## v02 changes (ten hostile-review blockers)

Candidate v01
(ed5cd285d1d87946b65f45e35c70fd139034105482e06820b24d64d888320dad) was
REJECTED at hostile packaged-byte review before any Termux run and is
preserved unchanged as audit history. v02 is built from the exact v01 tree.

**Blocker 1 was a fatal defect I shipped.** `inspect_binary.py` wrote a
JSON object AND a `BINARY_INSPECT: PASS` marker to the same stream, while
the gate called `json.load()` on the whole thing. That raises
`JSONDecodeError: Extra data: line 2 column 1` and would have failed Stage
H with certainty on device. I had built the parse path and never once
exercised it end to end. The interface is now unambiguous: the inspector
writes canonical JSON to an explicit absolute `--json-out` file (exactly
one object, exactly one trailing newline), the human marker stays on
stdout, and the gate parses only the file. An executable integration test
now runs the real inspector CLI, feeds its JSON into the exact gate-side
assembly path, and proves architecture extraction and provenance assembly
both succeed.

2. **The live tree is now bound byte-for-byte to the verified candidate
   archive.** Hash-verifying the archive while path-checking the tree let
   a modified allowlisted file pass, binding the generated binary to
   reviewed *names* rather than reviewed *bytes*.
   `check_move82_inherited.py --verify-tree-matches-zip` now proves, in
   both directions, that every packaged file exists in the live tree with
   identical bytes, that every live source file exists in the archive,
   and that executable bits agree — with runtime cache and build
   directories required to be absent at this pre-build stage. Executable
   tests mutate an allowlisted addition and add an unlisted live file, and
   prove each is caught.
3. **Standalone asserts exact adopted behaviour.** It previously accepted
   arbitrary stdout and any exit code as long as stderr was empty. Every
   standalone case now requires an exact expected exit code, exact
   verdict and reason code, single-object stdout framing, and completely
   empty stderr; the clean frozen bundle must produce `INCONCLUSIVE` /
   `RECEIPT_CHAIN_HASHES_RECOMPUTED` / exit 3. A regression test uses a
   fake executable printing wrong output and exiting 17, and proves it
   fails rather than reporting `STANDALONE: PASS`.
4. **Controlled behaviour is checked against the adopted authorities.**
   Correctness is no longer derived from two newly built binaries agreeing.
   Cases are loaded from the adopted `expected_results.json` and
   `fixture_manifest.json`; the release binary is asserted against each
   adopted verdict, reason code and exit code FIRST, then the debug binary
   must match byte-for-byte, and every expected case must appear exactly
   once. A test proves two identically WRONG binaries do not pass, and
   identical non-empty stderr fails for every non-usage invocation.
5. **Edge fixtures reach the code they target.** The v01 JSON edge
   directories were not valid bundles, so they failed at an early stage
   before the hostile values were ever parsed — testing nothing. Edge
   cases are now built from a valid frozen bundle by changing only the
   exact file and field needed, each declares the parser stage it must
   reach, and an early-stage answer (a missing manifest or required file)
   fails the edge check. Tests prove both the early-stage rejection and
   the reaching case.
6. **Path and output-directory enforcement.** Every supplied path —
   candidate, output directory and all five `REAL_*` inputs — is required
   to be absolute AS SUPPLIED, before any canonicalisation could promote a
   relative path. The output directory must additionally sit inside the
   internal run directory derived from the canonical candidate archive's
   parent, and the real lowercase Termux forms `*/storage/downloads`,
   `*/downloads`, `/sdcard` and `*/storage/emulated/*` are rejected
   alongside the capitalised spellings.
7. **The authorised target is required exactly.** Only
   `aarch64-linux-android` / `aarch64` / ELF64 / little-endian is accepted,
   cross-checked against the rustc host triple, the actual platform
   machine and the binary's own header. An x86 Android build can no longer
   be accepted and then reported under an AArch64 adoption marker. The
   inspector accepts only `EXEC` and `DYN` and rejects `REL`, `CORE` and
   unknown types. `DT_NEEDED` parsing is now bounded by the real dynamic
   string-table extent using `DT_STRSZ` where present, requires a
   `DT_NULL` terminator, and rejects malformed, unterminated, empty or
   out-of-bounds names rather than reading unrelated file bytes as
   dependency names.
8. **Generated sidecars and failure-atomic publication.** On success the
   output directory contains exactly four files: the release binary, the
   provenance record, and a `<sha256><two spaces><basename>` sidecar for
   each. Publication rolls back every partially published file on any
   copy, chmod, hashing, validation or verification failure. After
   publication the binary hash is recomputed and required to equal
   `binary_sha256`, both sidecars are verified, the copied provenance is
   re-parsed, re-validated and required to be canonical, and the directory
   must contain exactly the four expected files. Injected-failure tests at
   every step prove the output directory returns to empty.
9. **Static gate claims replaced by executable tests.** The mandatory
   negative cases now execute the real gate and the real tools rather than
   searching the gate source. The gate itself runs no inline Python:
   provenance assembly and publication go through `provenance.py`
   subcommands, which are the exact paths the suite drives end to end.
10. **Warning-clean stream discipline.** No acceptance evidence discards
    stderr. Version probing, the release build, the debug build, fixture
    generation, edge-fixture generation, binary inspection, provenance
    generation and publication each capture stderr to their own tracked
    temporary and require it empty. The only remaining `2>/dev/null` are
    the built-in environment `unset` and a directory-emptiness probe,
    neither of which is acceptance evidence — and a test enforces exactly
    that, joining shell line-continuations so it judges whole statements.

The suite grew from 80 to 111 tests. I also mutation-tested it: reinstating
the blocker-10 stderr discard makes two tests fail, so they detect the
defect rather than passing by construction.

## v01 structure (retained)

## What Move 82 adds (new files only, all text)

- `verify/portable_build_v01/build_binary.py`
- `verify/portable_build_v01/inspect_binary.py`
- `verify/portable_build_v01/provenance.py`
- `verify/portable_build_v01/equivalence.py`
- `verify/portable_build_v01/portable_tests.py`
- `verify/portable_build_v01/EXPECTED_TEST_COUNT.txt`
- `verify/portable_build_v01/README.md`
- `verify/portable_build_v01/allowlist_move82.json`
- `verify/portable_build_v01/check_move82_inherited.py`
- `tools/check_move82_portable_build_adoption.sh`
- `CHANGELOG_MOVE_82.md`

**No existing file changed.** `rust/`, `src/`, `freeze_record/`,
`reason_map.json`, the agreement corpus, the Move 80 fixture pack, the
Move 81 structured-verdict adapter/schema/tests, the Move 79, Move 80 and
Move 81 gates, `MOVE_INDEX.md` and `CURRENT_RELEASE_STATE.md` are all
byte-identical to the adopted baseline.

## Target claims

| Target | Classification |
|---|---|
| Android/Termux AArch64 | `NATIVE_BUILD_AND_RUNTIME_TEST_PRACTICAL` |
| Linux x86_64 | `NOT_CURRENTLY_ESTABLISHABLE` |
| Linux AArch64 | `NOT_CURRENTLY_ESTABLISHABLE` |
| Windows x86_64 | `NOT_CURRENTLY_ESTABLISHABLE` |

No cross-build is attempted. The produced executable is an Android/Termux
binary and is never described as a Linux binary; the three unestablished
targets are never described with runtime language.

## Artifact model

No prebuilt `witness-verify` executable is packaged in the candidate
archive: every Move 82 addition is text. The release binary and its
provenance record are generated during the genuine Termux adoption run and
preserved separately from the source candidate. Generated bytes therefore
never live inside packaged bytes, so the two hash sets cannot be confused.

## Profile

The preserved portable artefact is a clean **release**-profile build. A
fresh **debug** binary is also built during the gate, used solely for
strict behavioural-equivalence testing, and is never preserved or
advertised as the portable artefact. `rust/Cargo.toml` and every
`rust/src` file are unchanged; no `overflow-checks` setting was added.

If any debug/release behavioural divergence appears, the gate fails and the
candidate returns for review. The divergence is not repaired inside the
gate, the tests are not weakened, and there is no fallback to shipping the
debug binary.

## Candidate identity

The candidate cannot declare its own hash. The gate requires
`MOVE82_CANDIDATE_ZIP` as an absolute regular file and
`MOVE82_CANDIDATE_SHA256` as an externally supplied value, independently
computes the archive's SHA-256 with the trusted `sha256sum`, requires exact
equality, records only the verified name and hash in provenance, and fails
before building or publishing anything if they differ.

## Output-directory contract

`MOVE82_OUTPUT_DIR` must be explicit, absolute, pre-created, empty, not a
symlink, outside the extracted candidate source root, and not under
Android Downloads. All generated work happens in a private tracked staging
directory. Only after every substantive check has passed are the final
release binary and provenance record placed in the output directory; a
failed gate publishes neither.

## Final generated filenames

Deterministic and target-specific:

```
witness-verify-<emitted version>-<detected target triple>-release
witness-verify-<emitted version>-<detected target triple>-release.provenance.json
```

The emitted version is the binary's own `0.0.8-step79-diagnostics`; the
triple is detected from the toolchain, never assumed. No filename calls the
Android binary a Linux binary.

## Build provenance

Canonical JSON (UTF-8, sorted keys, exactly one object, exactly one
trailing newline), `schema_version = witness-build-provenance/1`,
`record_type = build_provenance`. Build facts only — no bundle verdicts and
no check results, which belong to Move 83.

Two contract points worth stating:

- **There is no `transcript_sha256` field.** A transcript cannot be hashed
  until it is complete, so embedding its hash in a record written earlier
  in the same run would be circular. The record carries `transcript_name`
  only; the completed transcript receives its own independent sidecar
  afterwards.
- **`test_level` may be at most `fixture_tested`.** Adoption-tested status
  is established externally by the successful gate plus the preserved
  transcript and sidecar, and is never self-declared by a build record.
  `adoption_tested` and `publicly_releasable` are rejected outright.

`build_argv` is a JSON array carrying the exact argv, replacing the
ambiguous single-string form. `runtime_dependencies` is derived from the
produced executable and deterministically sorted. `limitations` is
non-empty and must include that this is an Android/Termux binary rather
than a general Linux binary, that no runtime evidence exists for Linux or
Windows, and that separate builds are not claimed to be byte-reproducible.

## Binary inspection

`inspect_binary.py` parses the executable itself — ELF class, endianness,
`e_type`, `e_machine` architecture, `PT_INTERP` when present and
`DT_NEEDED` when present — and depends on no PATH-resolved `file`,
`readelf`, `objdump` or `ldd`. Android compatibility is never inferred
from a filename or from the Cargo command. The gate cross-checks the rustc
host triple, the actual platform architecture and the binary's own ELF
architecture, and fails closed on any disagreement or unsupported format.

## Standalone proof

The generated release binary is copied into a private directory outside
the candidate source tree together with only the controlled input each
invocation needs, then executed by absolute path with an empty `PATH` and
private `HOME` and `TMPDIR`, using no source-relative paths, requiring
exact stdout, completely empty stderr and an exact exit code. No Cargo,
rustc, Python, shell script or Rust source is placed in that directory.
Trusted Python and shell surround the binary as instrumentation; the binary
invocation itself requires neither.

No `--version` option or any other new CLI behaviour is introduced. The
adopted CLI grammar is used exactly as it stands.

## Move 81 regression

The complete unchanged Move 81 v08 adoption gate runs from a private,
safely extracted copy of the exact `REAL_MOVE81` archive — never from the
Move 82 candidate tree — with `REAL_MOVE78`, `REAL_705`, `REAL_MOVE79` and
`REAL_MOVE80` forwarded, its complete combined output retained between
explicit markers, and child exit 0 plus
`MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: PASS`,
`MOVE_80_REGRESSION_GATE: PASS`, `SYSTEM_AGREEMENT_RESULT: FAIL` and
`SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED` required. The
two adopted divergences remain visible.

## Not adopted

- **v01** — `ed5cd285d1d87946b65f45e35c70fd139034105482e06820b24d64d888320dad`
  — REJECTED at hostile packaged-byte review. Preserved unchanged as audit
  history. Never run on Termux; never adopted.
- **v02** — `2cfbccdf47985e3ddfd8d579a88fd64cfb0741870fe40fea373139e0c2aa60f0`
  — REJECTED at hostile packaged-byte review. Preserved unchanged as audit
  history. Never run on Termux; never adopted.
- **v03** — `3a75608bdc87c8596240a7a66a4a4f6a98f3425759a69bbd44393747fa9b8850`
  — REJECTED at hostile packaged-byte review. Preserved unchanged as audit
  history. Never run on Termux; never adopted.
- **v04** — `ac9c273f892caf7070f7858f78fa4ee1e933446377cd088ccf483c80fe33ccd5`
  — REJECTED pre-Termux. Preserved unchanged as audit history. Never run
  on Termux; never adopted.
- **v05** — `c516c0bac6abc5c32f7ccb27d11547e665faf63fe94c3a71d7d1541c82602acf`
  — REJECTED pre-Termux. Preserved unchanged as audit history. Never run
  on Termux; never adopted.
- **v06** — `8c861e78afbbdbab88a4b670cc6f94738ec8153f534fd8b857170a1ceb888e77`
  — REJECTED after a genuine first-run Termux adoption gate failure at edge
  equivalence (gate exit 1). First-run transcript
  `MOVE_82_V06_TERMUX_GATE.txt`, SHA-256
  `a8a37dfcce91a324127bf83733de82270774538a69ba856232aa2127228c12a7`.
  Preserved unchanged as audit history; never adopted.
- **v07** — this candidate. Packaged for independent hostile packaged-byte
  review. It has **not** been run on a real Termux device and is **not**
  adopted. No verifier behaviour, verification capability, verdict
semantics, reason code, structured-verdict schema or legacy stdout
changed.
