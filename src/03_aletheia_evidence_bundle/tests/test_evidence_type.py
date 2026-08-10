# tests/test_evidence_type.py
# Move 63 red/blue suite for the evidence-type classification layer.
import json
import os
import shutil
import tempfile
import unittest

from aletheia_evidence import evidence_type as et
from aletheia_evidence.hashing import sha256_bytes


class TestEvidenceType(unittest.TestCase):
    def setUp(self):
        self._tmpdirs = []
        self._tmpfiles = []

    def tearDown(self):
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)
        for f in self._tmpfiles:
            try:
                os.remove(f)
            except OSError:
                pass

    def _out(self):
        d = tempfile.mkdtemp()
        os.rmdir(d)  # a fresh, non-existent, empty target the layer will create
        self._tmpdirs.append(d)
        return d

    def _file(self, data):
        fd, p = tempfile.mkstemp()
        if isinstance(data, str):
            data = data.encode("utf-8")
        os.write(fd, data)
        os.close(fd)
        self._tmpfiles.append(p)
        return p

    def _classify(self, **kw):
        kw.setdefault("case_id", "case_001")
        kw.setdefault("evidence_id", "evidence_001")
        kw.setdefault("out_dir", self._out())
        kw.setdefault("now_utc", "2026-07-01T00:00:00Z")
        return et.classify_file(**kw)

    # ── PASS ────────────────────────────────────────────────────────────────
    def test_pass_text(self):
        r = self._classify(source_file=self._file("hello world\n"), evidence_type="LOCAL_TEXT_UTF8")
        self.assertEqual(r.status, et.CLASSIFIED)
        self.assertEqual(r.report["evidence_type"], "LOCAL_TEXT_UTF8")
        self.assertTrue(os.path.isfile(r.report_path))

    def test_pass_json_object(self):
        r = self._classify(source_file=self._file('{"a": 1, "b": [2, 3]}'), evidence_type="LOCAL_JSON")
        self.assertEqual(r.status, et.CLASSIFIED)
        self.assertEqual(r.report["evidence_type"], "LOCAL_JSON")

    def test_pass_json_array(self):
        r = self._classify(source_file=self._file('[1, 2, 3]'), evidence_type="LOCAL_JSON")
        self.assertEqual(r.status, et.CLASSIFIED)
        self.assertEqual(r.report["evidence_type"], "LOCAL_JSON")

    def test_pass_binary(self):
        r = self._classify(source_file=self._file(b"\x89PNG\x00\x01\x02\xff"), evidence_type="LOCAL_BINARY_FILE")
        self.assertEqual(r.status, et.CLASSIFIED)
        self.assertEqual(r.report["evidence_type"], "LOCAL_BINARY_FILE")

    def test_auto_prefers_json_over_text(self):
        r = self._classify(source_file=self._file('{"a": 1}'), evidence_type="AUTO")
        self.assertEqual(r.report["evidence_type"], "LOCAL_JSON")

    def test_auto_prefers_text_over_binary(self):
        r = self._classify(source_file=self._file("just plain text, not json"), evidence_type="AUTO")
        self.assertEqual(r.report["evidence_type"], "LOCAL_TEXT_UTF8")

    def test_auto_falls_back_to_binary(self):
        r = self._classify(source_file=self._file(b"\xff\xfe\x00\x01"), evidence_type="AUTO")
        self.assertEqual(r.report["evidence_type"], "LOCAL_BINARY_FILE")

    def test_report_contains_correct_sha256(self):
        data = b"exact bytes to hash"
        r = self._classify(source_file=self._file(data), evidence_type="LOCAL_BINARY_FILE")
        self.assertEqual(r.report["source_file_sha256"], sha256_bytes(data))

    def test_report_deterministic_except_timestamp(self):
        p = self._file('{"k": [1, 2, 3]}')
        a = self._classify(source_file=p, evidence_type="AUTO", now_utc="2026-07-01T00:00:00Z").report
        b = self._classify(source_file=p, evidence_type="AUTO", now_utc="2026-07-01T00:00:00Z").report
        self.assertEqual(a, b)
        # created_at_utc is the only field permitted to vary between runs.
        c = self._classify(source_file=p, evidence_type="AUTO", now_utc="2099-01-01T00:00:00Z").report
        diff = {k for k in a if a[k] != c[k]}
        self.assertEqual(diff, {"created_at_utc"})

    def test_report_has_all_required_fields(self):
        r = self._classify(source_file=self._file("x"), evidence_type="LOCAL_TEXT_UTF8")
        for field in ("report_schema_version", "case_id", "evidence_id", "source_file_name",
                      "source_file_size_bytes", "source_file_sha256", "evidence_type",
                      "classification_status", "checks_performed", "created_at_utc",
                      "known_limitations"):
            self.assertIn(field, r.report)

    def test_no_truth_claim_in_report(self):
        r = self._classify(source_file=self._file('{"x": 1}'), evidence_type="AUTO")
        blob = json.dumps(r.report).lower()
        for forbidden in ("is true", "are true", "is authentic", "verified true",
                          "proven true", "contents are accurate", "is genuine"):
            self.assertNotIn(forbidden, blob)

    # ── FAIL / BLOCK ──────────────────────────────────────────────────────────
    def test_reject_missing_file(self):
        self.assertEqual(self._classify(source_file="/no/such/file", evidence_type="AUTO").status,
                         et.REJECTED_MISSING_FILE)

    def test_reject_directory(self):
        d = tempfile.mkdtemp(); self._tmpdirs.append(d)
        self.assertEqual(self._classify(source_file=d, evidence_type="AUTO").status,
                         et.REJECTED_DIRECTORY)

    def test_reject_symlink(self):
        tgt = self._file("x"); link = tgt + ".link"; os.symlink(tgt, link); self._tmpfiles.append(link)
        self.assertEqual(self._classify(source_file=link, evidence_type="AUTO").status,
                         et.REJECTED_SYMLINK)

    def test_reject_unsafe_case_id(self):
        self.assertEqual(self._classify(source_file=self._file("x"), case_id="../evil",
                                        evidence_type="AUTO").status, et.REJECTED_SCHEMA_INVALID)

    def test_reject_unsafe_evidence_id(self):
        self.assertEqual(self._classify(source_file=self._file("x"), evidence_id="a/b",
                                        evidence_type="AUTO").status, et.REJECTED_SCHEMA_INVALID)

    def test_reject_invalid_evidence_type(self):
        self.assertEqual(self._classify(source_file=self._file("x"),
                                        evidence_type="LOCAL_PDF").status, et.REJECTED_SCHEMA_INVALID)

    def test_reject_text_invalid_utf8(self):
        self.assertEqual(self._classify(source_file=self._file(b"\xff\xfe\xfd"),
                                        evidence_type="LOCAL_TEXT_UTF8").status, et.REJECTED_INVALID_UTF8)

    def test_reject_text_with_nul(self):
        self.assertEqual(self._classify(source_file=self._file(b"ab\x00cd"),
                                        evidence_type="LOCAL_TEXT_UTF8").status, et.REJECTED_INVALID_UTF8)

    def test_reject_json_invalid(self):
        self.assertEqual(self._classify(source_file=self._file("not json at all"),
                                        evidence_type="LOCAL_JSON").status, et.REJECTED_INVALID_JSON)

    def test_reject_json_scalar_top_level(self):
        self.assertEqual(self._classify(source_file=self._file("42"),
                                        evidence_type="LOCAL_JSON").status, et.REJECTED_INVALID_JSON)

    def test_reject_oversized(self):
        big = self._file(b"a" * (10 * 1024 * 1024 + 1))
        self.assertEqual(self._classify(source_file=big, evidence_type="AUTO").status,
                         et.REJECTED_TOO_LARGE)

    def test_reject_output_dir_not_empty(self):
        ne = tempfile.mkdtemp(); self._tmpdirs.append(ne)
        open(os.path.join(ne, "x"), "w").close()
        self.assertEqual(self._classify(source_file=self._file("x"), evidence_type="AUTO",
                                        out_dir=ne).status, et.REJECTED_UNSAFE_PATH)


if __name__ == "__main__":
    unittest.main()
