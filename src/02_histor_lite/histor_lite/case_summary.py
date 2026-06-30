# histor_lite/case_summary.py
# Build a case summary dict and verify a written case folder's integrity.

import datetime
import os

from histor_lite.canonical import canonical_json, canonical_bytes, sha256_hex, hash_file
from histor_lite.errors import require, CaseError
from histor_lite import versions

CASE_SUMMARY_NAME = "case_summary.json"
REPLAY_REPORT_NAME = "sentinel_replay_report.txt"
CHECKSUMS_NAME = "checksums.txt"

_HEX_DIGITS = set("0123456789abcdef")


def _is_sha256_hex(value) -> bool:
    """True if value is a 64-character lowercase hex SHA-256 digest."""
    return (isinstance(value, str) and len(value) == 64
            and all(c in _HEX_DIGITS for c in value))


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 'Z' string (second precision)."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def case_id_for(source_run_sha256: str) -> str:
    """Deterministic case id derived from the run hash (stable per run)."""
    return "case_" + source_run_sha256[:16]


def build_case_summary(*, source_run_path, source_run_sha256, verdict, ok,
                       import_status, verified_at_utc):
    """Assemble the case_summary dict. Pure: no IO, fully determined by inputs.

    The Sentinel verdict is preserved EXACTLY; a PASS_WITH_ENVIRONMENTAL_EXCEPTIONS
    is never relabelled as strict.
    """
    return {
        "histor_lite_version": versions.HISTOR_LITE_VERSION,
        "case_id": case_id_for(source_run_sha256),
        "source_component": versions.SOURCE_COMPONENT,
        "source_component_version": versions.SOURCE_COMPONENT_VERSION,
        "source_run_path": source_run_path,
        "source_run_sha256": source_run_sha256,
        "sentinel_replay_verdict": verdict,
        "sentinel_replay_ok": ok,
        "import_status": import_status,
        "verified_at_utc": verified_at_utc,
        "known_limitations": list(versions.KNOWN_LIMITATIONS),
    }


def render_checksums(*, source_run_sha256, source_run_label,
                     case_summary_sha256, replay_report_sha256) -> str:
    """Render checksums.txt. Two-column 'hash  label' lines, trailing newline."""
    lines = [
        f"source_run_sha256  {source_run_sha256}  {source_run_label}",
        f"case_summary_sha256  {case_summary_sha256}  {CASE_SUMMARY_NAME}",
        f"sentinel_replay_report_sha256  {replay_report_sha256}  {REPLAY_REPORT_NAME}",
    ]
    return "\n".join(lines) + "\n"


def parse_checksums(text: str) -> dict:
    """Parse checksums.txt into {key: (hash, label)}.

    Rejects duplicate keys: a duplicated checksum line (e.g. a bogus
    source_run_sha256 followed by the correct one) must not be silently resolved
    by a "last line wins" rule, which would let a tampered line hide behind a
    correct one. Each recognised key must appear exactly once.
    """
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        require(len(parts) >= 2, f"Malformed checksum line: {raw!r}", CaseError)
        key, digest = parts[0], parts[1]
        require(key not in out, f"Duplicate checksum key in checksums.txt: {key!r}",
                CaseError)
        label = parts[2] if len(parts) >= 3 else ""
        out[key] = (digest, label)
    return out


def verify_case(case_dir: str) -> dict:
    """Verify a case output folder's internal integrity.

    Recomputes the SHA-256 of case_summary.json and sentinel_replay_report.txt
    and compares them against checksums.txt. Detects a mutated case_summary.json
    (or replay report). Returns a small result dict on success; raises CaseError
    on any problem.

    This is a structural integrity check of the CASE folder only. It does NOT
    re-run the Sentinel verifier (the Sentinel root may be unavailable) and does
    not re-prove Sentinel semantics.
    """
    require(os.path.isdir(case_dir), f"Case folder not found: {case_dir!r}", CaseError)
    summary_path = os.path.join(case_dir, CASE_SUMMARY_NAME)
    report_path = os.path.join(case_dir, REPLAY_REPORT_NAME)
    checksums_path = os.path.join(case_dir, CHECKSUMS_NAME)
    for p, name in [(summary_path, CASE_SUMMARY_NAME),
                    (report_path, REPLAY_REPORT_NAME),
                    (checksums_path, CHECKSUMS_NAME)]:
        require(os.path.isfile(p), f"Case folder missing {name}", CaseError)

    with open(checksums_path, encoding="utf-8") as f:
        recorded = parse_checksums(f.read())
    require("source_run_sha256" in recorded,
            "checksums.txt missing source_run_sha256", CaseError)
    require("case_summary_sha256" in recorded,
            "checksums.txt missing case_summary_sha256", CaseError)
    require("sentinel_replay_report_sha256" in recorded,
            "checksums.txt missing sentinel_replay_report_sha256", CaseError)

    # Parse the summary first; we need its source_run_sha256 to cross-check, and
    # we validate canonical form below.
    import json
    with open(summary_path, "rb") as f:
        raw = f.read()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise CaseError(f"{CASE_SUMMARY_NAME} is not valid JSON: {e}")

    # The source run file is NOT copied into the case folder, so we cannot rehash
    # the original. But the recorded source_run_sha256 metadata must be a
    # well-formed digest AND must match the value embedded in the case summary.
    # Otherwise the checksums.txt provenance line could be altered undetected.
    recorded_src = recorded["source_run_sha256"][0]
    require(_is_sha256_hex(recorded_src),
            f"checksums.txt source_run_sha256 is not a valid SHA-256 digest: "
            f"{recorded_src!r}", CaseError)
    summary_src = parsed.get("source_run_sha256")
    require(isinstance(summary_src, str) and _is_sha256_hex(summary_src),
            f"{CASE_SUMMARY_NAME} source_run_sha256 is missing or malformed",
            CaseError)
    require(recorded_src == summary_src,
            f"source_run_sha256 mismatch: checksums.txt {recorded_src} != "
            f"{CASE_SUMMARY_NAME} {summary_src}", CaseError)

    actual_summary = hash_file(summary_path)
    actual_report = hash_file(report_path)
    expected_summary = recorded["case_summary_sha256"][0]
    expected_report = recorded["sentinel_replay_report_sha256"][0]

    require(actual_summary == expected_summary,
            f"{CASE_SUMMARY_NAME} has been modified: recorded {expected_summary}, "
            f"actual {actual_summary}", CaseError)
    require(actual_report == expected_report,
            f"{REPLAY_REPORT_NAME} has been modified: recorded {expected_report}, "
            f"actual {actual_report}", CaseError)

    # The summary must be in canonical form (catches whitespace/key-order tamper
    # that a recomputed case_summary_sha256 would otherwise hide).
    require(canonical_bytes(parsed) == raw,
            f"{CASE_SUMMARY_NAME} is not in canonical form (possible tamper)", CaseError)

    return {
        "case_dir": case_dir,
        "case_id": parsed.get("case_id"),
        "sentinel_replay_verdict": parsed.get("sentinel_replay_verdict"),
        "import_status": parsed.get("import_status"),
        "integrity": "OK",
    }
