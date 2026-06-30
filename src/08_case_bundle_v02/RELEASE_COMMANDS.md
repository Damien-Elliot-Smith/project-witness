# RELEASE_COMMANDS.md — Case Bundle v0.2

The **authoritative freeze gate is this explicit list of individual commands**, run
from a clean extraction of `case_bundle_v02.zip`. There is no subprocess
orchestrator in the gate. The default unit suite uses in-process fakes / format
checks, so the gate spawns no subprocesses.

Run each command and confirm it passes on its own:

```
python3 -m compileall -q .
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 selfcheck.py
python3 -O selfcheck.py
python3 -W error::ResourceWarning -m unittest discover -s tests
sha256sum -c case_bundle_v02.sha256
python3 verify_release_manifest.py
```

All eight must pass. `verify_release_manifest.py` is a static checker that imports
only `ast`, `os`, and `sys` and launches no subprocesses.

## Manual integration smoke test (NOT part of the freeze gate)

Uses the real frozen upstream components. Document-only; never part of the gate:

```
# 1. Verified Histor-lite Sentinel case (real, PASS_STRICT):
python3 <sentinel_core_v022>/sentinel.py create --run /tmp/run.json \
    --run-id case_001 --request-id req_001 --target-path newdir \
    --allowed-root /tmp/allowed
python3 <sentinel_core_v022>/sentinel.py close --run /tmp/run.json
python3 <histor_lite_v012>/histor_lite.py import-sentinel \
    --sentinel-root <sentinel_core_v022> --run /tmp/run.json --out /tmp/sent_case
# (note the derived case_id, e.g. case_83cd1ba75eddfa05)

# 2. Verified Histor-lite Aletheia evidence case (same case_id):
python3 <aletheia_evidence_bundle_v01>/aletheia.py bundle-file --file ev.txt \
    --case-id <case_id> --evidence-id evidence_001 --out /tmp/ale_b
python3 <histor_lite_aletheia_importer_v01>/histor_aletheia.py import-evidence \
    --aletheia-root <aletheia_evidence_bundle_v01> --bundle /tmp/ale_b \
    --out /tmp/ale_case

# 3. Verified Histor-lite ODIN reasoning case (same case_id):
python3 <odin_claim_reasoner_v01>/odin.py reason --claims claims.json --out /tmp/odin_out
python3 <histor_lite_odin_importer_v01>/histor_odin.py import-reasoning \
    --odin-root <odin_claim_reasoner_v01> --run /tmp/odin_out --out /tmp/odin_case

# 4. Build + 5. verify the bundle:
python3 case_bundle_v02.py build --sentinel-case /tmp/sent_case \
    --aletheia-case /tmp/ale_case --odin-case /tmp/odin_case --out /tmp/pw_bundle
python3 case_bundle_v02.py verify --bundle /tmp/pw_bundle
```

Expected: `bundle_status = BUNDLED_VERIFIED_CASE`, the case_id preserved across all
three records, each case preserved byte-for-byte, and verify passes. Both ODIN
`CONSISTENT` and `CONTRADICTION_DETECTED` are valid packageable outcomes.

## Optional convenience wrapper

Any `release_check.py` / `release_check.sh` present is **optional convenience; not
the authoritative freeze gate**. The list above is authoritative.
