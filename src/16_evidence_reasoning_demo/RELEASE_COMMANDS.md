# Release commands — Evidence Reasoning Demo v0.1

## The authoritative freeze gate

The freeze gate is **exactly this sequence of individual commands**, run from a
clean extraction of the package directory. Each command must pass on its own. There
is no wrapper in the freeze definition — the individual commands are the gate.
(Lesson carried over from Coordinator v0.1.8, Companion v0.1, Aletheia v0.1, ODIN
v0.1, and the Bridge v0.1, where a wrapper orchestrator was the single failure
surface.)

```bash
python3 -m compileall -q .
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 selfcheck.py
python3 -O selfcheck.py
python3 -W error::ResourceWarning -m unittest discover -s tests
sha256sum -c evidence_reasoning_demo_v01.sha256
```

Then run the static manifest check (it launches **no** subprocesses):

```bash
python3 verify_release_manifest.py
```

That is the whole freeze gate. If every command above exits 0, the release is
gated. The default unit suite uses an in-process fake component runner, so the gate
spawns no Aletheia/Bridge/ODIN subprocesses.

## No subprocess orchestrator is the gate

There is deliberately no `release_check.py` / `release_check.sh` orchestrator in the
freeze definition. If a convenience wrapper is ever added, it must be labelled
"optional convenience; not the authoritative freeze gate" and must not be used to
decide freeze-readiness.

## Manual integration smoke test (NOT part of the freeze gate)

```bash
printf "hello evidence\n" > /tmp/evidence.txt

python3 demo.py run \
  --evidence-file /tmp/evidence.txt \
  --case-id case_001 \
  --evidence-id evidence_001 \
  --aletheia-root /path/to/aletheia_evidence_bundle_v01 \
  --bridge-root /path/to/aletheia_odin_bridge_v01 \
  --odin-root /path/to/odin_claim_reasoner_v01 \
  --out /tmp/evidence_reasoning_demo

python3 demo.py verify --run /tmp/evidence_reasoning_demo
```

Expected: `demo_status = DEMO_COMPLETED`; `aletheia_status = VERIFIED_PRESENT`;
`bridge_status = CONVERTED`; `odin_reasoning_status = CONSISTENT`;
`generated_claims = evidence.present, evidence.integrity_verified`; demo verify
passes.
