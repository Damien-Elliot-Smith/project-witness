# tests/test_run_seal.py
import json
import os
import shutil
import unittest

from sentinel_core.errors import ManifestError
from sentinel_core.run_seal import (
    build_run_seal, validate_run_seal, compute_run_seal_hash, RUN_SEAL_FIELD,
)
from tests.helpers import make_request, new_kernel, temp_root, temp_runs


class TestRunSeal(unittest.TestCase):
    def setUp(self):
        self.root = temp_root()
        self.runs = temp_runs()
        self.kernel, self.run_path = new_kernel("seal_run", self.root, self.runs)

    def tearDown(self):
        for d in (self.root, self.runs):
            shutil.rmtree(d, ignore_errors=True)

    def _build_closed_run(self):
        self.kernel.process(make_request("A", "d1"))
        self.kernel.close_session()
        with open(self.run_path, encoding="utf-8") as f:
            return json.load(f)

    def test_closed_run_has_seal(self):
        data = self._build_closed_run()
        self.assertIsNotNone(data[RUN_SEAL_FIELD])
        seal = validate_run_seal(data, require_closed=True)
        self.assertEqual(seal["final_session_state"], "CLOSED_BY_OPERATOR")

    def test_cannot_seal_empty_run(self):
        with self.assertRaises(ManifestError):
            build_run_seal({"run_id": "x", "manifest_hash": "0" * 64}, [])

    def test_seal_hash_mutation_detected(self):
        data = self._build_closed_run()
        data[RUN_SEAL_FIELD]["receipt_count"] = 999
        with self.assertRaises(ManifestError):
            validate_run_seal(data, require_closed=True)

    def test_open_run_seal_required_in_closed_mode(self):
        self.kernel.process(make_request("A", "d1"))
        with open(self.run_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsNone(data[RUN_SEAL_FIELD])
        with self.assertRaises(ManifestError):
            validate_run_seal(data, require_closed=True)

    def test_open_run_seal_accepted_in_open_mode(self):
        self.kernel.process(make_request("A", "d1"))
        with open(self.run_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsNone(validate_run_seal(data, require_closed=False))

    def test_seal_final_hash_must_match_final_receipt(self):
        data = self._build_closed_run()
        # Corrupt the final receipt hash; reseal hash stays old -> mismatch.
        data[RUN_SEAL_FIELD]["final_receipt_hash"] = "a" * 64
        data[RUN_SEAL_FIELD]["seal_hash"] = compute_run_seal_hash(
            {k: v for k, v in data[RUN_SEAL_FIELD].items() if k != "seal_hash"})
        with self.assertRaises(ManifestError):
            validate_run_seal(data, require_closed=True)


if __name__ == "__main__":
    unittest.main()
