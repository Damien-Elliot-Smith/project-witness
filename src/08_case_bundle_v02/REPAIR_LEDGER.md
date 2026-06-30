# REPAIR_LEDGER — Case Bundle v0.2

## Milestone

**Case Bundle v0.2 is the first Case Bundle version that combines action,
evidence, and reasoning case records into one bundle.** Case Bundle v0.1.1 packaged
a Sentinel action case only. v0.2 unifies three already-verified Histor-lite case
records — Sentinel action, Aletheia evidence, ODIN reasoning — into a single
portable, self-checked Project Witness bundle, preserving each record byte-for-byte
and proving structural integrity without ever asserting truth.

## Design decisions

- **Verify-before-bundle.** Each input case is verified in its own real producer
  format before anything is copied. The Sentinel case uses Histor-lite v0.1.2's
  3-token `checksums.txt` (`<key>  <digest>  <name>`, including a `source_run`
  line for a file outside the case folder, which is format-checked but skipped for
  in-folder hashing). The Aletheia and ODIN importer cases use 2-token
  `<digest>  <name>` files. Each verifier knows its own producer's real names and
  format.

- **Byte-for-byte preservation.** Subcase records are copied verbatim with
  `shutil.copyfile`; a test asserts every packaged file is byte-identical to its
  source. The bundle never rewrites or re-canonicalises a subcase file.

- **Shared case_id is mandatory.** Build refuses unless all three records carry one
  `case_id` (`FAILED_CASE_ID_MISMATCH`); verify re-confirms all three subcase
  summaries match `manifest.case_id`.

- **Internal + bundle-level integrity, both checked.** verify recomputes the 14
  bundle-level hashes AND re-runs each subcase's own internal checksum file. A
  tamper that is hidden by resyncing the bundle checksums is still caught by the
  subcase's internal checksums (covered by tests 35–37).

- **CONTRADICTION_DETECTED is packageable.** Both `CONSISTENT` and
  `CONTRADICTION_DETECTED` ODIN cases bundle and verify; only `INVALID_INPUT` is
  refused, at build and again at verify.

- **Field-mapping, documented not invented.** The frozen Sentinel case uses
  `import_status` / `sentinel_replay_verdict`; the manifest maps these to
  `sentinel.case_status` / `sentinel.action_status` rather than renaming the
  preserved subcase fields. Recorded in README and versions.py.

- **Authoritative freeze gate = explicit command list** (`RELEASE_COMMANDS.md`)
  plus the static `verify_release_manifest.py` (imports only ast/os/sys, no spawn
  call sites, AST-checked by test 48). No subprocess orchestrator is in the gate;
  the default suite uses in-process fakes / synthesized case folders.

## Repairs

### R1 — truth-scan false positive against the bundle's own disclaimers
- **Found:** the very first real end-to-end build self-verify failed with
  `TRUTH_CLAIM`: "contains 'are true'". The forbidden-token list included the bare
  substrings `"are true"` and `"is authentic"`, which collide with the manifest's
  own honest `known_limitations` ("It does not prove evidence contents **are
  true**", "It does not prove ODIN claims **are true**"). The scan was flagging the
  disclaimer that *denies* the truth claim.
- **Fix:** narrowed `FORBIDDEN_TRUTH_TOKENS` to affirmative, predicate-style forms
  only (e.g. `evidence_is_true`, `claims_are_true`, `file.authentic`,
  `source.trusted`, `proves reality`, `proven_true`) and removed the bare phrases
  that appear inside legitimate negated disclaimers. Added a `DISCLAIMER_FRAGMENTS`
  list and made `scan_truth()` strip those known disclaimer sentences before
  scanning. Injected affirmative truth claims in the manifest and in replay reports
  are still caught (tests 43–44); the honest disclaimers pass (test in
  test_validation: `scan_truth allows disclaimers`).
- **Lesson (recurring across the stack):** an honesty scanner must not collide with
  the honest text it is meant to protect. Scan for affirmative claims, and strip
  the known negated-disclaimer sentences first.

### Test self-correction — truth scan ordering vs internal checksums
- While writing test 44 (truth claim in a replay report), the first version edited
  the ODIN replay and resynced only the *bundle* checksums; verify then failed at
  the earlier `INTERNAL_ODIN_CHECKSUM_MISMATCH` rule (15–17) before reaching the
  truth scan (24). Corrected the test to also resync the ODIN subcase's internal
  checksums, so the injected truth claim is what verify objects to. This confirmed
  the rule ordering is sound: internal integrity is checked before the semantic
  truth scan.

## Real end-to-end integration (documented, not part of the freeze gate)

Built from the **real frozen** upstream chain: a Sentinel `PASS_STRICT` case
(Histor-lite v0.1.2, derived `case_id = case_83cd1ba75eddfa05`), a matching
Aletheia evidence case (`VERIFIED_PRESENT`), and a matching ODIN reasoning case
sharing that `case_id`. `build` produced `BUNDLED_VERIFIED_CASE`; `verify` passed;
every subcase file was byte-identical to its source. A second run with a real
`CONTRADICTION_DETECTED` ODIN case also built and verified successfully —
confirming a structural contradiction is a valid packageable outcome.
