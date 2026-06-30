# Release commands — Aletheia Evidence Bundle v0.1

## The authoritative freeze gate

The freeze gate is **exactly this sequence of individual commands**, run from a
clean extraction of the package directory. Each command must pass on its own.
There is no wrapper in the freeze definition — the individual commands are the
gate. (Lesson carried over from Coordinator v0.1.8 and Companion CLI v0.1, where a
wrapper orchestrator was the single failure surface.)

```bash
python3 -m compileall -q .
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 selfcheck.py
python3 -O selfcheck.py
python3 -W error::ResourceWarning -m unittest discover -s tests
sha256sum -c aletheia_evidence_bundle_v01.sha256
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
printf "hello evidence\n" > /tmp/evidence.txt

python3 aletheia.py bundle-file \
  --file /tmp/evidence.txt \
  --case-id case_001 \
  --evidence-id evidence_001 \
  --out /tmp/aletheia_bundle

python3 aletheia.py verify \
  --bundle /tmp/aletheia_bundle
```

Expected: `Aletheia evidence bundle verified` and
`evidence_status = VERIFIED_PRESENT`.
