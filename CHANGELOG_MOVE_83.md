# CHANGELOG — Move 83: Rust verifier report output

Status: CANDIDATE v13. Not adopted. Not run on Termux.

## v13 changes (focused-suite result parsing)

Candidate v12
(1ead2fd95f24be4150fe6344ecc1664af62c67e8c0cd80883d924625b3f9b6e2)
FAILED its genuine first-run Termux adoption gate and is preserved
unchanged as rejected audit history, together with its transcript
`MOVE_83_V12_TERMUX_GATE.txt`
(d8c3d087b57cf618210476ca03bb0d3bfdca59a6b74e1d3274d831d92d5c54e7).

**The focused suite genuinely succeeded** — `Ran 260 tests`,
`OK (skipped=2)`, exit 0 — and the gate rejected its own success. This
was a gate-parser defect, with two causes:

- it required a literal `^OK$` line, so unittest's legitimate annotated
  success form did not match;
- it separately listed `skipped=` as a forbidden marker, so even a fixed
  `OK` match would have failed on the same output.

The two skips are the device-node cases. An unprivileged Android
filesystem cannot create block or character devices, which v11's changelog
predicted would happen. **The skips are legitimate and are neither removed
nor suppressed to force a bare `OK`.**

**Result validation is now a helper, `check_focused_result.py`** (the
eleventh Move 83 addition, declared in the allowlist). Success requires
all of: the suite process exited 0; stdout carries exactly one
`Ran <N> tests` line whose N equals the pinned count; the FINAL non-empty
stdout line is a valid unittest success summary; no failure summary
appears anywhere; and stderr is empty.

The accepted grammar is exactly what `unittest.TextTestRunner` emits on
success, and nothing broader:

```
OK
OK (skipped=N)
OK (expected failures=N)
OK (skipped=N, expected failures=M)
```

`unexpected successes` is deliberately excluded: `wasSuccessful()` is
False when any occur, so a run reporting them is not a success and must
not parse as one. Because the summary is anchored to the final non-empty
line, an `OK` in a test name, in earlier output, or in text a test printed
cannot satisfy it. The helper also reports `FOCUSED_RAN`,
`FOCUSED_PINNED`, `FOCUSED_SUMMARY`, `FOCUSED_SKIPPED` and
`FOCUSED_EXPECTED_FAILURES` as evidence.

Nothing else changed. The Rust, report and digest behaviour v12
established on device is untouched.

Twenty-three tests added driving the real validator: every legitimate
success form including the exact Termux summary; skip counts reported
rather than suppressed; `FAILED` rejected; nonzero exit rejected despite
`OK` text; an earlier `OK` line, a test named `test_OK`, and text injected
after the summary each unable to spoof success; seven malformed
annotation forms rejected; `unexpected successes` rejected; pinned-count
mismatch still failing; a missing `Ran` line, non-empty stderr and empty
stdout each rejected; relative paths refused; and gate-level checks that
the validator is wired in and that both defective patterns are gone.

Suite: 260 -> 283 tests. Transcript identity is now
`MOVE_83_V13_TERMUX_GATE.txt`.

## v12 structure (retained)

## v12 changes (test prerequisites established, not assumed)

Candidate v11
(ae2b376c25ed8256e660c4256866a34b3f8fdbab47d13eec71056578548556a7)
FAILED its genuine first-run Termux adoption gate and is preserved
unchanged as rejected audit history, together with its transcript
`MOVE_83_V11_TERMUX_GATE.txt`
(226211ad0b9cfdac5fe122e5369bd1f993a066b2901c99acf223ca6c8a811c07).

The run reached Stage I and established a great deal: candidate identity,
live source binding, output-directory safety, Move 82 v07 inheritance with
886 files byte-identical, one strictly additive `main.rs` modification and
ten declared additions matched exactly, native `aarch64-linux-android`,
clean release and debug builds under cargo/rustc 1.96.0, **the Rust unit
suite at 133/133**, release binary inspection, standalone execution, Move
80 fixture integrity, the full corpus at 79/79, Move 81 adapter
equivalence at 79/79, hostile edge equivalence at 10/10, the usage
contract, structured report output, the digest structural fixtures, and
build provenance — with the publication directory left empty on failure.

It then failed one test, `test_fifo_and_socket_differ_only_in_type`, on
`AssertionError: 384 != 420` — 0600 against 0644.

**The implementation was not at fault; my test was.** `os.mkfifo(path,
0o644)` has its mode masked by the process umask, and Termux runs with a
restrictive umask, so the FIFO landed at 0600 while the socket had been
explicitly chmod'ed to 0644. The pair therefore differed in mode as well
as type, and the test failed its own prerequisite before it could compare
digests. **The digest implementation is unchanged in v12.**

**Modes are now set explicitly and verified.** A new `set_mode()` helper
chmods the entry, reads the mode back with `lstat`, and raises if the
filesystem did not take it. It is applied to every created entry — regular
files, FIFOs, sockets, directories and device nodes — so no creation
default, umask, Python default or platform behaviour is relied on. The
builder records the verified mode per side, and each test re-reads it from
`lstat` and asserts both sides match **before** making any type claim. The
payload file's mode and bytes are also asserted identical across sides, so
nothing but the special entry can move the digest.

**Symlinks are handled honestly rather than assumed.** A symlink's mode
cannot be set portably, so the builder records `null` for that side and
`fifo_vs_symlink` explicitly asserts the FIFO side is normalised and the
symlink side is recorded as absent — it never claims a mode equality it
cannot establish.

**Every other special-entry test was audited for the same hazard** and now
asserts the prerequisite: `fifo_vs_file`, `socket_vs_file`,
`fifo_vs_directory`, `chardev_rdev_differs` and `blockdev_vs_chardev`.
Directory modes in the empty-directory cases are normalised too.

**The hazard was reproduced off device.** Under `umask 077` the v11 code
produces exactly the Termux result — FIFO 0600, socket 0644 — while the
v12 fixtures produce 0644 on both sides, and the whole suite passes under
that umask.

Seven tests added covering `set_mode` verification, recorded-mode
fidelity, mode sharing across every non-symlink pair, an explicit
umask-masking probe, directory-mode normalisation, payload equality, and
fail-closed behaviour when a mode cannot be set.

Suite: 253 -> 260 tests. Transcript identity is now
`MOVE_83_V12_TERMUX_GATE.txt`.

## v11 structure (retained)

## v11 changes (a distinct tag for every Unix entry type)

Candidate v10
(b2941331b3f379229d6a65fe18c33be90b8b3532f8a6709a1c610bf6e702f991) was
REJECTED pre-Termux and is preserved unchanged as audit history.

v10 bound directories, raw path bytes, symlink targets, kinds and modes,
and those repairs are retained. But it collapsed every remaining Unix type
into a single `ENTRY_KIND_OTHER = 4` with an empty payload. A FIFO and a
socket at the same path with the same mode therefore produced the same
digest, as did two device nodes differing only in device identity. The
"injective over the complete tree" claim was not established.

**Every type now carries its own tag.** `ENTRY_KIND_OTHER` is gone.

| Tag | Entry type | Payload bound |
|---|---|---|
| 1 | regular file | 64 lowercase-hex bytes of the content SHA-256 |
| 2 | directory, including empty | (empty) |
| 3 | symbolic link | RAW target bytes, never followed |
| 4 | FIFO | (empty) |
| 5 | socket | (empty) |
| 6 | block device | 8-byte little-endian `rdev` |
| 7 | character device | 8-byte little-endian `rdev` |
| 8 | unrecognised | (empty) |

Tag 8 is reached only if the kernel reports a type none of the Unix
predicates recognise. It is a distinct tag, not a bucket the known types
fall into. Every entry additionally binds its length-prefixed raw relative
path bytes and its actual mode masked with `0o7777`, and the domain prefix
is bumped to `witness-bundle-digest/3`.

**Device identity is bound.** Two character devices differing only in
`rdev` are distinguished, and a block and a character device sharing an
`rdev` are distinguished by their tags.

Types come from `std::os::unix::fs::FileTypeExt` and `rdev` from
`std::os::unix::fs::MetadataExt` — both in the standard library, so the
workspace remains free of external crates, and both are available under
Android/Termux. Symbolic links are still never followed: `fs::read_link`
only, and `fs::canonicalize` is absent from the module. No verifier
verdict semantics changed and **the report schema is unchanged**.

Seven special-entry fixture pairs added: `fifo_vs_file`,
`fifo_vs_socket`, `socket_vs_file`, `fifo_vs_directory`,
`fifo_vs_symlink`, `chardev_rdev_differs` and `blockdev_vs_chardev`. The
FIFO/socket pair is normalised to the same mode so only the type differs;
the two character devices differ only in `rdev`; the block and character
device share an `rdev` and differ only in type.

**Honesty about the environment.** Each fixture is attempted and, where
the entry type cannot be created, is recorded with `supported: false`, the
reason, and no sides — so nothing downstream can treat it as tested, and
the gate skips it. In the packaging environment all seven were creatable
and were verified on disk to be genuinely the intended types. Under an
unprivileged Termux run the device cases will very likely record
`supported: false`; that is expected and is reported rather than hidden.

Suite: 236 -> 253 tests. Transcript identity is now
`MOVE_83_V11_TERMUX_GATE.txt`.

## v10 structure (retained)

## v10 changes (complete-tree digest binding; stale baseline docs)

Candidate v09
(dc926445c385650cf69d89d4d4dde702993ae3051293ef864314c575a9e8b0ef) was
REJECTED pre-Termux and is preserved unchanged as audit history.

**The bundle digest did not bind what it claimed.** `collect_files()`
serialized regular files only. Directory identities were never serialized,
and non-regular entries were counted but not identity-bound. So a tree
containing an empty directory and one without it produced the same
`input_digest.value`, as did two symlinks with different targets. Calling
that a digest of the complete bundle tree was false.

**The repair binds every entry with an explicit type.** `collect_entries()`
now walks the whole tree and records a typed entry for every regular file,
every directory including empty ones, every symlink and every other entry.
The domain prefix is bumped to `witness-bundle-digest/2` so a v10 digest
can never be mistaken for a v09 one. Each entry serializes as:

```
u32le(kind)          1 file | 2 directory | 3 symlink | 4 other
u64le(pathlen) || raw relative-path bytes
u32le(actual Unix mode & 0o7777)
u64le(payloadlen) || payload
```

The payload is the 64 lowercase-hex bytes of a regular file's content
SHA-256, the RAW target bytes of a symlink, and empty for a directory or
other entry. The listing is preceded by the domain prefix and an 8-byte
entry count, and entries are ordered by raw relative-path bytes then kind.

Because the kind tag is explicit and every variable-length element is
length-prefixed, distinct trees cannot collapse: adding, removing or
renaming an empty directory changes the digest; a file cannot masquerade
as a directory or a symlink; and two symlinks with equal counts but
different targets are distinguished. **Symlinks are still never followed**
— only their target bytes are bound as identity — so nothing outside the
bundle can be drawn in. No verifier verdict semantics changed.

**What the counts do and do not cover is now stated.** `file_count` counts
regular files only and `non_regular_entry_count` counts symlinks and other
entries; directories are bound into the digest but counted by neither. The
report scope says exactly that, so no field is described as covering more
than it does. **The report schema is unchanged** — no field was added,
removed or renamed.

**Secondary repair.** `verify/report_v01/check_move83_inherited.py` still
described comparison against the "REAL adopted Move 81 v08 ZIP". Move 83's
inherited baseline is Move 82 v07, and the documentation now says so. The
remaining Move 81 references across the Move 83 files were inspected and
left alone: they name Move 81 v08 as a dependency the Move 82 child gate
requires, and as the owner of the adapter used for equivalence, which is
genuinely what it is.

Structural differential fixtures added, each pair differing ONLY in tree
structure with identical regular-file bytes and modes on both sides:
`empty_dir_added`, `empty_dir_removed`, `empty_dir_renamed`,
`nested_empty_dir`, `file_vs_directory`, `symlink_target_differs` and
`symlink_vs_file`. The gate runs the real compiled binary over both sides
of each with both profiles and requires the digests to differ, and now
also digests the identical tree twice and requires the two runs to agree.

Suite: 217 -> 236 tests. Transcript identity is now
`MOVE_83_V10_TERMUX_GATE.txt`.

## v09 structure (retained)

## v09 changes (Move 82 child run directory; single-sourced transcript identity)

Candidate v08
(3956ae19fe8f3cf348b797269f1c6d7a11075a8393674b1fb74e05384b70d413)
reached a GENUINE Termux run and is preserved unchanged as rejected audit
history, together with its first-run transcript
`MOVE_83_V08_TERMUX_GATE.txt`
(b6f648f37dc7b8dbaae8b3a926ad4f171757725c7e9df0e01d9c40fca6f00146),
genuine gate exit code 1, run directory
`$HOME/m83_v08_internal_20260807_121201`.

That run established almost everything this move exists to establish:
trusted bootstrap, nested execution, the production-helper preflight, the
Rust source sanity stage, candidate identity and source binding,
output-directory validation, adopted Move 82 v07 baseline verification,
inherited-byte preservation, clean release and debug builds, the fresh
adopted baseline verifier build, **the complete Rust unit suite at
133/133**, binary inspection, standalone empty-PATH execution, the full
79-case corpus equivalence, genuine Move 81 adapter equivalence, 10/10
hostile edge fixtures, the usage contract, `witness-report/1` core and
classified reports, the mode/content/path digest hostility stage, build
provenance validation, and **the Move 83 focused suite at 200/200**.

It failed only when invoking the privately extracted adopted Move 82 gate.

1. **The child output directory now satisfies the adopted contract.** The
   adopted Move 82 gate derives its run directory as the directory
   CONTAINING the candidate zip it is handed, then requires its
   `MOVE82_OUTPUT_DIR` to sit inside that run directory while staying
   outside the extracted source root. v08 passed the real adopted zip from
   wherever the operator placed it and an unrelated temporary directory as
   the output, so the two never nested and the adopted checker correctly
   refused the layout.

   The gate now builds an explicit private child run directory:

   ```
   <child-run>/
       project-witness-MOVE_82_candidate_v07.zip   # staged, hash re-verified
       project-witness-main/                       # extracted adopted source
       move82_output/                              # fresh and empty
   ```

   The adopted zip is copied in and its SHA-256 re-checked against
   `7c3340f1...` after staging, so the child's run directory resolves to
   `<child-run>` and the output directory sits inside it and outside
   `project-witness-main`. Before the child is invoked, the gate runs the
   **adopted Move 82 output-directory checker itself**, from the extracted
   adopted tree, against the exact paths the child will receive — so an
   invalid layout fails immediately instead of after minutes of child
   work. The adopted checker is used, never weakened, bypassed or
   modified, and the Move 83 publication directory is still never reused.

2. **The transcript identity is single-sourced.** v08's provenance
   recorded `"transcript_name":"MOVE_83_V06_TERMUX_GATE.txt"`, which was
   false: the name was hard-coded at the provenance call site and never
   moved when the renames were applied elsewhere. The gate now defines
   `MOVE83_TRANSCRIPT_NAME` once and the provenance call references that
   variable, so the literal appears exactly once in the whole script and
   cannot drift again.

Executable tests added: the genuine v09 child layout is accepted by the
adopted checker; an output directory outside the child run directory,
inside the extracted source root, symlinked, or non-empty is each
rejected; the run directory is proven to be the directory holding the
child zip; the gate builds that layout, re-verifies the staged zip hash,
pre-validates with the adopted checker, never reuses the Move 83 output
directory, and passes the child exactly the staged zip and validated
output directory; the adopted checker is absent from both allowlists; the
transcript name is defined once and referenced by variable; and no stale
v06, v07 or v08 identity survives in active gate output.

Suite: 200 -> 217 tests. Transcript identity is now
`MOVE_83_V09_TERMUX_GATE.txt`.

## v08 structure (retained)

## v08 changes (report.rs made valid Rust again)

Candidate v07
(63dda0f0087c9cefc18ca7be5b1dde77ad0b9c9e0c064b0b760bcc276435e446) was
REJECTED pre-Termux and is preserved unchanged as audit history.

**report.rs did not parse as Rust.** `DIGEST_SCOPE_BUNDLE`'s first string
literal terminated at `non_regular_entry_count.";` and the tail of an
earlier revision of the same prose was left sitting after it as bare Rust
tokens. The cause was an edit that located the constant's terminating
semicolon with a plain search, which found a `;` inside the string content
instead of the real terminator and spliced the replacement in front of the
old tail.

Two things made this survive to packaging. The focused suite passed
182/182 while checking nothing about the Rust source at all. And the
delimiter-balance check I had been relying on could not see it, because
`they are counted separately in` contains no braces, parentheses or
brackets.

1. **`DIGEST_SCOPE_BUNDLE` is repaired** as exactly one valid Rust string
   constant, with nothing between its closing quote and the semicolon.
   Every required fact is retained and none is duplicated: every regular
   file is covered; raw relative-path bytes are used; ordering uses those
   same raw bytes; path bytes are length-prefixed; actual Unix mode bits
   are bound; the mask is `0o7777`; content SHA-256 is bound; the
   serialization is domain-separated; symlinks and special files are
   neither followed nor digested; non-regular entries are counted
   separately; the definition is Unix-only; and no cross-platform raw-mode
   definition is claimed. The value still contains no comma-space and no
   colon-space.
2. **A production source sanity check is added**,
   `verify/report_v01/rust_source_check.py` (the tenth Move 83 addition,
   declared in the allowlist). It strips comments, string literals, raw
   strings and char literals, then requires that every
   `const NAME: &str = ...;` block contains exactly one literal with no
   stray tokens before the semicolon, that no double quote survives
   stripping, and that no run of three or more consecutive non-keyword
   identifiers appears outside a literal. Run against the actual packaged
   v07 `report.rs` it reports the corruption; run against every adopted
   Rust source it passes.

   **It is explicitly not a compiler and says so in its own output.** The
   gate runs it before the long build purely to fail fast, and continues
   to run clean `cargo build --release`, clean `cargo build` and
   `cargo test` as the only things that establish buildability. This
   changelog makes no claim that the Python suite establishes it.

Executable tests added: the packaged Rust sources pass; every adopted Rust
source passes; prose outside a literal is detected; a constant with two
literals is detected; stray tokens before the semicolon are detected; an
unterminated literal is detected; raw strings, comments and ordinary Rust
keyword runs do not false-positive; `DIGEST_SCOPE_BUNDLE` is exactly one
literal with nothing after its terminator, states all twelve required
facts, carries no spaced separators, and contains no duplicated sentence;
the checker states it is not a compiler; and the gate runs it before a
build that still ends in `cargo test`.

Suite: 182 -> 200 tests. Transcript identity is now
`MOVE_83_V08_TERMUX_GATE.txt`.

## v07 structure (retained)

## v07 changes (one report-byte contract)

Candidate v06
(218dc804dc0d6bbbad61ad466a33ae5ef603ef23510b102d6bafd5e82c6cb3c8)
reached a GENUINE Termux run and is preserved unchanged as rejected audit
history, together with its first-run transcript
`MOVE_83_V06_TERMUX_GATE.txt`
(4d210812812518fd276bd18be3978647d39c8996e12e9b8aadcb5073b566d769),
genuine gate exit code 1, run directory
`$HOME/m83_v06_internal_20260806_185529`.

That run reached considerably further than any before it: trusted
bootstrap, nested execution, the production-helper preflight, candidate
identity, exact source binding, output-directory validation, adopted
Move 82 v07 SHA verification, baseline safety, inherited-byte
preservation, additive `main.rs` validation, the nine-file allowlist,
Android/Termux target detection, the clean release build, the clean debug
build, the fresh adopted baseline verifier build, and the version check
all passed. **The Rust compiled.**

It then ran the complete Rust unit suite: 133 tests, 132 passed, 1 failed,
cargo exit 101. The failure was
`report::tests::report_is_a_single_canonical_object`, on
`assertion failed: !line.contains(", ")`.

**The package carried two incompatible contracts.** The JSON *separators*
the report emits were already compact — the comma-space came from my
English prose inside the `input_digest.scope`, `not_run_reason` and
`limitations` string VALUES.

Taking the preferred repair rather than weakening the test, the contract
adopted is total and trivially checkable: **no comma-space and no
colon-space appears anywhere in the report line**, separator or content.
Every report string value is reworded to satisfy it, using semicolons and
sentence breaks in place of comma-space and colon-space. The failing Rust
unit test is retained unchanged and the equivalent `": "` assertion sits
beside it. No non-canonical output is normalised anywhere: a non-canonical
core report is rejected outright rather than quietly repaired by the
completion layer.

The rewording preserves every fact the validator requires — a test
reconstructs the scope value from source and asserts `regular file`,
`mode bits`, `0o7777`, `Unix-only`, `domain-separation`, `little-endian`,
`raw relative-path bytes` and `ACTUAL` all survive, and that the
limitations still state the `NOT_RUN` and no-pass facts.

Executable tests added: no production string literal contains a spaced
separator; the scope and limitations text survives the rewording; the Rust
unit test checks both spaced separators; the Python fixtures carry
neither; comma-space, colon-space, leading-space and trailing-space output
are each rejected; the completion layer receives the exact core bytes and
preserves every field value; a non-canonical core report is refused rather
than normalised; and the gate requires byte identity between the release
and debug reports.

Mutation-tested: putting comma-space back into a single report value makes
the new literal test fail.

Suite: 171 -> 182 tests. Transcript identity is now
`MOVE_83_V07_TERMUX_GATE.txt`.

## v06 structure (retained)

## v06 changes (packaged production dependencies)

Candidate v05
(a51648be71820f51cc93700e7db417b646e8632ce01a4383d283b8ac4ac2a0b1)
reached a GENUINE Termux run and is preserved unchanged as rejected audit
history, together with its first-run transcript
`MOVE_83_V05_TERMUX_GATE.txt`
(63bd7898efce6aa746b63fb6771ce6351b1cbc453d63dcd3f795d2ff446a9115),
genuine gate exit code 1, run directory
`$HOME/m83_v05_internal_20260806_154504`.

That run got considerably further: trusted bootstrap, nested execution,
candidate identity, exact source binding, output-directory validation,
adopted Move 82 v07 SHA verification, baseline safety, inherited-byte
preservation, additive `main.rs` validation, the exact nine-file addition
allowlist, and Android/Termux target detection all passed. It failed at
the first release build because the gate invoked
`verify/report_v01/build_binary.py`, which is not in the package.

**The audit found four such references, not one.** The same mechanical
`portable_build_v01` -> `report_v01` substitution had renamed the
references to `build_binary.py`, `inspect_binary.py`, `provenance.py` and
`equivalence.py` without ever creating those files. v05 died at the first
of them; the other three would have failed in turn.

**The repair reuses the adopted helpers rather than packaging copies.**
All four are ADOPTED Move 82 files, already inherited byte-identical in
this candidate at `verify/portable_build_v01/`. The gate now references
them there through a `PB` root. Copying them into `report_v01/` would have
duplicated reviewed code and invited the two copies to drift, so no new
file was added and the allowlist is unchanged at nine additions.

A **pre-flight stage** now runs before any build. It requires every local
production helper the gate invokes — nineteen files in total — to already
exist in the reviewed candidate, to be a regular file rather than a
symlink, and to be inside the verified candidate tree. No helper is ever
created during the run.

Executable hostile tests added:

- a **static self-test** that enumerates every source-tree file reference
  out of the gate itself and fails if any is absent from the package —
  this is the test that would have caught v05;
- every referenced file is a regular file, not a symlink, and inside the
  candidate tree;
- the four helpers exist at their adopted paths, are referenced there, are
  not duplicated into `report_v01/`, and are absent from the addition and
  modification allowlists because they are inherited, not added;
- the gate's pre-flight requires each helper, rejects missing, symlinked
  and outside-tree helpers, and provably precedes the first build;
- the same packaged helper drives both the release and debug builds;
- helper stdout, stderr and exit status are checked separately, with
  executable cases for a helper that fails while emitting plausible
  stdout, one that succeeds with non-empty stderr, and one that emits
  malformed metadata;
- the genuine packaged `build_binary.py` is executed and shown to fail
  closed on a relative toolchain path.

Mutation-tested: reinstating the v05 reference makes five of these fail.

Suite: 155 -> 171 tests. Transcript identity is now
`MOVE_83_V06_TERMUX_GATE.txt`.

## v05 structure (retained)

## v05 changes (canonical gate identity)

Candidate v04
(9716ceaa9fe53bf136dfaed970a4676291499d4eda11b110f9521f4675350ff2)
reached a GENUINE Termux run and is preserved unchanged as rejected audit
history, together with its first-run transcript
`MOVE_83_V04_TERMUX_GATE.txt`
(69e3776da70b79c0307ade2ce86368896b0eacd87940609ae31254a855280fa0),
genuine gate exit code 1, run directory
`$HOME/m83_v04_internal_20260806_143427`.

**The packaged gate rejected its own canonical name.** The file is
`tools/check_move83_report_adoption.sh`, present at mode 0755 and invoked
by its exact path, but the self-binding check accepted only
`*/tools/check_move83_portable_build_adoption.sh` — a file that does not
exist in the package. The gate therefore refused itself before candidate
identity, baseline immutability, the build, the tests, report equivalence
or any regression gate could run.

This is the same failure mode as the v03 rejection: the Move 83 gate was
derived from the adopted Move 82 gate by mechanical text substitution, and
`move82` -> `move83` renamed the self-binding suffix into a filename that
was never created. Syntactically valid, semantically false.

Repairs, taking the minimal option:

- the packaged filename is retained and the self-binding check now
  requires exactly `*/tools/check_move83_report_adoption.sh`. No alias,
  duplicate gate, symlink or wrapper was added: there is one genuine
  canonical gate;
- the Move 83 marker family is now internally consistent. Every Move 83
  exit path — success, usage, relative-path refusal, missing preload,
  inconclusive, untrusted script path, nested exec and `die` — emits
  `MOVE_83_REPORT_ADOPTION_GATE`, and the terminal success marker is
  `MOVE_83_REPORT_ADOPTION_GATE: PASS`. No copied Move 82 portable-build
  naming remains in active Move 83 output;
- the genuine Move 82 child references are deliberately untouched: the
  child gate is still invoked as
  `tools/check_move82_portable_build_adoption.sh` and is still required to
  emit `MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: PASS`, because those are its
  own correct identities.

Executable hostile tests added. They extract the accepting pattern
verbatim from the packaged script and run it through the shell itself, so
the semantics tested are the shell's:

- the genuine packaged name is accepted, including a real Termux-style
  absolute path;
- renamed copies are rejected, including the v04 name;
- a gate outside a `tools/` directory is rejected;
- a symlink alias is rejected, both by its own path and by its canonical
  target;
- a byte-identical clone under a different filename is rejected;
- the self-binding check provably precedes any substantive stage;
- invoking the gate under its genuine name never trips the refusal path;
- every Move 83 exit path uses the report-adoption marker family, the
  documentation and allowlist name the same gate, and the Move 82 child
  markers remain untouched.

The suite was mutation-tested: reinstating the v04 suffix and terminal
marker makes five of these tests fail.

Suite: 138 -> 155 tests. Transcript identity is now
`MOVE_83_V05_TERMUX_GATE.txt`.

## v04 structure (retained)

## v04 changes (four blockers)

Candidate v03
(218bdd2bc6637768e1ffe5162664f3211b3458c6974261df9eb56aa7b9b0432c) was
REJECTED pre-Termux and is preserved unchanged as audit history.

All four defects share one cause worth naming: the Move 83 gate was
derived from the adopted Move 82 gate by mechanical text substitution.
That produced a script which read plausibly and was syntactically valid,
but whose child invocation, marker set and diagnostics no longer described
what they actually measured.

1. **The Move 82 child gate now receives its full input contract.** v03
   forwarded only `REAL_MOVE78`, `REAL_MOVE79`, `REAL_MOVE80`, `REAL_705`
   and `LD_PRELOAD`, omitting `MOVE82_CANDIDATE_ZIP`,
   `MOVE82_CANDIDATE_SHA256`, `MOVE82_OUTPUT_DIR` and `REAL_MOVE81` — so
   the child would have terminated with usage exit 2 before establishing
   anything. The gate now requires `REAL_MOVE81` as an explicit input and
   invokes the child with the verified adopted Move 82 v07 archive and its
   adopted hash, all four `REAL_*` dependencies, and a fresh, empty,
   gate-owned output directory created outside the extracted child source
   root. The Move 83 output directory is never reused.
2. **The impossible child marker is gone.** v03 required the Move 82 child
   to emit `MOVE_83_REPORT_ADOPTION_GATE: PASS`, which no Move 82 gate can
   produce. The required set is now the adopted Move 82 terminal marker
   plus the per-stage markers proving the complete child gate ran, the
   `MOVE_81_REGRESSION_GATE: PASS` the child itself emits, and the
   expected visible `SYSTEM_AGREEMENT_RESULT: FAIL` with its reason.
3. **The broken Rust unit test is corrected and the suite is executed.**
   `report_carries_the_adopted_identities` required
   `"record_type":"verification_report"` while `report_bundle` emits the
   CORE type — only the completion layer produces the completed record.
   The assertion is corrected and four tests are added covering the core
   record type, the absence of classification in the raw record, the
   single archive check, and the unmeasurable digest state. The gate now
   runs `cargo test` after the clean build, preserving stdout, stderr and
   exit status separately and requiring a successful result line with a
   non-zero test count.
4. **Transcript authority labels now name what is measured.** Every label
   claiming Move 81 where Move 82 v07 is the authority is corrected —
   baseline immutability, the extraction evidence, the child gate
   headings, the diagnostics and the internal variable names. Move 81 v08
   remains named where it is genuinely involved: as a dependency supplied
   to the Move 82 child, and as the owner of the adapter used for
   equivalence.

Suite: 126 → 138 tests. The new child-contract and marker tests were
mutation-tested: reinstating either v03 defect makes them fail.
Transcript identity is now `MOVE_83_V04_TERMUX_GATE.txt`.

## v03 structure (retained)

## v03 changes (three blockers)

Candidate v02
(8bb67423339d131a4ac296e024eea1e54cc0c11fe5f9fa7c21fed7d446a501bb) was
REJECTED pre-Termux and is preserved unchanged as audit history.

1. **The digest now binds the ACTUAL mode bits.** v02's scope claimed each
   file serialized its mode masked with `0o7777`, but the implementation
   derived the mode from `Permissions::readonly()` — 0o444 when read-only,
   0o644 otherwise. That collapsed the executable bits, the group/other
   distinctions and the special bits, so a `0644 -> 0755` change left the
   digest unchanged while the scope claimed otherwise. `mode_bits` now
   reads `meta.permissions().mode() & 0o7777` through the Unix permission
   interface.
2. **Production-path proof, not a model of the intention.** v02's digest
   test fed a numeric mode into its own Python model and proved the model
   changed — which could never have detected the defect. The gate now
   builds paired trees differing in exactly one bound property, verifies
   the ACTUAL filesystem modes before invoking anything, runs the REAL
   compiled binary over both sides with both profiles, and requires
   differing pairs to differ, the identical control pair to match, and the
   two profiles to agree. The Python model is retained only as a
   supplementary cross-check and a test asserts the gate never uses it.
3. **The raw-path claim now matches the API.** v02 removed
   `to_string_lossy` but used `OsStr::as_encoded_bytes`, which is lossless
   yet documented as an opaque encoding rather than raw Unix bytes, so the
   "exact raw path bytes" wording overclaimed. Path authority is now
   `OsStrExt::as_bytes`, the explicit Unix byte interface.

**Stated limitation:** the digest definition is now deliberately
Unix-only. It reads the actual Unix mode and the raw Unix path bytes, and
no cross-platform raw-mode definition is claimed. This matches the only
target this project has established — Android/Termux AArch64 — and is
stated in the implementation, the report scope, the README and the tests.

Suite: 110 → 126 tests. Transcript identity is now
`MOVE_83_V03_TERMUX_GATE.txt`.

## v02 structure (retained)

## v02 changes (six blockers)

Candidate v01
(e6038b47721cf9fc961d03164ddb7580ca21655a5f18eef9de61cbb9b68ee28e) was
REJECTED pre-Termux and is preserved unchanged as audit history.

1. **Archive execution history is now honest.** The adopted
   `evaluate_archive` performs exactly ONE check,
   `zipguard::inspect_archive`. v01 invented an `archive_path_readable`
   check, recorded it FAILED when the digest could not be read, and then
   still ran and recorded the safety check — an executed result reported
   after evaluation had already stopped. The archive report now mirrors
   the adopted evaluation exactly: one check, and a missing or unreadable
   archive is reported by zipguard with its own adopted reason code.
2. **The invented reason code is gone.** `ARCHIVE_UNREADABLE_FOR_DIGEST`
   is removed; Move 83 creates and renames no verifier reason code. A
   digest that cannot be measured is now a digest STATE:
   `input_digest.state` ∈ `MEASURED` | `UNMEASURABLE`, with the value and
   counts null when unmeasurable. The validator rejects every
   contradiction between state and value or counts, and a test scans the
   Rust module for any SCREAMING_SNAKE literal outside the adopted set.
3. **The digest binds mode bits.** The serialization now encodes the
   mode bits masked with `0o7777` alongside the path and content, and the
   mask and representation are stated exactly in `input_digest.scope`.
4. **Path serialization is injective.** `to_string_lossy` is gone. The
   serialization is a domain-separation prefix
   (`witness-bundle-digest/1\n`) followed, per file in ascending order of
   RAW relative-path bytes, by an 8-byte little-endian path length, the
   raw path bytes, a 4-byte little-endian mode encoding, an 8-byte
   little-endian length of 64, and the 64 hex bytes of the file's sha256.
   Raw bytes come from `OsStr::as_encoded_bytes`, which is lossless.
5. **Reason class and stage are looked up, never restated.** The verifier
   emits `record_type: verification_report_core`; a completion step reads
   the adopted `reason_map.json` bytes and adds exactly
   `final_reason_class` and `final_stage`, emitting
   `record_type: verification_report`. A reason absent from the adopted
   map is refused. A test derives every adopted class and stage from the
   map itself and fails if any appears as a literal in production code.
6. **Production-path coverage.** The gate now runs, for every case, the
   adopted legacy invocation, the new report invocation on both profiles,
   the classification step against the adopted map, and validation of both
   the core and classified records — requiring equal exits, byte-identical
   reports across profiles, and agreement with the adopted legacy verdict.

Suite: 72 → 110 tests. Transcript identity is now
`MOVE_83_V02_TERMUX_GATE.txt`.

## v01 structure (retained)

## Roadmap objective

> **83 — Rust verifier report output** — Add structured report generation
> with verifier version, bundle hash, check results, final verdict, and
> reason codes.

## Adopted baseline

- `project-witness-MOVE_82_candidate_v07.zip`
- SHA-256:
  `7c3340f10b111196ec64e170b5a8a00b44c87e16c4b01390abf36734dc0a3a7c`
- Moves 71–82 adopted.

## Binding decisions implemented

1. **Reading C (hybrid).** A strictly additive `rust/src` change reachable
   only through two new invocations. `verify` and `inspect-archive` are
   byte-for-byte unchanged, as is the adopted usage text.
2. **Execution honesty.** Only checks that genuinely executed are
   described. A check that did not run is `NOT_RUN` with an explicit
   reason, never an inferred result.
3. **Bundle digest.** Deterministic, covering the complete input, with the
   scope stated in the record.
4. **Output contract.** Reports come only from the new invocations; no
   regression in stdout, stderr, exit codes, structured verdicts, the Move
   81 adapter or Move 82 portable-build behaviour.
5. **Separate schema** `witness-report/1`; `witness-verdict/1` untouched.
6. **Coverage** for both `verify` and `inspect-archive`.

## Changed files

Modified (1, strictly additive, declared and mechanically verified):

- `rust/witness-verify/src/main.rs` — `mod report;` plus two new arms after
  both adopted arms and before the usage fallback.

Added (9):

- `rust/witness-verify/src/report.rs`
- `verify/report_v01/report_schema.py`
- `verify/report_v01/report_tests.py`
- `verify/report_v01/check_move83_inherited.py`
- `verify/report_v01/allowlist_move83.json`
- `verify/report_v01/EXPECTED_TEST_COUNT.txt`
- `verify/report_v01/README.md`
- `tools/check_move83_report_adoption.sh`
- `CHANGELOG_MOVE_83.md`

## What the evidence establishes

- 886 inherited files byte-identical to Move 82 v07, plus exactly one
  declared strictly-additive modification, mechanically verified.
- The validator enforces execution honesty, canonical bytes, the exact
  field set, adopted identities, digest-scope honesty, non-empty
  limitations, and agreement with the adopted legacy verdict line.
- The gate runs both new invocations over the clean frozen bundle and
  every Move 80 fixture, requires byte-identical reports from both
  profiles, and validates each against the legacy line for the same input.

## What is NOT established off device

**The Rust report module has not been compiled or executed.** This
environment has no Rust toolchain. Compilation, report generation, the
digest computation, profile equivalence and the legacy cross-check are
exercised only by the genuine Termux adoption run. Nothing in this
changelog asserts a build or runtime result.

## Not adopted

- **v01** — `e6038b47721cf9fc961d03164ddb7580ca21655a5f18eef9de61cbb9b68ee28e`
  — REJECTED pre-Termux. Preserved unchanged as audit history.
- **v02** — `8bb67423339d131a4ac296e024eea1e54cc0c11fe5f9fa7c21fed7d446a501bb`
  — REJECTED pre-Termux. Preserved unchanged as audit history.
- **v03** — `218bdd2bc6637768e1ffe5162664f3211b3458c6974261df9eb56aa7b9b0432c`
  — REJECTED pre-Termux. Preserved unchanged as audit history.
- **v04** — `9716ceaa9fe53bf136dfaed970a4676291499d4eda11b110f9521f4675350ff2`
  — REJECTED after a genuine first-run Termux gate failure (exit 1) at the
  canonical self-binding check. First-run transcript
  `MOVE_83_V04_TERMUX_GATE.txt`, SHA-256
  `69e3776da70b79c0307ade2ce86368896b0eacd87940609ae31254a855280fa0`.
  Preserved unchanged as audit history.
- **v05** — `a51648be71820f51cc93700e7db417b646e8632ce01a4383d283b8ac4ac2a0b1`
  — REJECTED after a genuine Termux gate failure (exit 1) at the first
  release build, on an unpackaged helper. First-run transcript
  `MOVE_83_V05_TERMUX_GATE.txt`, SHA-256
  `63bd7898efce6aa746b63fb6771ce6351b1cbc453d63dcd3f795d2ff446a9115`.
  Preserved unchanged as audit history.
- **v06** — `218dc804dc0d6bbbad61ad466a33ae5ef603ef23510b102d6bafd5e82c6cb3c8`
  — REJECTED after a genuine Termux gate failure (exit 1) at the Rust unit
  suite, 132/133 passing. First-run transcript
  `MOVE_83_V06_TERMUX_GATE.txt`, SHA-256
  `4d210812812518fd276bd18be3978647d39c8996e12e9b8aadcb5073b566d769`.
  Preserved unchanged as audit history.
- **v07** — `63dda0f0087c9cefc18ca7be5b1dde77ad0b9c9e0c064b0b760bcc276435e446`
  — REJECTED pre-Termux: `report.rs` did not parse as Rust. Preserved
  unchanged as audit history.
- **v08** — `3956ae19fe8f3cf348b797269f1c6d7a11075a8393674b1fb74e05384b70d413`
  — REJECTED after a genuine Termux gate failure (exit 1) at the Move 82
  child output-directory contract. First-run transcript
  `MOVE_83_V08_TERMUX_GATE.txt`, SHA-256
  `b6f648f37dc7b8dbaae8b3a926ad4f171757725c7e9df0e01d9c40fca6f00146`.
  Preserved unchanged as audit history.
- **v09** — `dc926445c385650cf69d89d4d4dde702993ae3051293ef864314c575a9e8b0ef`
  — REJECTED pre-Termux: the bundle digest did not bind directory or
  non-regular identities. Preserved unchanged as audit history.
- **v10** — `b2941331b3f379229d6a65fe18c33be90b8b3532f8a6709a1c610bf6e702f991`
  — REJECTED pre-Termux: FIFOs, sockets and device nodes were collapsed
  into one generic tag. Preserved unchanged as audit history.
- **v11** — `ae2b376c25ed8256e660c4256866a34b3f8fdbab47d13eec71056578548556a7`
  — FAILED its genuine first-run Termux adoption gate at Stage I on a test
  prerequisite. Transcript `MOVE_83_V11_TERMUX_GATE.txt`, SHA-256
  `226211ad0b9cfdac5fe122e5369bd1f993a066b2901c99acf223ca6c8a811c07`.
  Preserved unchanged as audit history.
- **v12** — `1ead2fd95f24be4150fe6344ecc1664af62c67e8c0cd80883d924625b3f9b6e2`
  — FAILED its genuine first-run Termux adoption gate on a gate-parser
  defect, while the focused suite itself succeeded 260/260 with 2 skips.
  Transcript `MOVE_83_V12_TERMUX_GATE.txt`, SHA-256
  `d8c3d087b57cf618210476ca03bb0d3bfdca59a6b74e1d3274d831d92d5c54e7`.
  Preserved unchanged as audit history.
- **v13** — this candidate, packaged for independent hostile
  packaged-byte review. It has **not** been run on a real Termux device
  and is **not** adopted.
