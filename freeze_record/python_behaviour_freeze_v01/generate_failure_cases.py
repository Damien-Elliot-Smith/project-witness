"""Move 71 failure-case generator.

Applies one documented tamper per case to a fresh copy of the frozen
reference bundle. Each case is a behavioural fixture: the frozen Python
stack's verdict on it (recorded in expected_failures.json) is part of the
behavioural reference that any future verifier (including the planned
Part Two Rust verifier) must reproduce.

Stdlib only. Deterministic: the same reference bundle always yields the
same tampered trees.
"""

import json
import os
import shutil

EVIDENCE = os.path.join("coordinator_output", "aletheia_bundle",
                        "evidence", "evidence_001.bin")
EVIDENCE_SUMS = os.path.join("coordinator_output", "aletheia_bundle",
                             "evidence_checksums.txt")
SOURCE_RUN = os.path.join("coordinator_output", "sentinel_run",
                          "sentinel_run.json")
NESTED_LISTED = os.path.join("coordinator_output", "bridge_output",
                             "odin_claims.json")
TOP_REPORT = "companion_report.json"
TOP_CHECKSUMS = "companion_checksums.txt"
WORKFLOW_REPORT = os.path.join("coordinator_output", "workflow_report.json")


def _flip_byte(path, offset=5):
    with open(path, "rb") as handle:
        data = bytearray(handle.read())
    data[offset] = data[offset] ^ 0xFF
    with open(path, "wb") as handle:
        handle.write(bytes(data))


def _sha256_file(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def case_clean_control(root):
    """No tamper. The frozen stack must accept this."""


def case_evidence_byte_flip(root):
    """Flip one byte of the bundled evidence file."""
    _flip_byte(os.path.join(root, EVIDENCE))


def case_evidence_flip_with_checksum_fixup(root):
    """Flip evidence AND rewrite its nested checksum entry to match."""
    target = os.path.join(root, EVIDENCE)
    _flip_byte(target)
    new_digest = _sha256_file(target)
    sums_path = os.path.join(root, EVIDENCE_SUMS)
    with open(sums_path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    out = []
    for line in lines:
        if line.endswith("evidence/evidence_001.bin"):
            out.append("%s  evidence/evidence_001.bin" % new_digest)
        else:
            out.append(line)
    with open(sums_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")


def case_delete_nested_listed_file(root):
    """Delete a file listed only in a nested checksum file."""
    os.remove(os.path.join(root, NESTED_LISTED))


def case_tamper_top_level_report(root):
    """Append a byte to a top-level required file."""
    with open(os.path.join(root, TOP_REPORT), "ab") as handle:
        handle.write(b" ")


def case_delete_top_level_checksums(root):
    """Remove the top-level checksum file entirely."""
    os.remove(os.path.join(root, TOP_CHECKSUMS))


def case_unknown_top_level_entry(root):
    """Add a stray file at the output top level."""
    with open(os.path.join(root, "stray.txt"), "wb") as handle:
        handle.write(b"stray\n")


def case_tamper_source_run(root):
    """Append a byte to the Sentinel source run record."""
    with open(os.path.join(root, SOURCE_RUN), "ab") as handle:
        handle.write(b" ")


def case_malformed_report_json(root):
    """Truncate a required JSON file so it no longer parses."""
    path = os.path.join(root, WORKFLOW_REPORT)
    with open(path, "rb") as handle:
        data = handle.read()
    with open(path, "wb") as handle:
        handle.write(data[: len(data) // 2])


def case_evidence_added_unexpectedly(root):
    """Plant an unlisted file in the evidence directory."""
    target = os.path.join(root, os.path.dirname(EVIDENCE),
                          "planted_evidence.bin")
    with open(target, "wb") as handle:
        handle.write(b"planted\n")


CASES = (
    ("clean_control", case_clean_control),
    ("evidence_byte_flip", case_evidence_byte_flip),
    ("evidence_flip_with_checksum_fixup",
     case_evidence_flip_with_checksum_fixup),
    ("evidence_added_unexpectedly", case_evidence_added_unexpectedly),
    ("delete_nested_listed_file", case_delete_nested_listed_file),
    ("tamper_top_level_report", case_tamper_top_level_report),
    ("delete_top_level_checksums", case_delete_top_level_checksums),
    ("unknown_top_level_entry", case_unknown_top_level_entry),
    ("tamper_source_run", case_tamper_source_run),
    ("malformed_report_json", case_malformed_report_json),
)


def generate(reference_bundle, dest_root):
    """Build every tampered tree under dest_root. Returns list of names."""
    names = []
    for name, apply_tamper in CASES:
        target = os.path.join(dest_root, name)
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.copytree(reference_bundle, target)
        apply_tamper(target)
        names.append(name)
    return names


if __name__ == "__main__":
    import sys
    ref = sys.argv[1]
    dest = sys.argv[2]
    for built in generate(ref, dest):
        print("built:", built)
