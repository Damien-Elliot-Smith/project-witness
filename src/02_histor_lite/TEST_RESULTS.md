# Test results — Histor-lite v0.1.2

v0.1.2 is a narrow hardening + version-string cleanup of v0.1.1. No new features.
Standard library only. All commands below were run from a **clean extraction** of
`histor_lite_v012.zip`.

## The two findings and their fixes

**Issue 1 (integrity ambiguity) — duplicate checksum keys.** `checksums.txt` was
parsed "last line wins", so a bogus `source_run_sha256` line followed by the
correct one still verified OK. Fix: `parse_checksums` rejects any duplicate key
(each recognised key must appear exactly once), for all three checksum keys. All
existing checks remain.

**Issue 2 (stale wording) — release_check identity strings.** `release_check.py`
still said "Histor-lite v0.1" and hinted at `histor_lite_v01.sha256`. Current
identity is now v0.1.2 and the checksum hint is `histor_lite_v012.sha256`; a
tree-wide sweep bumped the remaining current-identity strings to v0.1.2.
Historical v0.1.0 / v0.1.1 references in the repair ledger are kept as history.

## Acceptance — all pass from a clean extraction

| Command | Result |
|---------|--------|
| `python3 -m compileall -q .` | PASS |
| `python3 -m unittest discover -s tests -v` | PASS — 37 tests (1 skipped: optional real-Sentinel integration) |
| `python3 -O -m unittest discover -s tests -v` | PASS — 37 tests |
| `python3 selfcheck.py` | PASS — 8/8 gates |
| `python3 -O selfcheck.py` | PASS — 8/8 gates |
| `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS |
| `python3 release_check.py` | PASS — 7/7 steps |
| `sha256sum -c histor_lite_v012.sha256` | OK |

## New tests (37 total, was 33)

`test_case_summary.py`:
- duplicate `source_run_sha256` fails;
- duplicate `case_summary_sha256` fails;
- duplicate `sentinel_replay_report_sha256` fails;
- the exact bogus-then-correct duplicate `source_run_sha256` attack fails.

Regression guards retained: valid case still verifies; `source_run_sha256`
value/missing/malformed still fail; case-summary-hash and replay-report-hash
tamper still fail; non-canonical summary still fails.

## Preserved guarantees

Sentinel verifier invoked in-process; exact Sentinel verdict preserved;
`PASS_WITH_ENVIRONMENTAL_EXCEPTIONS` never relabelled as strict; `PASS_STRICT +
ok=false` and `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS + ok=false` refused; `FAIL` and
`REPLAY_INCOMPATIBLE` refused; `source_run_sha256` in `checksums.txt` checked
against `case_summary.json`; no bare runtime asserts; selfcheck does not launch
the unit suite; `release_check.py` remains the external timed orchestrator;
standard library only. The optional real-Sentinel integration test still passes
against the frozen `sentinel_core_v022` build (sha `23381adf...`).

## Scope

Parser hardening + version-string cleanup only. No new features, no signing, no
external anchoring, no Aletheia/ODIN/Atlas/Companion import, no GUI, no LLM
integration, no change to Sentinel. `HISTOR_LITE_VERSION` -> 0.1.2.
