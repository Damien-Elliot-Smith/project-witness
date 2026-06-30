# Test Results — Stack Selfcheck v0.1.2

All commands run from a clean extraction of `stack_selfcheck_v012/`. Standard
library only. No network. No subprocess anywhere in the component.

## Authoritative release gate (RELEASE_COMMANDS.md)

| # | Command | Result |
|---|---------|--------|
| 1 | `python3 -m compileall -q .` | PASS |
| 2 | `python3 -m unittest discover -s tests -v` | PASS — 96 tests, OK |
| 3 | `python3 -O -m unittest discover -s tests -v` | PASS — 96 tests, OK |
| 4 | `python3 selfcheck.py` | PASS — all 10 gates |
| 5 | `python3 -O selfcheck.py` | PASS — all 10 gates |
| 6 | `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS — 96 tests, OK |
| 7 | `sha256sum -c stack_selfcheck_v012.sha256` | PASS — 41 files OK |
| 8 | `python3 verify_release_manifest.py` | PASS — launched no subprocesses |

The suite grew from 86 (v0.1.1) to 96. No prior test was deleted or relaxed; one
v0.1.1 test was repurposed to match the corrected, more-precise truth-boundary
model (see REPAIR_LEDGER.md), and a new `test_truth_boundary_model.py` was added.

## Phrase-model battery (the required cases)

Run directly against `documentation_checks`:

**Literal phrase still accepted**

    "It does not prove truth."                          -> accepted, boundary present

**Equivalent truth-boundary phrases accepted**

    "It does not prove evidence contents are true."     -> accepted
    "It does not prove ODIN claims are true."           -> accepted
    "It does not verify external reality."              -> accepted
    "It does not prove files are authentic."            -> accepted
    "It does not prove sources are trusted."            -> accepted
    "Structural verification only."                     -> accepted
    "It records structure, hashes, and statuses only."  -> accepted
    "...run workflows, or prove truth."  (list-governed) -> accepted

**Markdown negation accepted (treated as negated, not affirmative)**

    "It does **not** prove truth."                      -> accepted
    "It does *not* verify external reality."            -> accepted
    "It does not **prove** evidence contents are true." -> accepted

**Vacuous case accepted (no truth-domain claim)**

    "A deterministic action gate. It records receipts." -> accepted

**Affirmative truth claims still refused**

    "...proves the evidence contents are true."         -> REFUSED
    "The ODIN claims are true."                         -> REFUSED
    "Evidence is true."                                 -> REFUSED
    "All files are authentic."                          -> REFUSED
    "The sources are trusted."                          -> REFUSED
    "This case proves reality."                         -> REFUSED
    "The stack proves reality."                         -> REFUSED
    "It proves truth."                                  -> REFUSED

**Affirmative out-of-scope feature claims still refused**

    "This component uses an LLM."                       -> REFUSED
    "It is powered by an LLM."                          -> REFUSED
    "It supports signing."                              -> REFUSED
    "It signs the outputs."                             -> REFUSED
    "It supports external anchoring."                   -> REFUSED
    "It provides a GUI."                                -> REFUSED
    "It supports concurrency."                          -> REFUSED
    "It supports queues."                               -> REFUSED
    "It uses natural-language interpretation."          -> REFUSED

**Precision (no false positives)**

    "The verifier's own ok flag is true."  (boolean)    -> NOT a truth claim

## selfcheck.py gates

    PASS  imports
    PASS  canonical_json
    PASS  valid_inventory
    PASS  missing_component_refused
    PASS  zip_sidecar_mismatch_refused
    PASS  bad_stack_verifier_output_refused
    PASS  verify_valid_selfcheck_output
    PASS  no_truth_claims
    PASS  legacy_documentation_allowed
    PASS  unknown_legacy_claim_refused
    selfcheck: all 10 gates passed

## Real-documentation scan (all 22 frozen components)

Running the new boundary and truth checks against the real frozen documentation
of all 22 components: 0 boundary failures, 0 truth-scan false positives. Every
component's honest truth boundary is recognised; `sentinel_core_v022` satisfies
the truth boundary vacuously (it makes no truth-domain claim), which is recorded
honestly in REPAIR_LEDGER.md.

## Real smoke test (real frozen stack + real Stack Verifier output)

A real Stack Verifier output was produced from the real chain, all run offline by
subprocess from their public CLIs:

    Companion v0.3.1 create-evidence-case   -> COMPANION_COMPLETED
       (drives Coordinator v0.3.2 + Atlas)  -> WORKFLOW_COMPLETED, ATLAS_VALIDATED
    Unified Case Manifest v0.1 build        -> SOURCE_VERIFIED
    Stack Verifier v0.1 check               -> STACK_VERIFIED (truth_boundary_valid=true,
                                                atlas_vocabulary_valid=true)

Stack Selfcheck v0.1.2 against the real 22-component inventory, cross-checking
that real Stack Verifier output:

    python3 stack_selfcheck.py check --inventory real_stack_inventory.json \
        --stack-verifier-run <real stack_verifier_output> --out <out>

    stack_selfcheck_status        = STACK_SELFCHECK_PASSED
    inventory_status              = INVENTORY_VERIFIED
    stack_verifier_status         = STACK_VERIFIER_OUTPUT_VERIFIED
    documentation_boundary_status = DOCUMENTATION_BOUNDARY_VERIFIED
    truth_boundary_valid          = true   (from the cross-checked verifier)
    verify_ok                     = true
    legacy_documentation_allowance_count = 4

    python3 stack_selfcheck.py verify --run <out>
    -> {"stack_selfcheck_status": "STACK_SELFCHECK_PASSED", "verify_ok": true}

All six required fields are reached against the real frozen documentation. No
green run was faked.

## Connected Demo (Move 30)

The rebuilt Project Witness Connected Demo v0.1 was run for real, driving
Companion v0.3.1, Unified Case Manifest v0.1, Stack Verifier v0.1, and Stack
Selfcheck v0.1.2 (Companion driving Coordinator v0.3.2 and the lower stack). It
reached all seven required statuses:

    DEMO_COMPLETED
    COMPANION_COMPLETED
    WORKFLOW_COMPLETED
    ATLAS_VALIDATED
    SOURCE_VERIFIED
    STACK_VERIFIED
    STACK_SELFCHECK_PASSED

`connected_demo.py verify` -> verify_ok = true. Move 30 is complete.
