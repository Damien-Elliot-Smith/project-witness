# Independent Verification Algorithm

The independent verifier uses only Python standard library modules.

## Algorithm

1. Open the target Move 45 zip.
2. Check zip integrity and duplicate entries.
3. Confirm there is a single package root.
4. Confirm all required Move 45 files exist.
5. Parse and recompute `CHECKSUMS.txt` for every package file except `CHECKSUMS.txt` itself.
6. Parse `COMPONENT_VERSION_REGISTRY.json`.
7. Confirm required stack artifact IDs are present.
8. Recompute every artifact hash in `artifacts/` and compare with the registry.
9. Inspect the repaired local demo pack as bytes.
10. Confirm the embedded `frozen_working_projects_baseline.zip` exists.
11. Recompute the embedded baseline hash and compare with the registry.
12. Inspect the embedded baseline zip.
13. Validate all baseline `.sha256` records against included baseline zip artifacts.
14. Confirm required baseline component filenames are present.
15. Confirm Moves 35–39 documentation markers are present.
16. Scan for forbidden completion and overclaim phrases.
17. Print a deterministic success banner.

## Independence boundary

The script does not execute internal verifiers. It also does not execute internal Project Witness verifiers.

It does not import Project Witness modules.

It does not depend on Sentinel, Histor-lite, Case Bundle, Coordinator, Companion, Aletheia, ODIN, Atlas, Stack Verifier, or Stack Selfcheck.
