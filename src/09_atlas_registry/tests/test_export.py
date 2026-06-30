# tests/test_export.py
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from atlas_registry_lib.exporter import (  # noqa: E402
    export_registry, verify_export)
from atlas_registry_lib.canonical import canonical_bytes  # noqa: E402
from atlas_registry_lib.validation import sha256_file  # noqa: E402
from atlas_registry_lib.checksums import format_checksums, REQUIRED_KEYS  # noqa: E402
from atlas_registry_lib.errors import ExportError, BuildPathError  # noqa: E402
from atlas_registry_lib import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    write_registry, good_registry, export_dir, good_export)


def _resync(out):
    digests = {k: sha256_file(os.path.join(out, k)) for k in REQUIRED_KEYS}
    with open(os.path.join(out, versions.EXPORT_CHECKSUMS), "wb") as f:
        f.write(format_checksums(digests))


class TestExport(unittest.TestCase):
    def test_26_export_writes_required_files(self):
        out = export_dir()
        export_registry(write_registry(good_registry()), out)
        self.assertEqual(set(os.listdir(out)), set(versions.EXPORT_FILES))

    def test_27_summary_counts_match_registry(self):
        out = export_dir()
        result = export_registry(write_registry(good_registry()), out)
        s = result.summary
        self.assertEqual(s["component_count"], 15)
        self.assertEqual(s["workflow_type_count"], 2)
        self.assertEqual(s["action_type_count"], 1)
        self.assertEqual(s["claim_predicate_count"], 2)
        self.assertEqual(s["registry_status"], "REGISTRY_VERIFIED")

    def test_28_checksums_written(self):
        out = good_export()
        with open(os.path.join(out, versions.EXPORT_CHECKSUMS),
                  encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)

    def test_29_verify_valid_export_succeeds(self):
        summary = verify_export(good_export())
        self.assertEqual(summary["registry_status"], "REGISTRY_VERIFIED")

    def test_nonempty_output_dir_refused(self):
        out = export_dir()
        os.makedirs(out)
        with open(os.path.join(out, "rogue"), "w") as f:
            f.write("x")
        with self.assertRaises(BuildPathError) as cm:
            export_registry(write_registry(good_registry()), out)
        self.assertEqual(cm.exception.reason, "OUTPUT_DIR_NOT_EMPTY")

    def test_30_mutated_registry_copy_fails(self):
        out = good_export()
        with open(os.path.join(out, versions.EXPORT_REGISTRY_COPY), "ab") as f:
            f.write(b" ")
        with self.assertRaises(ExportError):
            verify_export(out)

    def test_31_mutated_summary_fails(self):
        out = good_export()
        with open(os.path.join(out, versions.EXPORT_SUMMARY), "ab") as f:
            f.write(b" ")
        with self.assertRaises(ExportError):
            verify_export(out)

    def test_summary_count_mismatch_fails(self):
        out = good_export()
        p = os.path.join(out, versions.EXPORT_SUMMARY)
        with open(p, "rb") as f:
            s = json.loads(f.read().decode())
        s["component_count"] = 999
        with open(p, "wb") as f:
            f.write(canonical_bytes(s))
        _resync(out)
        with self.assertRaises(ExportError) as cm:
            verify_export(out)
        self.assertEqual(cm.exception.reason, "COUNT_MISMATCH")

    def test_32_missing_checksums_fails(self):
        out = good_export()
        os.remove(os.path.join(out, versions.EXPORT_CHECKSUMS))
        with self.assertRaises(ExportError) as cm:
            verify_export(out)
        self.assertEqual(cm.exception.reason, "FILE_MISSING")

    def test_37_unknown_extra_export_file_fails(self):
        out = good_export()
        with open(os.path.join(out, "rogue.txt"), "w") as f:
            f.write("x")
        with self.assertRaises(ExportError) as cm:
            verify_export(out)
        self.assertEqual(cm.exception.reason, "UNKNOWN_FILE")


if __name__ == "__main__":
    unittest.main()
