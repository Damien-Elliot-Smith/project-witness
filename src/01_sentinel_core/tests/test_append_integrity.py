# tests/test_append_integrity.py
# v0.1.2 release-blocker repair tests: load-time integrity for append.
#
# Attack 1 (v0.1.1): close a run, delete its run_seal, append again — accepted,
# and a real directory was created despite the CLOSED_BY_OPERATOR receipt.
# Attack 2 (v0.1.1): delete a receipt from an open run, append — accepted onto
# a structurally invalid chain, producing duplicate IDs and broken linkage.
# In both cases replay failed LATER, but the filesystem side effect had
# already happened.
#
# The repair: open_run_for_append validates manifest, every receipt hash, full
# chain structure, and closure (a close receipt refuses append REGARDLESS of
# seal presence) BEFORE any kernel exists. These tests prove each rejection,
# prove no filesystem side effect occurs, and prove the valid paths and replay
# behaviour are unchanged. CLI subprocess tests reproduce both attacks
# end-to-end exactly as reported.

import contextlib
import hashlib
import io
import json
import os
import shutil
import unittest

from sentinel_core.errors import (
    ChainVerificationError, ManifestError, SessionClosedError, SentinelError,
)
from sentinel_core.replay import replay_from_path
from sentinel_core.run_loader import open_run_for_append
from sentinel_core.run_seal import RUN_SEAL_FIELD
from tests.helpers import make_request, new_kernel, temp_root, temp_runs

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _CliResult:
    """Mimics the subset of subprocess.CompletedProcess the tests use."""
    __slots__ = ("returncode", "stdout", "stderr")

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run_cli(argv):
    """Invoke the Sentinel CLI IN-PROCESS and return a _CliResult.

    v0.2.1: the CLI tests no longer spawn `python sentinel.py` as a subprocess.
    Spawning under capture_output could leave an inherited pipe or child process
    holding the interpreter open at shutdown, which intermittently hung the unit
    suite. Calling sentinel.main() directly removes every subprocess, pipe, and
    child from the test suite. main() returns an int for handled errors and
    raises SystemExit for argparse/refusal exits; we normalise both to a code,
    and capture stdout/stderr via redirection.
    """
    import sentinel
    out, err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = sentinel.main(list(argv))
        code = 0 if rc is None else int(rc)
    except SystemExit as e:  # argparse errors / explicit raises in cmd_*
        if e.code is None:
            code = 0
        elif isinstance(e.code, int):
            code = e.code
        else:
            code = 1  # a string message -> non-zero
            err.write(str(e.code))
    return _CliResult(code, out.getvalue(), err.getvalue())


class _Base(unittest.TestCase):
    def setUp(self):
        self.root = temp_root()
        self.runs = temp_runs()
        self.run_path = os.path.join(self.runs, "r.json")

    def tearDown(self):
        for d in (self.root, self.runs):
            shutil.rmtree(d, ignore_errors=True)

    def _build_run(self, n_creates=2, close=False):
        kernel, run_path = new_kernel("r", self.root, self.runs)
        for i in range(n_creates):
            kernel.process(make_request(f"R{i}", f"d{i}"))
        if close:
            kernel.close_session()
        return run_path

    def _load(self):
        with open(self.run_path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data):
        with open(self.run_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _root_listing(self):
        return sorted(os.listdir(self.root))

    def _file_hash(self):
        with open(self.run_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _assert_append_refused(self, exc=SentinelError):
        """Attempt the full append flow; assert refusal, no side effect, and
        that the loader did not modify the run file."""
        before_fs = self._root_listing()
        before_hash = self._file_hash()
        with self.assertRaises(exc):
            kernel = open_run_for_append(self.run_path)
            # If the loader wrongly returned a kernel, complete the attack so
            # the side-effect assertion below has teeth.
            kernel.process(make_request("ATK", "attack_dir"))
        self.assertEqual(self._root_listing(), before_fs,
                         "Filesystem was modified despite refused append")
        self.assertFalse(os.path.exists(os.path.join(self.root, "attack_dir")))
        self.assertEqual(self._file_hash(), before_hash,
                         "Run file was modified by a refused load")


class TestAppendIntegrity(_Base):
    # ── Attack 1: closed run, deleted seal ─────────────────────────────────
    def test_closed_run_with_deleted_seal_refuses_append(self):
        self._build_run(close=True)
        data = self._load()
        self.assertIsNotNone(data[RUN_SEAL_FIELD])
        data[RUN_SEAL_FIELD] = None  # the attack: erase the seal
        self._write(data)
        self._assert_append_refused(SessionClosedError)

    def test_sealed_run_refuses_append(self):
        self._build_run(close=True)
        self._assert_append_refused(SessionClosedError)

    def test_closed_run_with_deleted_seal_refuses_second_close_via_cli(self):
        # A deleted-seal run must not accept a second close receipt either.
        self._build_run(close=True)
        data = self._load()
        data[RUN_SEAL_FIELD] = None
        self._write(data)
        proc = run_cli(["close", "--run", self.run_path])
        self.assertNotEqual(proc.returncode, 0, proc.stdout)

    # ── Attack 2: structurally broken open chains ──────────────────────────
    def test_open_run_with_deleted_first_receipt_refuses_append(self):
        self._build_run(n_creates=2, close=False)
        data = self._load()
        data["receipts"] = data["receipts"][1:]  # delete the first receipt
        self._write(data)
        self._assert_append_refused(ChainVerificationError)

    def test_open_run_with_deleted_middle_receipt_refuses_append(self):
        self._build_run(n_creates=3, close=False)
        data = self._load()
        del data["receipts"][1]  # delete a middle receipt
        self._write(data)
        self._assert_append_refused(ChainVerificationError)

    def test_broken_prior_hash_refuses_append(self):
        self._build_run(n_creates=2, close=False)
        data = self._load()
        r = data["receipts"][1]
        r["prior_hash"] = "f" * 64
        # Recompute the self-hash so ONLY the linkage is broken (otherwise the
        # self-hash check fires first and the linkage check is never reached).
        from sentinel_core.canonical import canonical_json
        payload = {k: v for k, v in r.items() if k != "canonical_hash"}
        r["canonical_hash"] = hashlib.sha256(
            canonical_json(payload).encode("utf-8")).hexdigest()
        self._write(data)
        self._assert_append_refused(ChainVerificationError)

    def test_duplicate_receipt_ids_refuse_append(self):
        self._build_run(n_creates=2, close=False)
        data = self._load()
        data["receipts"].append(dict(data["receipts"][1]))  # duplicate id 1
        self._write(data)
        self._assert_append_refused(ChainVerificationError)

    def test_tampered_receipt_field_refuses_append(self):
        # Field tamper without rehash: caught by per-receipt self-hash at load.
        self._build_run(n_creates=2, close=False)
        data = self._load()
        data["receipts"][0]["request"]["target_path"] = "evil"
        self._write(data)
        self._assert_append_refused(ChainVerificationError)

    # ── Valid paths unchanged ──────────────────────────────────────────────
    def test_valid_open_run_appends(self):
        self._build_run(n_creates=2, close=False)
        kernel = open_run_for_append(self.run_path)
        self.assertEqual(kernel.session_state, "OPEN")
        r = kernel.process(make_request("R9", "appended"))
        self.assertEqual(r.decision, "ALLOW")
        # v0.2: 2 prior ALLOW creates = 4 receipts (ids 0-3); the appended
        # ALLOW adds INTENT(4)+RESULT(5). The returned RESULT id is 5.
        self.assertEqual(r.receipt_id, 5)  # contiguous, no duplicates
        self.assertEqual(r.intent_receipt_id, 4)
        self.assertTrue(os.path.isdir(os.path.join(self.root, "appended")))
        # The extended run is still fully valid for a future append.
        kernel2 = open_run_for_append(self.run_path)
        self.assertEqual(kernel2._journal.chain.next_id(), 6)

    def test_session_state_derived_from_chain_head(self):
        self._build_run(n_creates=1, close=False)
        kernel = open_run_for_append(self.run_path)
        head = kernel._journal.chain.head()
        self.assertEqual(kernel.session_state, head.post_session_state)

    # ── Replay behaviour unchanged ─────────────────────────────────────────
    def test_replay_unchanged_valid_closed_run_passes(self):
        self._build_run(n_creates=2, close=True)
        ok, report = replay_from_path(self.run_path)
        self.assertTrue(ok, report)

    def test_replay_unchanged_after_refused_append(self):
        # A refused append must leave a valid closed run byte-identical and
        # still replayable; and the tampered (deleted-seal) variant must still
        # fail replay exactly as before.
        self._build_run(n_creates=2, close=True)
        with self.assertRaises(SessionClosedError):
            open_run_for_append(self.run_path)
        ok, report = replay_from_path(self.run_path)
        self.assertTrue(ok, report)
        data = self._load()
        data[RUN_SEAL_FIELD] = None
        self._write(data)
        ok2, _ = replay_from_path(self.run_path)
        self.assertFalse(ok2)


class TestAppendIntegrityCLI(_Base):
    """End-to-end reproductions of both reported attacks through the CLI.

    v0.2.1: invoked IN-PROCESS via sentinel.main() (no subprocess, no pipes, no
    child processes), so the suite cannot be held open at shutdown by an
    inherited pipe or lingering child. The class name is preserved so
    `python3 -m unittest tests.test_append_integrity.TestAppendIntegrityCLI`
    still resolves.
    """

    def _cli(self, *args):
        return run_cli(list(args))

    def test_attack1_end_to_end(self):
        # 1. create a run; 2. create one directory; 3. close; 4. delete
        # run_seal; 5. run create again. Must be refused with no side effect.
        p = self._cli("create", "--run", self.run_path, "--run-id", "r",
                      "--request-id", "R1", "--target-path", "legit",
                      "--allowed-root", self.root)
        self.assertEqual(p.returncode, 0, p.stderr)
        p = self._cli("close", "--run", self.run_path)
        self.assertEqual(p.returncode, 0, p.stderr)
        data = self._load()
        data[RUN_SEAL_FIELD] = None  # step 4: the attack
        self._write(data)
        before = self._root_listing()
        p = self._cli("create", "--run", self.run_path, "--run-id", "r",
                      "--request-id", "R2", "--target-path", "smuggled")
        self.assertNotEqual(p.returncode, 0,
                            f"Append onto closed/deseal run was ACCEPTED:\n{p.stdout}")
        self.assertEqual(self._root_listing(), before)
        self.assertFalse(os.path.exists(os.path.join(self.root, "smuggled")))

    def test_attack2_end_to_end(self):
        # 1. open run with two receipts; 2. delete the first receipt;
        # 3. run create again. Must be refused with no side effect.
        for i, name in enumerate(("a", "b")):
            p = self._cli("create", "--run", self.run_path, "--run-id", "r",
                          "--request-id", f"R{i}", "--target-path", name,
                          *(["--allowed-root", self.root] if i == 0 else []))
            self.assertEqual(p.returncode, 0, p.stderr)
        data = self._load()
        data["receipts"] = data["receipts"][1:]  # step 2: the attack
        self._write(data)
        before = self._root_listing()
        p = self._cli("create", "--run", self.run_path, "--run-id", "r",
                      "--request-id", "R9", "--target-path", "smuggled")
        self.assertNotEqual(p.returncode, 0,
                            f"Append onto broken chain was ACCEPTED:\n{p.stdout}")
        self.assertEqual(self._root_listing(), before)
        self.assertFalse(os.path.exists(os.path.join(self.root, "smuggled")))

    def test_valid_cli_append_still_works(self):
        p = self._cli("create", "--run", self.run_path, "--run-id", "r",
                      "--request-id", "R1", "--target-path", "a",
                      "--allowed-root", self.root)
        self.assertEqual(p.returncode, 0, p.stderr)
        p = self._cli("create", "--run", self.run_path, "--run-id", "r",
                      "--request-id", "R2", "--target-path", "a/b")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(os.path.isdir(os.path.join(self.root, "a", "b")))
        p = self._cli("close", "--run", self.run_path)
        self.assertEqual(p.returncode, 0, p.stderr)
        p = self._cli("replay", "--run", self.run_path)
        self.assertEqual(p.returncode, 0, p.stdout)


if __name__ == "__main__":
    unittest.main()
