# tests/test_boundary_authority.py
# v0.1.1 release-blocker repair tests.
#
# The blocker: in v0.1.0 the request carried its own "allowed_root", so a run
# created with manifest root A could process a request self-declaring root B
# and create a directory under B, while replay still passed (the run was
# internally consistent). The configured boundary was not authoritative.
#
# The repair: allowed_root was REMOVED from the request schema (v1.1.0). The
# kernel passes journal.manifest["allowed_root"] into path policy. These tests
# prove the manifest root is the only boundary that matters.

import json
import os
import shutil
import unittest

from sentinel_core.reason_codes import (
    BLOCK, BLOCK_SCHEMA_INVALID, BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED,
)
from sentinel_core.replay import replay_from_path
from tests.helpers import make_request, new_kernel, temp_root, temp_runs


class TestBoundaryAuthority(unittest.TestCase):
    def setUp(self):
        self.root_a = temp_root()   # the run's configured boundary
        self.root_b = temp_root()   # an attacker-chosen other root
        self.runs = temp_runs()
        self.kernel, self.run_path = new_kernel("authority", self.root_a, self.runs)

    def tearDown(self):
        for d in (self.root_a, self.root_b, self.runs):
            shutil.rmtree(d, ignore_errors=True)

    def _listing(self, root):
        return sorted(os.listdir(root))

    def test_request_declaring_other_root_is_blocked_and_no_root_modified(self):
        # The exact v0.1.0 attack shape: a request that self-declares root B
        # while the manifest says root A. In v1.1.0 the field itself is
        # rejected (extra field -> schema invalid). Neither root is touched.
        before_a, before_b = self._listing(self.root_a), self._listing(self.root_b)
        attack = make_request("ATK-1", "stolen_dir")
        attack["allowed_root"] = self.root_b  # v1.0.0-style self-declared root
        receipt = self.kernel.process(attack)
        self.assertEqual(receipt.decision, BLOCK)
        self.assertEqual(receipt.reason_code, BLOCK_SCHEMA_INVALID)
        self.assertFalse(receipt.executed)
        self.assertEqual(self._listing(self.root_a), before_a)
        self.assertEqual(self._listing(self.root_b), before_b)
        self.assertFalse(os.path.exists(os.path.join(self.root_b, "stolen_dir")))

    def test_absolute_target_under_other_root_blocked_against_manifest_root(self):
        # Even without the removed field, an absolute target under root B must
        # be judged against the MANIFEST root A and blocked.
        before_b = self._listing(self.root_b)
        r = self.kernel.process(make_request("ATK-2", os.path.join(self.root_b, "stolen_dir")))
        self.assertEqual(r.reason_code, BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED)
        self.assertEqual(self._listing(self.root_b), before_b)

    def test_allow_executes_under_manifest_root_only(self):
        r = self.kernel.process(make_request("OK-1", "legit"))
        self.assertEqual(r.decision, "ALLOW")
        self.assertTrue(os.path.isdir(os.path.join(self.root_a, "legit")))
        self.assertFalse(os.path.exists(os.path.join(self.root_b, "legit")))

    def test_recorded_request_carries_no_allowed_root(self):
        # The normalised request stored in the receipt must not contain any
        # allowed_root field; the boundary lives in the manifest alone.
        r = self.kernel.process(make_request("OK-2", "another"))
        self.assertNotIn("allowed_root", r.request)
        with open(self.run_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertNotIn("allowed_root", data["receipts"][-1]["request"])
        self.assertEqual(data["manifest"]["allowed_root"], self.root_a)

    def test_replay_judges_against_manifest_root(self):
        # Build a run containing the attack attempts; close; replay must pass
        # (the blocks re-derive) and must not create anything outside its
        # sandbox — in particular nothing in root B.
        attack = make_request("ATK-3", "stolen_dir")
        attack["allowed_root"] = self.root_b
        self.kernel.process(attack)
        self.kernel.process(make_request("ATK-4", os.path.join(self.root_b, "x")))
        self.kernel.process(make_request("OK-3", "legit"))
        self.kernel.close_session()
        before_b = self._listing(self.root_b)
        ok, report = replay_from_path(self.run_path)
        self.assertTrue(ok, report)
        self.assertEqual(self._listing(self.root_b), before_b)


if __name__ == "__main__":
    unittest.main()
