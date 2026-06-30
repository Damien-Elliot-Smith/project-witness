#!/usr/bin/env python3
"""Independent verifier for Project Witness full-stack component-version freeze packages.

This script is deliberately external to the Project Witness runtime. It uses only the
Python standard library and verifies the Move 45 package by inspecting bytes, hashes,
zip structure, registries, and embedded baseline records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

EXPECTED_ROOT = "full_stack_component_version_freeze_v01/"
EXPECTED_PACKAGE_NAME = "full_stack_component_version_freeze_v01.zip"
EXPECTED_MOVE = 45
EXPECTED_NEXT_MOVE = 46
EXPECTED_OUTPUT = "PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED"

REQUIRED_PACKAGE_FILES = [
    "README.md",
    "START_HERE.md",
    "VERSION_FREEZE_RECORD.md",
    "COMPONENT_VERSION_REGISTRY.md",
    "COMPONENT_VERSION_REGISTRY.json",
    "BASELINE_COMPONENTS.md",
    "STACK_ARTIFACTS.md",
    "MOVE_STATUS.md",
    "CHECKSUM_POLICY.md",
    "ARTIFACT_MANIFEST.md",
    "CLAIMS_AND_LIMITS.md",
    "SCOPE_BOUNDARY.md",
    "RELEASE_GATE.md",
    "VERIFICATION.md",
    "TEST_RESULTS.md",
    "REPAIR_LEDGER.md",
    "MOVE_46_HANDOFF.md",
    "CHECKSUMS.txt",
    "tools/verify_full_stack_component_version_freeze.py",
]

REQUIRED_STACK_ARTIFACT_IDS = {
    "LOCAL_DEMO_PACK_REPAIRED",
    "LOCAL_DEMO_PACK_CLEAN_PRE_REPAIR",
    "RED_TEAM_ROUND_1",
    "BLUE_TEAM_REPAIR_ROUND_1",
    "RED_TEAM_ROUND_2",
    "FULL_STACK_DOCUMENTATION_CLEAN",
    "ROADMAP_CLEAN",
}

REQUIRED_BASELINE_COMPONENT_FILENAMES = {
    "sentinel_core_v022.zip",
    "sentinel_red_blue_pack_v01.zip",
    "histor_lite_v012.zip",
    "case_bundle_v011.zip",
    "coordinator_workflow_v018.zip",
    "companion_cli_v01.zip",
    "project_witness_workflow_red_blue_pack_v01.zip",
    "aletheia_evidence_bundle_v01.zip",
    "odin_claim_reasoner_v01.zip",
    "odin_red_blue_pack_v01.zip",
    "aletheia_odin_bridge_v01.zip",
    "evidence_reasoning_demo_v01.zip",
    "histor_lite_aletheia_importer_v01.zip",
    "histor_lite_odin_importer_v01.zip",
    "case_bundle_v02.zip",
    "coordinator_workflow_v02.zip",
    "companion_cli_v02.zip",
    "atlas_registry_v01.zip",
    "atlas_release_gate_v01.zip",
    "atlas_red_blue_pack_v01.zip",
    "coordinator_workflow_v03.zip",
    "companion_cli_v03.zip",
    "unified_case_manifest_v01.zip",
    "stack_verifier_v01.zip",
    "stack_selfcheck_v01.zip",
    "stack_red_blue_pack_v02.zip",
    "connected_demo_v01.zip",
    "coordinator_workflow_v031.zip",
    "companion_cli_v031.zip",
    "coordinator_workflow_v032.zip",
    "stack_selfcheck_v011.zip",
    "stack_selfcheck_v012.zip",
    "beginner_runbook_v01.zip",
    "one_command_demo_script_v01.zip",
    "demo_output_bundle_v01.zip",
    "architecture_diagram_v01.zip",
}

REQUIRED_DOC_MARKERS = {
    "master_known_limitations_v01",
    "threat_model_v01",
    "external_review_pack_v01",
    "hostile_review_prompt_pack_v01",
    "response_to_review_ledger_v01",
}

FORBIDDEN_COMPLETION_CLAIMS = [
    "Move 46 is complete",
    "Move 47 is complete",
    "Local v1 Candidate is frozen",
    "Local v1 Release is frozen",
    "Project Witness Part One is complete.",
]

FORBIDDEN_OVERCLAIMS = [
    "Project Witness proves truth",
    "Project Witness verifies external reality",
    "Project Witness is production-ready",
    "Project Witness is tamper-proof",
    "signing exists",
    "external anchoring exists",
]

class VerifyError(Exception):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(message: str) -> None:
    raise VerifyError(message)


def check_zip_integrity(path: Path) -> List[str]:
    try:
        with zipfile.ZipFile(path, "r") as z:
            bad = z.testzip()
            if bad is not None:
                fail(f"zip integrity failure at member: {bad}")
            names = z.namelist()
    except zipfile.BadZipFile as exc:
        fail(f"bad zip file: {exc}")
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        fail(f"duplicate zip entries: {duplicates[:10]}")
    return names


def read_member(z: zipfile.ZipFile, name: str) -> bytes:
    try:
        return z.read(name)
    except KeyError:
        fail(f"missing zip member: {name}")


def strip_root(names: Iterable[str]) -> Tuple[str, Dict[str, str]]:
    names = [n for n in names if not n.endswith("/")]
    root_counts = {}
    for n in names:
        root = n.split("/", 1)[0]
        root_counts[root] = root_counts.get(root, 0) + 1
    if len(root_counts) != 1:
        fail(f"expected one package root, found: {sorted(root_counts)}")
    root = next(iter(root_counts)) + "/"
    relmap = {}
    for n in names:
        if not n.startswith(root):
            fail(f"member outside root: {n}")
        relmap[n[len(root):]] = n
    return root, relmap


def parse_checksums(text: str) -> Dict[str, str]:
    expected = {}
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            fail(f"bad CHECKSUMS.txt line {i}: {line!r}")
        digest, rel = parts[0].strip().lower(), parts[1].strip()
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            fail(f"bad sha256 digest in CHECKSUMS.txt line {i}: {digest}")
        if rel in expected:
            fail(f"duplicate CHECKSUMS.txt entry: {rel}")
        expected[rel] = digest
    return expected


def verify_package_checksums(z: zipfile.ZipFile, relmap: Dict[str, str]) -> None:
    checksum_member = relmap.get("CHECKSUMS.txt")
    if not checksum_member:
        fail("missing CHECKSUMS.txt")
    expected = parse_checksums(read_member(z, checksum_member).decode("utf-8", errors="replace"))
    actual_files = sorted(rel for rel in relmap if rel != "CHECKSUMS.txt")
    for rel in actual_files:
        if rel not in expected:
            fail(f"CHECKSUMS.txt missing entry for {rel}")
        actual = sha256_bytes(read_member(z, relmap[rel]))
        if actual != expected[rel]:
            fail(f"CHECKSUMS.txt hash mismatch for {rel}")
    for rel in expected:
        if rel not in actual_files:
            fail(f"CHECKSUMS.txt lists missing file: {rel}")


def validate_baseline_sha_records(baseline_bytes: bytes) -> Tuple[int, int, int]:
    with tempfile.TemporaryDirectory(prefix="pw_independent_baseline_") as tmpdir:
        tmp = Path(tmpdir) / "baseline.zip"
        tmp.write_bytes(baseline_bytes)
        names = check_zip_integrity(tmp)
        with zipfile.ZipFile(tmp, "r") as z:
            zip_entries = [n for n in names if n.lower().endswith(".zip")]
            sha_entries = [n for n in names if n.lower().endswith(".sha256") or n.lower().endswith(".sha256.txt")]
            zip_hashes = {n: sha256_bytes(z.read(n)) for n in zip_entries}
            zip_hash_values = set(zip_hashes.values())
            passed = 0
            for sha_name in sha_entries:
                text = z.read(sha_name).decode("utf-8", errors="replace")
                m = re.search(r"([a-fA-F0-9]{64})", text)
                if not m:
                    fail(f"baseline checksum record has no sha256 digest: {sha_name}")
                expected = m.group(1).lower()
                if expected not in zip_hash_values:
                    fail(f"baseline checksum record does not match any included zip: {sha_name}")
                passed += 1
            # Required baseline component filenames.
            filenames = {Path(n).name for n in zip_entries}
            missing = sorted(REQUIRED_BASELINE_COMPONENT_FILENAMES - filenames)
            if missing:
                fail(f"embedded baseline missing required component zips: {missing}")
            # Required doc markers for Moves 35-39.
            joined = "\n".join(names)
            missing_markers = sorted(m for m in REQUIRED_DOC_MARKERS if m not in joined)
            if missing_markers:
                fail(f"embedded baseline missing required documentation markers: {missing_markers}")
            return len(zip_entries), len(sha_entries), passed


def scan_forbidden_claims(z: zipfile.ZipFile, relmap: Dict[str, str]) -> None:
    text_blob_parts = []
    for rel, member in relmap.items():
        if rel.lower().endswith((".md", ".txt", ".json")):
            try:
                text_blob_parts.append(read_member(z, member).decode("utf-8", errors="replace"))
            except Exception:
                pass
    text_blob = "\n".join(text_blob_parts)
    for phrase in FORBIDDEN_COMPLETION_CLAIMS + FORBIDDEN_OVERCLAIMS:
        if phrase in text_blob:
            fail(f"forbidden claim found: {phrase}")


def verify(target: Path) -> Dict[str, object]:
    if not target.exists():
        fail(f"target file does not exist: {target}")
    names = check_zip_integrity(target)
    root, relmap = strip_root(names)

    for rel in REQUIRED_PACKAGE_FILES:
        if rel not in relmap:
            fail(f"missing required package file: {rel}")

    verify_package_checksums(zipfile.ZipFile(target, "r"), relmap)

    with zipfile.ZipFile(target, "r") as z:
        scan_forbidden_claims(z, relmap)
        registry = json.loads(read_member(z, relmap["COMPONENT_VERSION_REGISTRY.json"]).decode("utf-8"))

        if registry.get("roadmap_move") != EXPECTED_MOVE:
            fail(f"registry roadmap_move is not {EXPECTED_MOVE}")
        if "Move 46" not in registry.get("limits", [""])[4] and not any("Move 46" in x for x in registry.get("limits", [])):
            fail("registry limits do not mention Move 46 boundary")

        stack_artifacts = registry.get("stack_artifacts", [])
        artifact_ids = {rec.get("artifact_id") for rec in stack_artifacts}
        missing_ids = sorted(REQUIRED_STACK_ARTIFACT_IDS - artifact_ids)
        if missing_ids:
            fail(f"registry missing stack artifact IDs: {missing_ids}")

        artifact_members = {rel for rel in relmap if rel.startswith("artifacts/") and not rel.endswith("/")}
        expected_artifact_members = {"artifacts/" + rec["filename"] for rec in stack_artifacts}
        extra_artifacts = sorted(artifact_members - expected_artifact_members)
        missing_artifacts = sorted(expected_artifact_members - artifact_members)
        if extra_artifacts:
            fail(f"unlisted artifacts present: {extra_artifacts}")
        if missing_artifacts:
            fail(f"listed artifacts missing: {missing_artifacts}")

        repaired_filename = None
        for rec in stack_artifacts:
            member_rel = "artifacts/" + rec["filename"]
            data = read_member(z, relmap[member_rel])
            actual = sha256_bytes(data)
            if actual != rec["sha256"]:
                fail(f"artifact hash mismatch for {member_rel}")
            if rec.get("artifact_id") == "LOCAL_DEMO_PACK_REPAIRED":
                repaired_filename = rec["filename"]
                repaired_bytes = data
        if not repaired_filename:
            fail("missing LOCAL_DEMO_PACK_REPAIRED record")

    # Inspect repaired local demo pack.
    with tempfile.TemporaryDirectory(prefix="pw_independent_repaired_") as tmpdir:
        repaired_path = Path(tmpdir) / repaired_filename
        repaired_path.write_bytes(repaired_bytes)
        repaired_names = check_zip_integrity(repaired_path)
        with zipfile.ZipFile(repaired_path, "r") as rz:
            baseline_member = "project_witness_demo/START_HERE/artifacts/frozen_working_projects_baseline.zip"
            if baseline_member not in repaired_names:
                fail("repaired local demo pack missing embedded baseline")
            baseline_bytes = rz.read(baseline_member)
            baseline_sha = sha256_bytes(baseline_bytes)

    expected_baseline_sha = registry["baseline_archive"]["sha256"]
    if baseline_sha != expected_baseline_sha:
        fail("embedded baseline sha256 does not match registry")

    zip_count, sha_record_count, sha_passed = validate_baseline_sha_records(baseline_bytes)
    expected_zip_count = registry["baseline_archive"].get("component_zip_count")
    expected_sha_count = registry["baseline_archive"].get("sha_record_count")
    if zip_count != expected_zip_count:
        fail(f"baseline component zip count mismatch: {zip_count} != {expected_zip_count}")
    if sha_record_count != expected_sha_count:
        fail(f"baseline sha record count mismatch: {sha_record_count} != {expected_sha_count}")
    if sha_passed != sha_record_count:
        fail("not all baseline sha records passed")

    return {
        "target": str(target),
        "target_sha256": sha256_file(target),
        "package_root": root,
        "artifact_count": len(REQUIRED_STACK_ARTIFACT_IDS),
        "baseline_sha256": baseline_sha,
        "baseline_component_zip_count": zip_count,
        "baseline_sha_record_count": sha_record_count,
        "baseline_sha_records_passed": sha_passed,
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Independently verify a Project Witness Move 45 full-stack version freeze package.")
    parser.add_argument("target", help="Path to full_stack_component_version_freeze_v01.zip")
    parser.add_argument("--json", action="store_true", help="print verification summary as JSON after success banner")
    args = parser.parse_args(argv)

    try:
        summary = verify(Path(args.target))
    except VerifyError as exc:
        print(f"INDEPENDENT_VERIFY_FAIL: {exc}", file=sys.stderr)
        return 1

    print(EXPECTED_OUTPUT)
    print("verify_ok = true")
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
