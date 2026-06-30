#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import re
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "START_HERE.md",
    "LOCAL_V1_CANDIDATE_FREEZE_RECORD.md",
    "RUN_LOCAL_CANDIDATE.md",
    "VERIFY_LOCAL_CANDIDATE.md",
    "CANDIDATE_ARTIFACT_MANIFEST.md",
    "EXTERNAL_ARTIFACTS_INDEX.md",
    "ROADMAP_STATUS.md",
    "CLAIMS_AND_LIMITS.md",
    "REVIEWER_NOTE.md",
    "DOWNLOAD_SAFE_NOTE.md",
    "RELEASE_GATE.md",
    "TEST_RESULTS.md",
    "REPAIR_LEDGER.md",
    "MOVE_51_HANDOFF.md",
    "VERIFICATION.md",
    "LOCAL_V1_CANDIDATE_REGISTRY.json",
    "CHECKSUMS.txt",
    "tools/verify_local_v1_candidate.py",
]

FORBIDDEN_AFFIRMATIVE_CLAIMS = [
    "Move 51 is complete",
    "Move 51 has been completed",
    "Final Local v1 Release: frozen",
]

def fail(msg):
    print(f"VERIFY_FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def read(rel):
    p = ROOT / rel
    if not p.exists():
        fail(f"missing required file: {rel}")
    return p.read_text(encoding="utf-8")

def validate_baseline_records(baseline_bytes):
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(baseline_bytes)
        tmp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(tmp_path, "r") as z:
            bad = z.testzip()
            if bad is not None:
                fail(f"embedded baseline zip integrity failed: {bad}")
            names = z.namelist()
            zip_entries = [n for n in names if n.lower().endswith(".zip")]
            sha_entries = [n for n in names if n.lower().endswith(".sha256") or n.lower().endswith(".sha256.txt")]
            zip_hashes = {n: sha256_bytes(z.read(n)) for n in zip_entries}
            for sha_name in sha_entries:
                txt = z.read(sha_name).decode("utf-8", errors="replace")
                m = re.search(r"([a-fA-F0-9]{64})", txt)
                if not m:
                    fail(f"baseline sha record missing digest: {sha_name}")
                digest = m.group(1).lower()
                if digest not in set(zip_hashes.values()):
                    fail(f"baseline sha record does not match included zip: {sha_name}")
            if len(zip_entries) < 30:
                fail("embedded baseline has too few component zips")
            if len(sha_entries) < 30:
                fail("embedded baseline has too few checksum records")
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass

def main():
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            fail(f"missing required file: {rel}")

    all_md = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in ROOT.rglob("*.md"))
    for phrase in FORBIDDEN_AFFIRMATIVE_CLAIMS:
        if phrase in all_md:
            fail(f"forbidden affirmative claim present: {phrase}")

    registry = json.loads(read("LOCAL_V1_CANDIDATE_REGISTRY.json"))

    for key, info in registry["included_artifacts"].items():
        p = ROOT / "artifacts" / info["filename"]
        if not p.exists():
            fail(f"missing included artifact: {info['filename']}")
        if sha256_file(p) != info["sha256"]:
            fail(f"included artifact hash mismatch: {info['filename']}")

    demo_name = registry["candidate_runnable_artifact"]["filename"]
    demo_path = ROOT / "artifacts" / demo_name
    with zipfile.ZipFile(demo_path, "r") as z:
        bad = z.testzip()
        if bad is not None:
            fail(f"runnable local demo zip integrity failed: {bad}")
        names = z.namelist()
        if len(names) != len(set(names)):
            fail("runnable local demo has duplicate entries")
        baseline_member = "project_witness_demo/START_HERE/artifacts/frozen_working_projects_baseline.zip"
        if baseline_member not in names:
            fail("runnable local demo missing embedded baseline")
        if "project_witness_demo/START_HERE/README.md" not in names:
            fail("runnable local demo missing START_HERE README")
        if "project_witness_demo/START_HERE/tools/verify_local_demo_pack.py" not in names:
            fail("runnable local demo missing local demo verifier")
        baseline_bytes = z.read(baseline_member)

    baseline_sha = sha256_bytes(baseline_bytes)
    if baseline_sha != registry["candidate_runnable_artifact"]["embedded_baseline_sha256"]:
        fail("embedded baseline SHA256 mismatch against candidate runnable artifact registry")
    if baseline_sha != registry["embedded_baseline"]["sha256"]:
        fail("embedded baseline SHA256 mismatch against embedded_baseline registry")

    validate_baseline_records(baseline_bytes)

    expected = {}
    for line in read("CHECKSUMS.txt").splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            fail(f"bad CHECKSUMS line: {line}")
        expected[parts[1].strip()] = parts[0].strip().lower()

    actual = []
    for p in ROOT.rglob("*"):
        if p.is_file():
            rel = p.relative_to(ROOT).as_posix()
            if rel != "CHECKSUMS.txt":
                actual.append(rel)

    for rel in actual:
        if rel not in expected:
            fail(f"CHECKSUMS missing file: {rel}")
        if sha256_file(ROOT / rel) != expected[rel]:
            fail(f"CHECKSUMS hash mismatch: {rel}")

    for rel in expected:
        if rel not in actual:
            fail(f"CHECKSUMS lists missing file: {rel}")

    print("LOCAL_V1_CANDIDATE_VERIFIED")
    print("verify_ok = true")

if __name__ == "__main__":
    main()
