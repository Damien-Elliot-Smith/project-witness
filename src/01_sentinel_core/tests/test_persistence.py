# tests/test_persistence.py
import json
import os
import shutil
import unittest

from sentinel_core.errors import PersistenceFailure
from sentinel_core.journal import Journal
from sentinel_core.kernel import Kernel
from sentinel_core.manifest import build_manifest
from sentinel_core.persistence import (
    AtomicFileBackend, FailingTestBackend, FailAfterNWritesBackend,
    execute_create_directory,
)
from sentinel_core.receipts import ReceiptChain
from tests.helpers import make_request, temp_root, temp_runs


class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.root = temp_root()
        self.runs = temp_runs()

    def tearDown(self):
        for d in (self.root, self.runs):
            shutil.rmtree(d, ignore_errors=True)

    def _req(self, rid, target, dry=False):
        return make_request(rid, target, dry_run=dry)

    def test_run_file_written_atomically(self):
        run_path = os.path.join(self.runs, "r.json")
        k = Kernel(Journal(AtomicFileBackend(run_path), ReceiptChain("r"), build_manifest("r", self.root)))
        k.process(self._req("A", "d1"))
        self.assertTrue(os.path.exists(run_path))
        with open(run_path, encoding="utf-8") as f:
            data = json.load(f)
        # v0.2: a successful ALLOW persists an INTENT then a RESULT.
        self.assertEqual(len(data["receipts"]), 2)
        self.assertEqual(data["receipts"][0]["stage"], "INTENT")
        self.assertEqual(data["receipts"][1]["stage"], "RESULT")
        # No stray temp files left in the runs directory.
        leftovers = [f for f in os.listdir(self.runs) if f.startswith(".tmp_run_")]
        self.assertEqual(leftovers, [])

    def test_persistence_failure_prevents_commit(self):
        # With a backend whose write always fails, the in-memory chain must NOT
        # advance and the failure must surface (not be swallowed).
        k = Kernel(Journal(FailingTestBackend(), ReceiptChain("r2"), build_manifest("r2", self.root)))
        with self.assertRaises(PersistenceFailure):
            k.process(self._req("A", "commit_probe"))
        self.assertEqual(k._journal.chain.next_id(), 0)
        self.assertEqual(k.session_state, "OPEN")

    def test_intent_persisted_before_mkdir(self):
        # v0.2 core guarantee (fixes the old L1): if persistence fails on the
        # FIRST write (the INTENT), no mkdir runs and no directory is created.
        k = Kernel(Journal(FailingTestBackend(), ReceiptChain("r3"), build_manifest("r3", self.root)))
        with self.assertRaises(PersistenceFailure):
            k.process(self._req("A", "no_dir"))
        self.assertFalse(os.path.exists(os.path.join(self.root, "no_dir")))  # NO side effect
        self.assertEqual(k._journal.chain.next_id(), 0)  # nothing committed

    def test_result_persistence_failure_after_mkdir_is_explicit(self):
        # If the INTENT persists (write #1) but the RESULT write (#2) fails,
        # mkdir already happened: the directory exists, the INTENT is committed,
        # but no RESULT is. The failure is raised, and the on-disk run is left in
        # a detectable RESULT_MISSING_AFTER_INTENT state (see test_two_stage).
        run_path = os.path.join(self.runs, "r4.json")
        backend = FailAfterNWritesBackend(AtomicFileBackend(run_path), n_ok=1)
        k = Kernel(Journal(backend, ReceiptChain("r4"), build_manifest("r4", self.root)))
        with self.assertRaises(PersistenceFailure):
            k.process(self._req("A", "made"))
        self.assertTrue(os.path.isdir(os.path.join(self.root, "made")))  # mkdir ran
        # In-memory: only the INTENT committed.
        self.assertEqual(k._journal.chain.next_id(), 1)
        with open(run_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["receipts"]), 1)
        self.assertEqual(data["receipts"][0]["stage"], "INTENT")

    def test_executor_never_overwrites(self):
        target = os.path.join(self.root, "existing")
        os.mkdir(target)
        with self.assertRaises(PersistenceFailure):
            execute_create_directory(target)

    def test_executor_single_level_only(self):
        # os.mkdir does not create intermediate dirs; missing parent -> failure.
        target = os.path.join(self.root, "missing_parent", "child")
        with self.assertRaises(PersistenceFailure):
            execute_create_directory(target)


if __name__ == "__main__":
    unittest.main()
