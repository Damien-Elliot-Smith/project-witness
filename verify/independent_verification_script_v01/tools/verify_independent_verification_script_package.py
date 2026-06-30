#!/usr/bin/env python3
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "README.md",
    "START_HERE.md",
    "INDEPENDENT_VERIFICATION_SCOPE.md",
    "INDEPENDENT_VERIFICATION_ALGORITHM.md",
    "USAGE.md",
    "TEST_RESULTS.md",
    "NEGATIVE_TEST_RESULTS.md",
    "RELEASE_GATE.md",
    "REPAIR_LEDGER.md",
    "MOVE_47_HANDOFF.md",
    "VERIFICATION.md",
    "CHECKSUMS.txt",
    "artifacts/full_stack_component_version_freeze_v01.zip",
    "tools/independent_verify_project_witness.py",
    "tools/verify_independent_verification_script_package.py",
]
REQUIRED_PHRASES = {
    "README.md": ["Move 46", "Build Independent Verification Script", "does not modify"],
    "INDEPENDENT_VERIFICATION_SCOPE.md": ["independent", "Move 45", "outside the Project Witness runtime"],
    "INDEPENDENT_VERIFICATION_ALGORITHM.md": ["CHECKSUMS.txt", "embedded baseline", "does not execute internal verifiers"],
    "USAGE.md": ["independent_verify_project_witness.py", "PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED"],
    "TEST_RESULTS.md": ["PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED", "ResourceWarning"],
    "NEGATIVE_TEST_RESULTS.md": ["negative", "expected failure"],
    "RELEASE_GATE.md": ["PASS criteria", "FAIL criteria", "Move 47 is not performed"],
    "MOVE_47_HANDOFF.md": ["Move 47", "Example Reviewer Walkthrough"],
    "VERIFICATION.md": ["INDEPENDENT_VERIFICATION_SCRIPT_PACKAGE_VERIFIED"],
}
FORBIDDEN = [
    "Move 47 is complete",
    "Local v1 Candidate is frozen",
    "Local v1 Release is frozen",
    "Project Witness proves truth",
    "Project Witness verifies external reality",
    "Project Witness is production-ready",
]

def fail(msg):
    print(f"VERIFY_FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read(rel):
    p=ROOT/rel
    if not p.exists(): fail(f"missing required file: {rel}")
    return p.read_text(encoding='utf-8')

def main():
    for rel in REQUIRED_FILES:
        if not (ROOT/rel).exists(): fail(f"missing required file: {rel}")
    for rel, phrases in REQUIRED_PHRASES.items():
        text=read(rel)
        for phrase in phrases:
            if phrase not in text: fail(f"{rel} missing phrase: {phrase}")
    all_text="\n".join(read(rel) for rel in REQUIRED_FILES if rel.endswith('.md'))
    for phrase in FORBIDDEN:
        if phrase in all_text: fail(f"forbidden phrase present: {phrase}")
    # CHECKSUMS must match all package files except itself.
    expected={}
    for line in read('CHECKSUMS.txt').splitlines():
        if not line.strip(): continue
        parts=line.split(None,1)
        if len(parts)!=2: fail(f"bad CHECKSUMS line: {line}")
        expected[parts[1].strip()]=parts[0].strip().lower()
    actual=[]
    for p in ROOT.rglob('*'):
        if p.is_file():
            rel=p.relative_to(ROOT).as_posix()
            if rel!='CHECKSUMS.txt': actual.append(rel)
    for rel in actual:
        if rel not in expected: fail(f"CHECKSUMS missing file: {rel}")
        if sha256_file(ROOT/rel)!=expected[rel]: fail(f"CHECKSUMS hash mismatch: {rel}")
    for rel in expected:
        if rel not in actual: fail(f"CHECKSUMS lists missing file: {rel}")
    # Run independent verifier against included artifact.
    cmd=[sys.executable, 'tools/independent_verify_project_witness.py', 'artifacts/full_stack_component_version_freeze_v01.zip']
    res=subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=300)
    if res.returncode != 0:
        fail('independent verifier failed against included artifact: ' + res.stderr.strip())
    if 'PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED' not in res.stdout:
        fail('independent verifier success banner missing')
    print('INDEPENDENT_VERIFICATION_SCRIPT_PACKAGE_VERIFIED')
    print('verify_ok = true')
if __name__=='__main__': main()
