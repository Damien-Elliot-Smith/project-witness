#!/usr/bin/env python3
"""
Verifier for Move 51 — Termux Run Instructions v0.1

Checks:
- Required files present
- SHA256 in instructions matches known handoff zip SHA256
- No forbidden claims present
- Move 52 not performed
- Final Local v1 Release not claimed
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "TERMUX_RUN_INSTRUCTIONS.md",
    "README.md",
    "RELEASE_GATE.md",
    "CHECKSUMS.txt",
    "tools/verify_termux_run_instructions.py",
]

EXPECTED_HANDOFF_SHA256 = "a84fabe6b7f70254c45986457b569917149d0a3c7310465f15f8b31e2596cfa4"

FORBIDDEN_CLAIMS = [
    "Move 52 is complete",
    "Move 52 has been completed",
    "Final Local v1 Release: frozen",
    "final Local v1 Release is frozen",
    "production-ready",
    "proves truth",
    "verifies external reality",
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


def main():
    # 1. Required files
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        if not p.exists():
            fail(f"missing required file: {rel}")

    # 2. SHA256 of handoff zip is stated correctly in instructions
    instructions = (ROOT / "TERMUX_RUN_INSTRUCTIONS.md").read_text(encoding="utf-8")
    if EXPECTED_HANDOFF_SHA256 not in instructions:
        fail(
            f"TERMUX_RUN_INSTRUCTIONS.md does not contain the expected "
            f"handoff zip SHA256: {EXPECTED_HANDOFF_SHA256}"
        )

    # 3. No forbidden claims in any markdown file
    all_md = "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in ROOT.rglob("*.md")
    )
    for phrase in FORBIDDEN_CLAIMS:
        if phrase.lower() in all_md.lower():
            fail(f"forbidden claim present: {phrase!r}")

    # 4. CHECKSUMS.txt validates
    checksums_text = (ROOT / "CHECKSUMS.txt").read_text(encoding="utf-8")
    expected = {}
    for line in checksums_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            fail(f"bad CHECKSUMS line: {line!r}")
        expected[parts[1].strip()] = parts[0].strip().lower()

    for rel, digest in expected.items():
        p = ROOT / rel
        if not p.exists():
            fail(f"CHECKSUMS lists missing file: {rel}")
        actual = sha256_file(p)
        if actual != digest:
            fail(f"CHECKSUMS hash mismatch: {rel}")

    for p in ROOT.rglob("*"):
        if p.is_file():
            rel = p.relative_to(ROOT).as_posix()
            if rel != "CHECKSUMS.txt" and rel not in expected:
                fail(f"CHECKSUMS missing file: {rel}")

    print("TERMUX_RUN_INSTRUCTIONS_VERIFIED")
    print("verify_ok = true")


if __name__ == "__main__":
    main()
