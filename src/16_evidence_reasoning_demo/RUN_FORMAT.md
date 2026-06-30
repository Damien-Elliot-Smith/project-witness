# Output format — Evidence Reasoning Demo v0.1

A successful `run` writes a **demo output directory**:

```
demo_report.json       the demo report (canonical JSON)
demo_steps.json        the ordered six-step record (canonical JSON)
demo_checksums.txt      sha256 of the demo files + referenced component files
aletheia_bundle/       the frozen Aletheia bundle output (preserved exactly)
bridge_output/         the frozen Bridge output (preserved exactly)
odin_output/           the frozen ODIN reasoning output (preserved exactly)
```

The component subfolders are produced by the frozen components and are **never
rewritten** by the demo. The output directory must be empty or absent before a run.

## demo_report.json

Canonical JSON. Fields: `evidence_reasoning_demo_version`, `case_id`,
`evidence_id`, `demo_status`, `aletheia_status`, `bridge_status`,
`odin_reasoning_status`, `odin_claim_count`, `generated_claims`,
`verified_outputs`, `known_limitations`.

`demo_status` ∈ {`DEMO_COMPLETED`, `FAILED_INPUT_VALIDATION`,
`FAILED_ALETHEIA_BUNDLE`, `FAILED_ALETHEIA_VERIFY`, `FAILED_BRIDGE_CONVERT`,
`FAILED_BRIDGE_VERIFY`, `FAILED_ODIN_REASON`, `FAILED_ODIN_VERIFY`,
`FAILED_CHECKSUMS_INVALID`}. A written demo output always has `DEMO_COMPLETED`; the
failure statuses are surfaced on the CLI/stderr and no successful output is written.

## demo_steps.json

Canonical JSON. `demo_steps_version`, `case_id`, and six ordered `steps`, each with
`step_id`, `component`, `operation`, and `status`. Step status ∈ {`COMPLETED`,
`FAILED`, `SKIPPED_AFTER_FAILURE`}. The fixed sequence is: Aletheia bundle-file,
Aletheia verify, Bridge convert, Bridge verify, ODIN reason, ODIN verify.

## demo_checksums.txt

Exactly five lines, `sha256sum`-style (`<digest>  <path>`):

```
<demo_report_sha256>  demo_report.json
<demo_steps_sha256>  demo_steps.json
<aletheia_bundle_manifest_sha256>  aletheia_bundle/evidence_manifest.json
<bridge_report_sha256>  bridge_output/bridge_report.json
<odin_reasoning_report_sha256>  odin_output/reasoning_report.json
```

Strict: required keys exactly once; duplicate/missing/unknown keys fail; malformed
or uppercase digests fail; hash mismatch fails.

## verify

`demo.py verify --run <dir>` performs checks 1–18 (required files + subfolders; no
unknown top-level files; canonical demo report/steps; strict checksums; recomputed
hashes; case_id matches across demo report/steps/bridge/ODIN; evidence_id matches
Aletheia + bridge; only allowed predicates; no truth-like predicate;
odin_reasoning_status == CONSISTENT; demo_status == DEMO_COMPLETED). Exit 0 +
`Demo output verified` on success, or non-zero with a specific reason on failure.
