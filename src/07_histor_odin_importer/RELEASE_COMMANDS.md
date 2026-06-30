# Release commands — Histor-lite ODIN Importer v0.1

## The authoritative freeze gate

The freeze gate is **exactly this sequence of individual commands**, run from a
clean extraction of the package directory. Each command must pass on its own. There
is no wrapper in the freeze definition — the individual commands are the gate.
(Lesson carried over from Coordinator v0.1.8, Companion v0.1, Aletheia v0.1, ODIN
v0.1, the Bridge v0.1, the Evidence Reasoning Demo v0.1, and the Histor-lite
Aletheia Importer v0.1, where a wrapper orchestrator was the single failure
surface.)

```bash
python3 -m compileall -q .
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 selfcheck.py
python3 -O selfcheck.py
python3 -W error::ResourceWarning -m unittest discover -s tests
sha256sum -c histor_lite_odin_importer_v01.sha256
```

Then run the static manifest check (it launches **no** subprocesses):

```bash
python3 verify_release_manifest.py
```

That is the whole freeze gate. If every command above exits 0, the release is
gated. The default unit suite uses an in-process fake ODIN verifier, so the gate
spawns no ODIN subprocesses.

## No subprocess orchestrator is the gate

There is deliberately no `release_check.py` / `release_check.sh` orchestrator in the
freeze definition. If a convenience wrapper is ever added, it must be labelled
"optional convenience; not the authoritative freeze gate" and must not be used to
decide freeze-readiness.

## Manual integration smoke test (NOT part of the freeze gate)

```bash
cat > /tmp/claims.json <<'JSON'
{"odin_claim_set_version":"0.1.0","case_id":"case_001","claims":[
 {"claim_id":"claim_001","subject":"evidence:evidence_001","predicate":"evidence.present","object":true,"polarity":"AFFIRMED","support":[{"support_id":"support_001","source_component":"aletheia_evidence_bundle","source_id":"evidence_001","source_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}]}]}
JSON

python3 /path/to/odin_claim_reasoner_v01/odin.py reason \
  --claims /tmp/claims.json --out /tmp/odin_output

python3 histor_odin.py import-reasoning \
  --odin-root /path/to/odin_claim_reasoner_v01 \
  --run /tmp/odin_output \
  --out /tmp/histor_odin_case

python3 histor_odin.py verify-case --case /tmp/histor_odin_case
```

Expected: `import_status = IMPORTED_VERIFIED_ODIN`;
`source_reasoning_status = CONSISTENT`; case_id, claim_count, contradiction_count,
and proof_step_count all preserved; verify-case passes.

Also test a contradiction case (two claims, same predicate, AFFIRMED + DENIED):
ODIN yields `reasoning_status = CONTRADICTION_DETECTED`, the importer still produces
`import_status = IMPORTED_VERIFIED_ODIN`, and verify-case passes — because a
structural contradiction is a valid ODIN reasoning outcome, not a failed import.
