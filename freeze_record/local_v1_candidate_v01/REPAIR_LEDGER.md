# Repair Ledger — Local v1 Candidate v0.1

## Boundary

This repair ledger is for the Move 50 candidate package itself.

No frozen Project Witness runtime artifact was modified.

## Package construction repairs

| Repair ID | Issue | Fix | Scope impact | Status |
|---|---|---|---|---|
| MV50-PKG-001 | Full recursive artifact nesting would likely recreate the app download failure seen at Move 49. | Built a download-safe candidate package that includes the runnable local demo pack and records large historical artifacts by checksum. | Packaging only. No runtime change. | CLOSED |
| MV50-PKG-002 | Initial verifier wording was too broad and treated a warning about final release as a final-release claim. | Rebuilt verifier to block only affirmative current-status claims, while allowing warning text. | Verifier-only. No runtime change. | CLOSED |

## Final status

No open package repairs.
