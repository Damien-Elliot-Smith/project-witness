# tests/helpers.py
# Shared fixtures for Histor-lite tests.
#
# build_stub_sentinel_root() writes a MINIMAL stand-in for the frozen Sentinel
# verifier: a sentinel_core/replay.py exposing replay_from_path(path) that
# returns a ReplayResult-like object whose verdict is driven by the run file's
# "__stub_verdict__" field. This lets us test Histor-lite's import / refuse /
# case logic deterministically for every verdict WITHOUT depending on the real
# frozen Sentinel tree, and without reimplementing Sentinel semantics — the stub
# only stands in for "the frozen verifier returned verdict X". A malformed run
# file makes the stub return FAIL, mirroring the real verifier's load-failure
# behaviour.

import json
import os
import tempfile

_STUB_REPLAY = '''\
# Minimal stand-in for sentinel_core/replay.py (test fixture only).
import json

VERDICT_PASS_STRICT = "PASS_STRICT"
VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS = "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS"
VERDICT_FAIL = "FAIL"
VERDICT_REPLAY_INCOMPATIBLE = "REPLAY_INCOMPATIBLE"
_OK = frozenset({VERDICT_PASS_STRICT, VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS})


class ReplayResult:
    __slots__ = ("ok", "verdict", "report")

    def __init__(self, ok, verdict, report):
        self.ok = ok
        self.verdict = verdict
        self.report = report

    def __iter__(self):
        return iter((self.ok, self.report))

    def __bool__(self):
        return self.ok


def replay_from_path(path, allow_open=False, max_receipts=10000):
    # Mirror the real verifier's load-failure -> FAIL behaviour.
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        return ReplayResult(False, VERDICT_FAIL,
                            "STUB: failed to load run file: %s" % e)
    if "__stub_crash__" in data:
        raise RuntimeError("STUB: injected verifier crash")
    verdict = data.get("__stub_verdict__", VERDICT_PASS_STRICT)
    # ok defaults to "verdict is an accepted PASS", but a run file may override
    # it to model an inconsistent verifier result (verdict says PASS, ok=False).
    ok = data.get("__stub_ok__", verdict in _OK)
    report = "STUB REPLAY\\nREPLAY VERDICT: %s\\n%s\\n" % (verdict, verdict)
    return ReplayResult(ok, verdict, report)
'''


def build_stub_sentinel_root():
    """Create a temp dir that looks like a Sentinel root with a stub verifier.

    Returns the root path. Caller is responsible for cleanup.
    """
    root = tempfile.mkdtemp(prefix="stub_sentinel_")
    pkg = os.path.join(root, "sentinel_core")
    os.makedirs(pkg, exist_ok=True)
    with open(os.path.join(pkg, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("# stub sentinel_core package (test fixture)\n")
    with open(os.path.join(pkg, "replay.py"), "w", encoding="utf-8") as f:
        f.write(_STUB_REPLAY)
    return root


def write_stub_run(path, verdict="PASS_STRICT", crash=False, raw=None, ok=None):
    """Write a stub Sentinel run file selecting a verdict (or malformed if raw).

    If ok is not None, it overrides the stub verifier's ok flag (used to model an
    inconsistent verifier result, e.g. verdict=PASS_STRICT with ok=False).
    """
    if raw is not None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(raw)
        return path
    payload = {"run_id": "stub", "__stub_verdict__": verdict}
    if crash:
        payload["__stub_crash__"] = True
    if ok is not None:
        payload["__stub_ok__"] = ok
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return path
