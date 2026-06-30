# Stack Selfcheck v0.1.2

Stack Selfcheck v0.1.2 checks that the frozen Project Witness stack inventory is
present, version-consistent, checksum-valid, and truth-bounded. It does not run
workflows, copy evidence contents, or prove truth.

This is a narrow compatibility repair over v0.1.1. The check logic, output shape,
and CLI are unchanged except that the documentation truth-boundary check now
accepts equivalent truth-boundary wording already present in the real frozen
documentation, and the negation scanner is robust to markdown emphasis. No frozen
component is modified, and the refusal of affirmative truth-like claims and
affirmative out-of-scope feature claims is not weakened. The v0.1.1 legacy
documentation allowances are kept exactly and are not broadened.

## What it is

Stack Selfcheck is a standalone, read-only stack health check. It reads one
`stack_inventory.json` describing the frozen Project Witness Local v1 components
and confirms the required components are present, their roots exist, their
expected project files and documentation boundaries are present, their zip
sidecars match where provided, and their documentation stays inside the truth
boundary. It can optionally cross-check one existing Stack Verifier v0.1 output.
It is standard-library only.

It does not run workflows. It does not call frozen components during the freeze
gate. It does not copy evidence contents. It does not prove truth: it records
that the inventory was verified, that required component folders were present,
that zip sidecars matched, that documentation boundaries were checked, and that
an optional Stack Verifier output was structurally verified. It never asserts
that evidence is true, that ODIN claims are true, that files are authentic, that
sources are trusted, or that the case or stack proves reality.

The inventory file may contain absolute local paths because it is an input
configuration. The output report stores labels only and never stores absolute
paths.

## Truth-boundary phrase model (new in v0.1.2)

Earlier versions required the single literal phrase "does not prove truth" on
every component and used a negation scanner that markdown emphasis could defeat.
The real frozen documentation states the same boundary in several honest ways and
uses markdown emphasis, so that model blocked the Connected Demo.

v0.1.2 makes the phrase model deterministic but compatible. Documentation text is
normalized deterministically — markdown emphasis stripped, line-wrapping and list
structure flattened, whitespace collapsed, lowercased — with no LLM and no
semantic model. A truth-boundary statement is recognised when, after
normalization, a negated sentence mentions a truth-domain token (so the literal
"does not prove truth" and equivalent honest wordings such as "does not prove
evidence contents are true", "does not prove ODIN claims are true", "does not
verify external reality", "does not prove files are authentic", and "does not
prove sources are trusted" are all accepted), or an explicit structural-only
marker is present (such as "structural verification only" or "records structure /
hashes / statuses only"), or the documentation makes no truth-domain claim at all
(a component that never claims to prove truth needs no truth-boundary disclaimer).

Markdown emphasis no longer breaks negation: "does **not** prove truth", "does
*not* verify external reality", and "does not **prove** evidence contents are
true" are all treated as negated, not affirmative.

The refusal of affirmative claims is unchanged in strength. Affirmative truth-like
claims (evidence is true, ODIN claims are true, files are authentic, sources are
trusted, the case or stack proves reality) and affirmative out-of-scope feature
claims (signing, external anchoring, LLM use, natural-language interpretation,
GUI, queues, concurrency) are still refused.

## Legacy documentation compatibility (unchanged from v0.1.1)

Four early frozen components were sealed before the later documentation
convention. Legacy frozen components may omit only the exact documentation files
their recorded profile permits:

- `sentinel_core_v022` may omit KNOWN_LIMITATIONS.md and RELEASE_COMMANDS.md
- `histor_lite_v012` may omit RELEASE_COMMANDS.md
- `case_bundle_v011` may omit RELEASE_COMMANDS.md
- `atlas_red_blue_pack_v01` may omit KNOWN_LIMITATIONS.md and RELEASE_COMMANDS.md

The allowance is opt-in per component via the inventory field
`legacy_documentation_profile` (value `pre_documentation_convention_v0`), is never
automatic, and is recorded honestly in the report. These allowances are kept
exactly as in v0.1.1 and are not broadened.

## How to run check

    python3 stack_selfcheck.py check \
      --inventory /path/to/stack_inventory.json \
      --out /path/to/stack_selfcheck_output

Optionally cross-check a Stack Verifier output:

    python3 stack_selfcheck.py check \
      --inventory /path/to/stack_inventory.json \
      --stack-verifier-run /path/to/stack_verifier_output \
      --out /path/to/stack_selfcheck_output

## How to run verify

    python3 stack_selfcheck.py verify --run /path/to/stack_selfcheck_output

## How to selfcheck

    python3 stack_selfcheck.py selfcheck

## Optional: summary (read-only)

    python3 stack_selfcheck.py summary --run /path/to/stack_selfcheck_output

## Boundaries

- Stack Selfcheck v0.1.2 checks frozen stack inventory and release hygiene.
- It does not run workflows.
- It does not call frozen components during the freeze gate.
- It does not copy evidence contents.
- It does not prove truth.
- Optional Stack Verifier output may be cross-checked.
- The truth-boundary phrase model accepts equivalent truth-boundary wording and
  is robust to markdown emphasis; affirmative truth-like and out-of-scope feature
  claims are still refused.
- Legacy documentation allowances are explicit, narrow, and recorded; they are
  unchanged from v0.1.1 and do not weaken checks for newer components.

## A note on ATLAS_VALIDATED

`ATLAS_VALIDATED` is the Coordinator v0.3 validation result, not an Atlas Registry
v0.1 vocabulary term. When an optional Stack Verifier output is cross-checked,
Stack Selfcheck relies on that output's own already-computed `truth_boundary_valid`
and `atlas_vocabulary_valid` results.
