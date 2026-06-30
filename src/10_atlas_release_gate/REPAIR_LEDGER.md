# Repair Ledger — Atlas Release Gate v0.1

## Build 0.1.0 — first Atlas Release Gate build

This is the first build of Atlas Release Gate v0.1. There are no prior versions
of this component to repair; this ledger records the build itself and the two
design corrections made during construction.

### Origin

Atlas Release Gate v0.1 is Move 22 of Project Witness. It follows the frozen
Atlas Registry v0.1 (Move 21) and does not modify it, nor any other frozen
component (Sentinel, Histor-lite, Case Bundle, Coordinator, Companion,
Aletheia, ODIN). It is a narrow, read-only release-gate checker.

### Corrections made during this build

1. **Honesty check made independent of the documentation check.**
   The honesty-boundary statements were initially a subset of the documentation
   boundaries, which made `FAILED_HONESTY_CHECK` unreachable (the documentation
   check, being a superset, would always fail first). The honesty check now
   additionally requires the explicit statement "does not modify the registry",
   which is not one of the documentation boundaries. This lets the honesty gate
   fail on its own and makes step_006 a genuine, separately-testable gate.

2. **Checksums verification helper corrected.**
   An early draft of `verify_checksums` constructed the checksums-file path with
   a no-op string replacement. It was replaced with a direct reference to the
   fixed `atlas_release_gate_checksums.txt` filename.

### Honesty boundary (unchanged from design intent)

The gate proves structural chain integrity of the release package only. It never
asserts the truth of registry contents, evidence, claims, files, or sources. The
verifier rejects any truth-like claim found in the gate's own report or steps.

## Build 0.1.0 — repair: real Atlas subprocess adapter argv

The default in-process unit suite passed, but running the gate against a real
frozen Atlas Registry v0.1 package returned FAILED_REGISTRY_VERIFY. The cause
was the `SubprocessAtlasRunner` command templates, which did not match the
frozen Atlas v0.1 CLI contract.

### Symptom

    release_gate_status = FAILED_REGISTRY_VERIFY

### Root cause

The adapter invoked bare subcommands (`atlas.py verify`, `atlas.py export`,
`atlas.py verify-export --run <dir>`). Frozen Atlas Registry v0.1 requires an
explicit `--registry registry/atlas_registry.json` on verify and export, an
`--out <dir>` on export, and `--export <dir>` (not `--run`) on verify-export.

### Repair

The adapter now builds the correct frozen Atlas v0.1 argv shapes:

    atlas.py verify        --registry registry/atlas_registry.json
    atlas.py export        --registry registry/atlas_registry.json --out <export_dir>
    atlas.py verify-export --export <export_dir>

Two further adapter corrections were needed for the real path to complete:

1. **verify-export working directory.** `verify-export` was being run with its
   working directory set to the export folder, where `atlas.py` does not live.
   The adapter now remembers the Atlas root from the preceding verify/export
   calls and runs `verify-export` from there (the `--export` path is absolute,
   so the export folder still resolves correctly).
2. **Injectable executor for testing.** The adapter now accepts an injectable
   executor so the unit suite can assert the exact argv and working-directory
   wiring without launching any real subprocess. The default executor still uses
   `subprocess.run`.

### Scope guarantees (unchanged)

No Atlas Registry v0.1 change. No change to Atlas Release Gate scope. No
Coordinator, Companion, red/blue pack, signing, anchoring, LLM, natural
language, workflow execution, or new registry terms. The freeze gate remains
in-process: the default unit tests inject a fake executor and spawn no
subprocesses; the real subprocess path is exercised only by the manual
integration smoke test.

### Verification

The repaired real-subprocess path was exercised end to end against an Atlas
CLI-contract-conformant stand-in (not the genuine frozen Atlas, which is owned
by that frozen component) and produced:

    release_gate_status = RELEASE_GATE_PASSED
    registry_status     = REGISTRY_VERIFIED
    export_status       = EXPORT_VERIFIED
    verify passes

Run the same two commands against a genuine frozen Atlas Registry v0.1
extraction to confirm in your environment.

## Build 0.1.0 — repair: honesty check compatible with frozen Atlas wording

After the subprocess-argv repair, running the gate against a real frozen Atlas
Registry v0.1 package returned FAILED_HONESTY_CHECK.

### Symptom

    release_gate_status = FAILED_HONESTY_CHECK

### Root cause

The honesty check (added in the previous repair) hard-required the exact phrase
"does not modify the registry" in the checked Atlas docs. Frozen Atlas Registry
v0.1 was frozen using equivalent honesty wording instead (read-only registry,
records vocabulary, does not run workflows, does not prove truth, does not call
components, does not decide truth, not connected to Coordinator/Companion), so
the gate was incompatible with the already-frozen package.

### Repair

The honesty boundary is now satisfied by the registry's honest read-only /
no-run / no-truth boundary expressed through ANY equivalent statement, grouped
into three concepts (each satisfied if any one phrasing is present):

- read-only or vocabulary:   "read-only registry" | "records vocabulary" |
                             "does not modify the registry" | ...
- no workflows or calls:      "does not run workflows" | "does not call components"
- no prove or decide truth:   "does not prove truth" | "does not decide truth"

The gate no longer requires the checked Atlas docs to contain the exact phrase
"does not modify the registry". Atlas Registry v0.1 is unchanged.

### Consequence for FAILED_HONESTY_CHECK reachability

With this relaxation the honesty concepts overlap the documentation boundaries,
so a doc that passes the documentation check (step_005) also passes the honesty
check (step_006); through the full gate, honesty failures now surface as
documentation failures first. FAILED_HONESTY_CHECK remains a defined status and
is exercised directly at the `check_honesty` unit level (positive: frozen Atlas
wording passes without "does not modify the registry"; negative: docs lacking
any read-only / no-workflow / no-truth boundary fail). This is a deliberate,
documented trade to stay compatible with the frozen Atlas package without
modifying it.

### The gate's own docs are unchanged

Atlas Release Gate's own README.md and KNOWN_LIMITATIONS.md still state "does
not modify the registry" about themselves; only the requirement on the *checked*
Atlas docs was relaxed.

### Verification

The repaired path was exercised end to end via the real subprocess executor
against a stand-in that uses the real frozen Atlas v0.1 documentation wording
(README without "does not modify the registry") and a CLI-contract-conformant
atlas.py:

    release_gate_status = RELEASE_GATE_PASSED
    registry_status     = REGISTRY_VERIFIED
    export_status       = EXPORT_VERIFIED
    verify passes

Run the same two commands against a genuine frozen Atlas Registry v0.1
extraction to confirm in your environment.

### Scope guarantees (unchanged)

No Atlas Registry v0.1 change. No Coordinator, Companion, red/blue pack,
signing, anchoring, LLM, natural language, workflow execution, or new registry
terms. Freeze gate remains in-process.

## Build 0.1.0 — repair: forbidden-feature scanner false positives on frozen Atlas

Against the genuine frozen Atlas Registry v0.1 extraction the gate returned
FAILED_FORBIDDEN_FEATURE_CHECK. The scanner was treating honest registry,
descriptive, limitation, and refusal text as affirmative feature claims.

### Symptom

    release_gate_status = FAILED_FORBIDDEN_FEATURE_CHECK

Twelve sentences were wrongly flagged, e.g. "workflow types" / "the status
vocabulary across ... Coordinator, Companion, workflow steps", the refused
out-of-roadmap action tokens "WRITE_FILE / DELETE_FILE / SHELL_COMMAND /
NETWORK_CALL", "ontology expansion", and "signing or external anchoring ... out
of scope". Markdown line-wrapping made it worse: wrapped lines split mid-sentence
so the negating/scoping context (e.g. "no", "out of scope") landed on a different
line from the forbidden term.

### Root cause

The old scanner flagged any non-negated sentence that merely contained a
forbidden term. Registry vocabulary, listed component names, refused action
types, and out-of-scope items all contain forbidden terms without being claims
of support.

### Repair

The scanner now reports a violation only for an affirmative support claim:

1. the sentence is not an explicit negation / refusal / out-of-scope disclaimer
   (markers include does not / no / never / without / refuse(s)/refused /
   forbidden / out of scope / out-of-roadmap / not supported / read-only), and
2. it contains an affirmative-support cue (supports, integrates, connects, runs,
   uses, provides, enables, performs, executes, implements, offers, and the verb
   forms signs / anchors), and
3. it mentions a forbidden feature.

Descriptive vocabulary, listed components, refused action tokens, and
out-of-scope items carry no affirmative cue, so they pass. Real claims such as
"Atlas integrates with Coordinator", "Atlas runs workflows", "Atlas supports
signing", and "Atlas provides WRITE_FILE" still fail. The gerund/noun forms
"signing" and "anchoring" are deliberately not cues (they appear in
"no signing" / "out of scope"), while the verb forms "signs" / "anchors" are.

### Verification (genuine package, real subprocess)

Run against the genuine frozen Atlas Registry v0.1 extraction via its own
atlas.py (real subprocess, not a stand-in):

    python3 atlas_release_gate.py check --atlas-root <atlas_registry_v01> --out <out>
    python3 atlas_release_gate.py verify --run <out>

Result:

    release_gate_status       = RELEASE_GATE_PASSED
    registry_status           = REGISTRY_VERIFIED
    export_status             = EXPORT_VERIFIED
    required_files_present     = true
    documentation_present      = true
    honesty_boundary_present   = true
    forbidden_features_absent  = true
    verify_ok                  = true

### Scope guarantees (unchanged)

No Atlas Registry v0.1 change. No Coordinator, Companion, red/blue pack,
signing, anchoring, LLM, natural language, workflow execution, or new registry
terms. Freeze gate remains in-process.
