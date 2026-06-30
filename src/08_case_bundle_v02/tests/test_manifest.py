# tests/test_manifest.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from case_bundle_v02_lib.manifest import build_manifest  # noqa: E402
from case_bundle_v02_lib.canonical import canonical_bytes  # noqa: E402
from case_bundle_v02_lib import versions  # noqa: E402


def _facts():
    return dict(
        sentinel_facts={"source_component": "histor_lite",
                        "case_status": "IMPORTED", "action_status": "PASS_STRICT"},
        aletheia_facts={"source_component": "histor_lite_aletheia_importer",
                        "import_status": "IMPORTED_VERIFIED_ALETHEIA",
                        "source_evidence_status": "VERIFIED_PRESENT"},
        odin_facts={"source_component": "histor_lite_odin_importer",
                    "import_status": "IMPORTED_VERIFIED_ODIN",
                    "source_reasoning_status": "CONSISTENT", "claim_count": 1,
                    "contradiction_count": 0})


class TestManifest(unittest.TestCase):
    def test_manifest_fields(self):
        m = build_manifest(case_id="case_001", **_facts())
        self.assertEqual(m["case_bundle_version"], "0.2.0")
        self.assertEqual(m["bundle_status"], "BUNDLED_VERIFIED_CASE")
        self.assertEqual(m["included_records"],
                         ["sentinel_case", "aletheia_case", "odin_case"])
        self.assertEqual(m["aletheia"]["source_evidence_status"],
                         "VERIFIED_PRESENT")
        self.assertEqual(m["odin"]["source_reasoning_status"], "CONSISTENT")

    def test_manifest_deterministic_canonical(self):
        a = build_manifest(case_id="case_001", **_facts())
        b = build_manifest(case_id="case_001", **_facts())
        self.assertEqual(canonical_bytes(a), canonical_bytes(b))

    def test_manifest_known_limitations_disclaim_truth(self):
        m = build_manifest(case_id="case_001", **_facts())
        joined = " ".join(m["known_limitations"]).lower()
        self.assertIn("does not prove evidence contents are true", joined)
        self.assertIn("does not prove odin claims are true", joined)

    def test_contradiction_status_in_manifest(self):
        f = _facts()
        f["odin_facts"]["source_reasoning_status"] = "CONTRADICTION_DETECTED"
        f["odin_facts"]["contradiction_count"] = 1
        m = build_manifest(case_id="case_001", **f)
        self.assertEqual(m["odin"]["source_reasoning_status"],
                         "CONTRADICTION_DETECTED")


if __name__ == "__main__":
    unittest.main()
