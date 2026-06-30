# Known limitations — Histor-lite v0.1.2

Histor-lite v0.1.2 is a deliberately narrow importer/verifier. It is a prototype
stack component, not a production ledger. The following limitations are explicit
and accepted for this milestone.

## H1 — No signing
Histor-lite does not sign the case summary, the replay report, or anything else.
The checksums it writes are unkeyed SHA-256 over the files it produced. They
detect accidental or casual modification of a case folder, but a local actor who
can run this code can rewrite a case folder and its `checksums.txt` so that it is
internally consistent. Detecting that requires cryptographic signing, which is
out of scope for v0.1.

## H2 — No external anchoring
Histor-lite does not anchor any hash to an external trusted log, timestamp
authority, or notary. There is no protection against a fully reconstructed case
folder; `verify-case` only proves internal consistency of the folder as written.

## H3 — It trusts the frozen Sentinel verifier for Sentinel semantics
Histor-lite does NOT reimplement Sentinel's replay logic. It locates the frozen
Sentinel verifier at `--sentinel-root` and trusts its verdict
(`PASS_STRICT` / `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS` / `FAIL` /
`REPLAY_INCOMPATIBLE`). If the verifier at that root is wrong, compromised, or not
the audited v0.2.2 build, Histor-lite's verdict inherits that. Verify the Sentinel
checksum (`23381adf...`) before importing if provenance matters. Histor-lite's job
is to invoke that verifier honestly and preserve its verdict exactly — not to
second-guess Sentinel.

## H4 — Sentinel's own disclosed limitations carry through
Because Histor-lite trusts the Sentinel verdict, Sentinel's documented limits
apply to every imported case and are recorded verbatim in `case_summary.json`:
- Sentinel hashes are **unkeyed**; whole-file fabrication of a Sentinel run
  requires signing or anchoring to detect. A fabricated-but-internally-consistent
  Sentinel run can replay as a PASS and therefore import.
- **Environmental ERROR** receipts may be **structurally verified rather than
  strictly reproduced**; such a run replays as `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS`,
  which Histor-lite preserves exactly (it never relabels it as strict).

## H5 — Sentinel import only
Histor-lite v0.1.2 imports Sentinel Core v0.2.2 runs only. It does **not** import
Aletheia, ODIN, Atlas, or Companion records. Those are out of scope for this
milestone.

## H6 — One action, one component, one run at a time
It reflects Sentinel v0.2.2's single supported action (`CREATE_DIRECTORY`). It
imports one run into one case folder per invocation; it does not aggregate,
chain, or cross-link cases. That is full Histor's job, not this milestone's.

## H7 — Not a production ledger / not production security
This is a prototype seam between Sentinel and the wider Project Witness stack. It
must not be relied on as a tamper-proof record or a security boundary.
