# RELEASE_COMMANDS.md — Atlas Registry v0.1

The **authoritative freeze gate is this explicit list of individual commands**, run
from a clean extraction of `atlas_registry_v01.zip`. There is no subprocess
orchestrator in the gate. Atlas is read-only; the unit suite and selfcheck run
entirely in process and spawn no subprocesses.

Run each command and confirm it passes on its own:

```
python3 -m compileall -q .
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 selfcheck.py
python3 -O selfcheck.py
python3 -W error::ResourceWarning -m unittest discover -s tests
python3 atlas.py verify --registry registry/atlas_registry.json
sha256sum -c atlas_registry_v01.sha256
python3 verify_release_manifest.py
```

All nine must pass. `verify_release_manifest.py` is a static checker that imports
only `ast`, `os`, and `sys` and launches no subprocesses.

## Manual smoke test (NOT part of the freeze gate)

```
python3 atlas.py verify --registry registry/atlas_registry.json

python3 atlas.py export \
  --registry registry/atlas_registry.json \
  --out /tmp/atlas_export

python3 atlas.py verify-export --export /tmp/atlas_export
```

Expected: `registry_status = REGISTRY_VERIFIED`; export writes
`atlas_registry_copy.json`, `atlas_summary.json`, and `atlas_checksums.txt`;
`verify-export` passes.

## Optional convenience wrapper

Any `release_check.py` / `release_check.sh` present is **optional convenience; not
the authoritative freeze gate**. The list above is authoritative.
