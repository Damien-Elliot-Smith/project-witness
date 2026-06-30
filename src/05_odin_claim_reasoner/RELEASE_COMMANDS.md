# Release commands — ODIN Claim Reasoner v0.1

## The authoritative freeze gate

The freeze gate is **exactly this sequence of individual commands**, run from a
clean extraction of the package directory. Each command must pass on its own.
There is no wrapper in the freeze definition — the individual commands are the
gate. (Lesson carried over from Coordinator v0.1.8, Companion CLI v0.1, and
Aletheia Evidence Bundle v0.1, where a wrapper orchestrator was the single failure
surface.)

```bash
python3 -m compileall -q .
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 selfcheck.py
python3 -O selfcheck.py
python3 -W error::ResourceWarning -m unittest discover -s tests
sha256sum -c odin_claim_reasoner_v01.sha256
```

Then run the static manifest check (it launches **no** subprocesses):

```bash
python3 verify_release_manifest.py
```

That is the whole freeze gate. If every command above exits 0, the release is
gated.

## No subprocess orchestrator is the gate

There is deliberately no `release_check.py` / `release_check.sh` orchestrator in
the freeze definition. If a convenience wrapper is ever added, it must be labelled
"optional convenience; not the authoritative freeze gate" and must not be used to
decide freeze-readiness.

## Manual smoke test (NOT part of the freeze gate)

```bash
cat > /tmp/claims.json <<'JSON'
{
  "odin_claim_set_version": "0.1.0",
  "case_id": "case_001",
  "claims": [
    {
      "claim_id": "claim_001",
      "subject": "evidence:evidence_001",
      "predicate": "evidence.integrity_verified",
      "object": true,
      "polarity": "AFFIRMED",
      "support": [
        {
          "support_id": "support_001",
          "source_component": "aletheia_evidence_bundle",
          "source_id": "evidence_001",
          "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        }
      ]
    }
  ]
}
JSON

python3 odin.py reason --claims /tmp/claims.json --out /tmp/odin_output
python3 odin.py verify --run /tmp/odin_output
```

Expected: `reasoning_status = CONSISTENT`, `contradiction_count = 0`, and the ODIN
output verifies.
