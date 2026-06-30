# Independent Verification Scope

## Purpose

Move 46 builds an independent verifier that checks the Move 45 full-stack component-version freeze package from outside the Project Witness runtime.

## In scope

The independent verifier checks:

- target zip integrity
- duplicate zip entries
- required package files
- `CHECKSUMS.txt` recomputation for the Move 45 package
- `COMPONENT_VERSION_REGISTRY.json` parsing
- copied artifact hashes against the registry
- repaired local demo pack presence and hash
- embedded baseline archive presence
- embedded baseline SHA256 against the registry
- embedded baseline zip integrity
- embedded baseline `.sha256` records against included zips
- required component zip filenames for Moves 1–34 and the Move 30 repair chain
- required documentation markers for Moves 35–39
- obvious forbidden completion or overclaim phrases

## Out of scope

The independent verifier does not:

- run Project Witness runtime workflows
- repair artifacts
- modify frozen components
- perform Move 47
- freeze Local v1 Candidate
- prove truth
- verify external reality
- prove source trust
- sign or externally anchor artifacts
