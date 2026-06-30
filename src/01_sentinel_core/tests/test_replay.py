# tests/test_replay.py
import copy
import json
import os
import shutil
import unittest

from sentinel_core.replay import replay_from_path
from sentinel_core.run_seal import RUN_SEAL_FIELD, compute_run_seal_hash
from sentinel_core.manifest import compute_manifest_hash
from tests.helpers import make_request, new_kernel, temp_root, temp_runs


class TestReplay(unittest.TestCase):
    def setUp(self):
        self.root = temp_root()
        self.runs = temp_runs()
        self.outside = temp_root()

    def tearDown(self):
        for d in (self.root, self.runs, self.outside):
            shutil.rmtree(d, ignore_errors=True)

    def _build_run(self, close=True, run_id="rp"):
        kernel, run_path = new_kernel(run_id, self.root, self.runs)
        kernel.process(make_request("A", "demo"))
        kernel.process(make_request("B", "demo/output"))
        kernel.process(make_request("C", "demo"))          # already exists -> block
        kernel.process(make_request("D", "ghost", dry_run=True))  # dry-run
        kernel.process(make_request("E", "../escape"))     # traversal -> block
        if close:
            kernel.close_session()
        return run_path

    def _load(self, path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def test_valid_replay_passes(self):
        path = self._build_run()
        ok, report = replay_from_path(path)
        self.assertTrue(ok, report)

    def test_open_run_replay_requires_open_mode(self):
        path = self._build_run(close=False)
        ok, _ = replay_from_path(path)  # closed/audit mode, no seal
        self.assertFalse(ok)
        ok2, report = replay_from_path(path, allow_open=True)
        self.assertTrue(ok2, report)

    def test_deleted_final_receipt_fails_closed(self):
        path = self._build_run()
        data = self._load(path)
        data["receipts"] = data["receipts"][:-1]  # drop the close receipt
        self._write(path, data)
        ok, report = replay_from_path(path)
        self.assertFalse(ok)  # seal now references a missing final receipt

    def test_deleted_run_seal_fails_closed(self):
        path = self._build_run()
        data = self._load(path)
        data[RUN_SEAL_FIELD] = None
        self._write(path, data)
        ok, report = replay_from_path(path)
        self.assertFalse(ok)

    def test_mutated_target_path_fails(self):
        path = self._build_run()
        data = self._load(path)
        data["receipts"][0]["request"]["target_path"] = "evil"
        self._write(path, data)
        ok, report = replay_from_path(path)
        self.assertFalse(ok)
        self.assertIn("receipt chain", report.lower())

    def test_injected_allowed_root_in_request_fails(self):
        # v1.1.0 requests have no allowed_root. Injecting one into a saved
        # request is field tampering: the receipt self-hash no longer matches.
        path = self._build_run()
        data = self._load(path)
        data["receipts"][0]["request"]["allowed_root"] = self.outside
        self._write(path, data)
        ok, report = replay_from_path(path)
        self.assertFalse(ok)

    def test_mutated_manifest_allowed_root_fails(self):
        # The manifest root is the authoritative boundary; changing it without
        # recomputing manifest_hash must fail at manifest validation.
        path = self._build_run()
        data = self._load(path)
        data["manifest"]["allowed_root"] = self.outside
        self._write(path, data)
        ok, report = replay_from_path(path)
        self.assertFalse(ok)

    def test_mutated_decision_fails(self):
        path = self._build_run()
        data = self._load(path)
        # v0.2: index 4 is the BLOCK_TARGET_ALREADY_EXISTS RESULT. Flip it to
        # ALLOW without recomputing hash -> caught by per-receipt self-hash.
        data["receipts"][4]["decision"] = "ALLOW"
        self._write(path, data)
        ok, report = replay_from_path(path)
        self.assertFalse(ok)

    def test_mutated_decision_with_recomputed_hash_still_fails_revalidation(self):
        # Even if an attacker recomputes the self-hash (unkeyed), the invalid
        # decision/reason pairing is rejected when the receipt is reconstructed.
        path = self._build_run()
        data = self._load(path)
        r = data["receipts"][4]  # the BLOCK_TARGET_ALREADY_EXISTS RESULT
        r["decision"] = "ALLOW"  # ALLOW with a BLOCK reason -> invalid pairing/stage
        # Recompute a hash over the tampered payload (excluding canonical_hash).
        from sentinel_core.canonical import canonical_json
        import hashlib
        payload = {k: v for k, v in r.items() if k != "canonical_hash"}
        r["canonical_hash"] = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
        self._write(path, data)
        ok, report = replay_from_path(path)
        self.assertFalse(ok)  # invalid pairing rejected at receipt reconstruction

    def test_hostile_malformed_json_fails_closed(self):
        path = os.path.join(self.runs, "hostile.json")
        with open(path, "w") as f:
            f.write("{not valid json at all ::::")
        ok, report = replay_from_path(path)
        self.assertFalse(ok)
        self.assertIn("load", report.lower())

    def test_deeply_nested_json_fails_closed(self):
        path = os.path.join(self.runs, "bomb.json")
        with open(path, "w") as f:
            f.write("[" * 200000 + "]" * 200000)
        ok, report = replay_from_path(path)
        self.assertFalse(ok)  # RecursionError mapped to controlled failure

    def test_manifest_hash_mutation_fails(self):
        path = self._build_run()
        data = self._load(path)
        data["manifest"]["allowed_root"] = self.outside  # without rehash
        self._write(path, data)
        ok, report = replay_from_path(path)
        self.assertFalse(ok)

    def test_missing_file_fails_closed(self):
        ok, report = replay_from_path(os.path.join(self.runs, "nope.json"))
        self.assertFalse(ok)

    def test_old_version_vector_is_replay_incompatible(self):
        # A run claiming the v0.1.0 vector (request schema 1.0.0) must be
        # refused as incompatible — never silently re-interpreted under the
        # new authoritative-root semantics. The manifest hash is recomputed so
        # the file is internally consistent; only the version gate stops it.
        path = self._build_run()
        data = self._load(path)
        m = data["manifest"]
        m["impl_version"] = "0.1.0"
        m["action_schema_version"] = "1.0.0"
        m["policy_version"] = "0.1.0"
        m["manifest_hash"] = compute_manifest_hash(m)
        self._write(path, data)
        ok, report = replay_from_path(path)
        self.assertFalse(ok)
        self.assertIn("INCOMPATIBLE", report)


if __name__ == "__main__":
    unittest.main()
