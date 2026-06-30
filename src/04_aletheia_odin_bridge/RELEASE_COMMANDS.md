# Release commands — Aletheia -> ODIN Bridge v0.1

## The authoritative freeze gate

The freeze gate is **exactly this sequence of individual commands**, run from a
clean extraction of the package directory. Each command must pass on its own. There
is no wrapper in the freeze definition — the individual commands are the gate.
(Lesson carried over from Coordinator v0.1.8, Companion v0.1, Aletheia v0.1, and
ODIN v0.1, where a wrapper orchestrator was the single failure surface.)

```bash
python3 -m compileall -q .
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 selfcheck.py
python3 -O selfcheck.py
python3 -W error::ResourceWarning -m unittest discover -s tests
sha256sum -c aletheia_odin_bridge_v01.sha256
```

Then run the static manifest check (it launches **no** subprocesses):

```bash
python3 verify_release_manifest.py
```

That is the whole freeze gate. If every command above exits 0, the release is
gated. The default unit suite uses in-process fakes for the Aletheia/ODIN
boundaries, so the gate spawns no Aletheia/ODIN subprocesses.

## No subprocess orchestrator is the gate

There is deliberately no `release_check.py` / `release_check.sh` orchestrator in the
freeze definition. If a convenience wrapper is ever added, it must be labelled
"optional convenience; not the authoritative freeze gate" and must not be used to
decide freeze-readiness.

## Manual integration smoke test (NOT part of the freeze gate)

```bash
# 1. Build an Aletheia bundle
printf "hello evidence\n" > /tmp/evidence.txt
python3 /path/to/aletheia_evidence_bundle_v01/aletheia.py bundle-file \
  --file /tmp/evidence.txt --case-id case_001 --evidence-id evidence_001 \
  --out /tmp/aletheia_bundle

# 2. Convert it to ODIN claims
python3 bridge.py convert \
  --aletheia-root /path/to/aletheia_evidence_bundle_v01 \
  --odin-root /path/to/odin_claim_reasoner_v01 \
  --bundle /tmp/aletheia_bundle \
  --out /tmp/bridge_output

# 3. Verify bridge output
python3 bridge.py verify --run /tmp/bridge_output

# 4. Run ODIN reasoning on the generated claims
python3 /path/to/odin_claim_reasoner_v01/odin.py reason \
  --claims /tmp/bridge_output/odin_claims.json --out /tmp/odin_from_bridge
python3 /path/to/odin_claim_reasoner_v01/odin.py verify --run /tmp/odin_from_bridge
```

Expected: `bridge_status = CONVERTED`; ODIN claims contain only `evidence.present`
and `evidence.integrity_verified`; ODIN `reasoning_status = CONSISTENT`; ODIN output
verifies.
