"""Move 71 verifier — Python behaviour freeze.

Checks, from a fresh extraction, that the frozen behavioural reference
still holds:

 1. reference bundle integrity: every file matches the frozen hash
    manifest, no files are missing, no extra files are present
 2. reference bundle verdict: `companion verify` accepts it
 3. failure corpus: every tampered variant is regenerated from the
    reference bundle and the frozen stack's verdict (verify_ok, exit
    code, error text prefix) matches the recorded expectation exactly
 4. reason-code vocabulary: re-extraction from src/ matches the frozen
    registry byte-for-byte (drift in either direction fails)
 5. nondeterminism registry and expected-results records are present
    and parse

Run from the stack root:

    python3 freeze_record/python_behaviour_freeze_v01/verify_move_71.py

Stdlib only. Read-only against src/; writes only to a temp directory.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REF = os.path.join(HERE, "reference_bundle")
HASHES = os.path.join(HERE, "reference_bundle_hashes.sha256")
COMPANION = os.path.join(ROOT, "src", "12_companion_cli_v031", "companion.py")

_results = []


def check(name, ok, detail=""):
    _results.append((name, bool(ok), detail))
    marker = "PASS" if ok else "FAIL"
    line = " [%s] %s" % (marker, name)
    if detail and not ok:
        line += " — %s" % detail
    print(line)
    return bool(ok)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def companion_verify(run_dir):
    proc = subprocess.run(
        [sys.executable, COMPANION, "verify", "--run", run_dir],
        capture_output=True, text=True, cwd=ROOT)
    try:
        out = json.loads(proc.stdout.strip())
    except ValueError:
        out = {}
    return proc.returncode, out


def check_reference_hashes():
    listed = {}
    with open(HASHES, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.strip() == "":
                continue
            digest, rel = line.split("  ", 1)
            listed[os.path.normpath(rel)] = digest
    actual = {}
    for root, dirs, files in os.walk(REF):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(root, name)
            rel = os.path.normpath(os.path.relpath(path, REF))
            actual[rel] = sha256_file(path)
    missing = sorted(set(listed) - set(actual))
    extra = sorted(set(actual) - set(listed))
    mismatched = sorted(r for r in listed
                        if r in actual and actual[r] != listed[r])
    check("reference bundle: no listed file missing", not missing,
          "missing: %s" % missing[:3])
    check("reference bundle: no extra file present", not extra,
          "extra: %s" % extra[:3])
    check("reference bundle: all %d hashes match" % len(listed),
          not mismatched, "mismatched: %s" % mismatched[:3])


def check_reference_verdict():
    code, out = companion_verify(REF)
    check("reference bundle: companion verify accepts",
          code == 0 and out.get("verify_ok") is True,
          "exit=%s out=%s" % (code, out))


def check_failure_corpus():
    sys.path.insert(0, HERE)
    import generate_failure_cases as gen
    expected = load_json(os.path.join(HERE, "expected_failures.json"))
    by_name = {c["case"]: c for c in expected["cases"]}
    generated = set()
    tmp = tempfile.mkdtemp(prefix="move71_cases_")
    try:
        for name in gen.generate(REF, tmp):
            generated.add(name)
            exp = by_name.get(name)
            if not check("failure corpus: %s has a recorded expectation"
                         % name, exp is not None):
                continue
            code, out = companion_verify(os.path.join(tmp, name))
            ok = (code == exp["exit_code"]
                  and out.get("verify_ok") == exp["verify_ok"])
            exp_err = exp.get("error", "")
            got_err = out.get("error", out.get("reason", ""))
            if exp_err:
                ok = ok and got_err[:40] == exp_err[:40]
            check("failure corpus: %s verdict matches record" % name, ok,
                  "expected exit=%s ok=%s err=%r / got exit=%s ok=%s err=%r"
                  % (exp["exit_code"], exp["verify_ok"], exp_err[:40],
                     code, out.get("verify_ok"), got_err[:40]))
        unreplayed = sorted(set(by_name) - generated)
        check("failure corpus: every recorded case was replayed",
              not unreplayed, "not replayed: %s" % unreplayed)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_reason_codes():
    sys.path.insert(0, HERE)
    import extract_reason_codes as extractor
    frozen = load_json(os.path.join(HERE, "reason_code_registry.json"))
    current = extractor.extract(os.path.join(ROOT, "src"))
    check("reason codes: vocabulary matches frozen registry",
          current == frozen["components"],
          "components differing: %s" % sorted(
              set(k for k in set(frozen["components"]) | set(current)
                  if frozen["components"].get(k) != current.get(k)))[:5])


def check_records_parse():
    for rel in ("nondeterminism_registry.json", "expected_results.json"):
        path = os.path.join(HERE, rel)
        ok = os.path.isfile(path)
        if ok:
            try:
                load_json(path)
            except ValueError:
                ok = False
        check("record present and parses: %s" % rel, ok)


def main():
    print("Move 71 verifier — Python behaviour freeze")
    print("=" * 62)
    check_reference_hashes()
    check_reference_verdict()
    check_failure_corpus()
    check_reason_codes()
    check_records_parse()
    print("=" * 62)
    failed = [name for name, ok, _ in _results if not ok]
    if failed:
        print("MOVE_71_PYTHON_BEHAVIOUR_FREEZE_NOT_VERIFIED")
        print("verify_ok = false")
        return 1
    print("MOVE_71_PYTHON_BEHAVIOUR_FREEZE_VERIFIED")
    print("verify_ok = true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
