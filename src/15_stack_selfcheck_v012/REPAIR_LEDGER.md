# Repair Ledger — Stack Selfcheck v0.1.2

## Build 0.1.2 — truth-boundary phrase-model compatibility repair

### Why this repair exists

Stack Selfcheck v0.1.1 cleared the legacy missing-documentation-file blocker, but
Move 30 then blocked again at documentation/truth-boundary checking:

    stack_selfcheck_status = FAILED_DOCUMENTATION_BOUNDARY
    error = sentinel_core_v022 missing boundary: does not prove truth

The v0.1 / v0.1.1 documentation truth-boundary model required one literal phrase,
"does not prove truth", on every component, and its negation scanner could be
defeated by markdown emphasis. The real frozen documentation states the same
boundary in several honest ways and uses markdown emphasis, so the literal-phrase
model rejected honest disclaimers. An audit of all 22 real components found:

- Every component states an honest truth boundary, but in varied wording —
  "does not prove evidence contents are true", "does not prove claims true",
  "does not modify the registry, run workflows, or prove truth",
  "nothing about whether the contents are true", and so on — not only the literal
  phrase.
- Markdown emphasis (for example bolded "not") and ~80-column line-wrapping split
  negations away from the tokens they govern, turning honest disclaimers into
  false affirmatives.
- `sentinel_core_v022` makes no truth-domain claim at all: it is a filesystem
  action-gating prototype that never claims to prove truth, so it has nothing to
  disclaim.

### What v0.1.2 changes

The change is confined to `stack_selfcheck_lib/documentation_checks.py`. The
phrase model is made deterministic but compatible with the real documentation.

Deterministic normalization (no LLM, no semantic model): markdown emphasis,
heading, quote, code and list markers are stripped; underscores become spaces;
line-wrapping, list structure, tabs and table pipes are flattened to spaces; text
is lowercased; sentences are split on `.`, `!`, `?` only. Flattening line-wrap and
list structure is what stops a negation being separated from the token it governs.

A required boundary is satisfied by a negated sentence that mentions the concept's
tokens, so honest disclaimers in any wording are accepted. The truth boundary is
satisfied by any of:

1. a negated sentence mentioning a truth-domain token (so the literal "does not
   prove truth" and equivalents such as "does not prove evidence contents are
   true", "does not prove ODIN claims are true", "does not verify external
   reality", "does not prove files are authentic", "does not prove sources are
   trusted" are all accepted);
2. an explicit structural-only marker ("structural verification only", "records
   structure / hashes / statuses only"); or
3. the absence of any truth-domain token at all — a component that never claims to
   prove truth needs no truth-boundary disclaimer (the vacuous case).

`sentinel_core_v022` is the one component that satisfies the truth boundary
vacuously, and it does so honestly: it is a filesystem action-gating prototype
that makes no truth-domain claim. This is recorded here transparently.

The negation scanner is now robust to markdown emphasis: "does **not** prove
truth", "does *not* verify external reality", and "does not **prove** evidence
contents are true" are all treated as negated.

### What v0.1.2 does NOT change

- **Truth-claim refusal is not weakened.** Affirmative truth-like claims
  (evidence is true, ODIN claims are true, files are authentic, sources are
  trusted, the case or stack proves reality) and affirmative out-of-scope feature
  claims (signing, external anchoring, LLM use, natural-language interpretation,
  GUI, queues, concurrency) are still refused. The refusal POLICY is unchanged —
  a sentence containing a negation/refusal marker is a limitation and is skipped,
  exactly as before; only the INPUT normalization and pattern precision changed.
- Two patterns were made more precise so they match genuine affirmative claims
  rather than incidental wording: the truth assertions are anchored to a
  truth-domain subject, so "the verifier's own ok flag is true" is not a
  violation while "evidence contents are true" still is; and the LLM /
  natural-language feature patterns now require an affirmative capability verb
  ("uses an LLM"), consistent with the other feature patterns, so a bare "LLM
  reasoning" bullet under an "Out of scope" heading is not a violation while
  "uses an LLM" still is. A battery of the documented affirmative claims confirms
  every one is still refused.
- **No frozen component was modified.** Coordinator v0.3.2, Companion v0.3.1,
  Unified Manifest v0.1, Stack Verifier v0.1, Atlas, Sentinel, Histor-lite,
  Aletheia, the Bridge, ODIN, and Case Bundle are all untouched.
- **The v0.1.1 legacy documentation allowances are kept exactly** and are not
  broadened.
- **No new feature surface.** No workflows, action types, Atlas terms, GUI, LLM,
  signing, anchoring, queues, or concurrency. No subprocess anywhere in the
  component; the freeze gate is fully in-process.
- The separate truth scanner in `verifier.py` (which scans the report Stack
  Selfcheck itself writes, controlled content) is unchanged.

### Files changed

- `stack_selfcheck_lib/documentation_checks.py` — deterministic normalization,
  negated-token boundary model with the vacuous truth clause, markdown-robust
  negation, domain-anchored truth patterns, verb-anchored LLM/NL feature patterns.
- `stack_selfcheck_lib/versions.py` — version bumped to 0.1.2.
- `tests/test_documentation_checks.py` — the one v0.1.1 test that encoded the
  over-strict "every component must carry the literal phrase" behaviour was
  repurposed: a doc that uses a truth-domain token without disclaiming is still
  refused, and a new test confirms the vacuous case (no truth-domain token) is
  accepted. All other v0.1.1 documentation tests pass unchanged.
- `tests/test_truth_boundary_model.py` — new: literal accepted, equivalents
  accepted, markdown negation accepted, vacuous accepted, list-governed-by-heading
  accepted, affirmative truth refused, affirmative feature refused, boolean-flag
  "is true" not treated as a claim.
- `verify_release_manifest.py`, README, KNOWN_LIMITATIONS, RELEASE_COMMANDS,
  RUN_FORMAT — updated to 0.1.2, new sha filename, and the new required doc
  statements.

### Result

The literal phrase model required one wording and mishandled markdown negation;
v0.1.2 makes the phrase model deterministic but compatible with the actual frozen
documentation, no frozen component was modified, and truth-claim refusal was not
weakened. Run against the real 22-component inventory with a real Stack Verifier
output produced from Coordinator v0.3.2 -> Companion v0.3.1 -> Unified Case
Manifest v0.1 -> Stack Verifier v0.1, Stack Selfcheck v0.1.2 reaches
STACK_SELFCHECK_PASSED, INVENTORY_VERIFIED, STACK_VERIFIER_OUTPUT_VERIFIED,
DOCUMENTATION_BOUNDARY_VERIFIED, truth_boundary_valid = true, and verify_ok =
true. The rebuilt Connected Demo reaches all seven required statuses. See
TEST_RESULTS.md.
