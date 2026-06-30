# tests/test_build_bundle.py
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_evidence.builder import build_bundle  # noqa: E402
from aletheia_evidence.canonical import canonical_bytes  # noqa: E402
from aletheia_evidence.errors import BuildError, ValidationError  # noqa: E402
from aletheia_evidence import versions  # noqa: E402
from tests.helpers import make_source  # noqa: E402


class TestBuildBundle(unittest.TestCase):
    def setUp(self):
        self.src = make_source(b"hello evidence\n")
        self.out = os.path.join(tempfile.mkdtemp(), "bundle")

    def _build(self):
        return build_bundle(source_file=self.src, case_id="case_001",
                            evidence_id="evidence_001", out_dir=self.out)

    def test_9_valid_file_bundles_successfully(self):
        r = self._build()
        self.assertEqual(r.evidence_status, versions.EVIDENCE_VERIFIED_PRESENT)
        self.assertEqual(r.manifest["bundle_status"], "BUNDLED")

    def test_10_bundle_copies_file_into_evidence_bin(self):
        self._build()
        bundled = os.path.join(self.out, "evidence", "evidence_001.bin")
        self.assertTrue(os.path.isfile(bundled))
        with open(bundled, "rb") as f:
            self.assertEqual(f.read(), b"hello evidence\n")

    def test_11_manifest_is_canonical_json(self):
        r = self._build()
        p = os.path.join(self.out, "evidence_manifest.json")
        with open(p, "rb") as f:
            raw = f.read()
        self.assertEqual(canonical_bytes(r.manifest), raw)
        self.assertTrue(raw.endswith(b"\n"))
        # round-trips
        self.assertEqual(json.loads(raw.decode()), r.manifest)

    def test_12_checksums_file_written(self):
        self._build()
        p = os.path.join(self.out, "evidence_checksums.txt")
        self.assertTrue(os.path.isfile(p))
        with open(p, encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        self.assertTrue(any("evidence_manifest.json" in ln for ln in lines))
        self.assertTrue(any("evidence/evidence_001.bin" in ln for ln in lines))

    def test_source_and_bundled_hashes_match(self):
        r = self._build()
        self.assertEqual(r.manifest["source_file_sha256"],
                         r.manifest["bundled_file_sha256"])

    def test_manifest_records_size_and_name(self):
        r = self._build()
        self.assertEqual(r.manifest["source_file_size_bytes"], 15)
        self.assertEqual(r.manifest["source_file_name"],
                         os.path.basename(self.src))

    def test_nonempty_output_dir_refused(self):
        os.makedirs(self.out)
        with open(os.path.join(self.out, "rogue"), "w") as f:
            f.write("x")
        with self.assertRaises(BuildError) as cm:
            self._build()
        self.assertEqual(cm.exception.reason, "OUTPUT_DIR_NOT_EMPTY")

    def test_unsafe_ids_refused_at_build(self):
        with self.assertRaises(ValidationError):
            build_bundle(source_file=self.src, case_id="../x",
                         evidence_id="evidence_001", out_dir=self.out)

    def test_deterministic_with_fixed_timestamp(self):
        out2 = os.path.join(tempfile.mkdtemp(), "bundle2")
        ts = "2026-01-01T00:00:00Z"
        r1 = build_bundle(source_file=self.src, case_id="c", evidence_id="e",
                          out_dir=self.out, created_at_utc=ts)
        r2 = build_bundle(source_file=self.src, case_id="c", evidence_id="e",
                          out_dir=out2, created_at_utc=ts)
        self.assertEqual(canonical_bytes(r1.manifest),
                         canonical_bytes(r2.manifest))


if __name__ == "__main__":
    unittest.main()
