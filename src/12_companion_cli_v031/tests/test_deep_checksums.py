"""Tests for the v0.3.2 deep verification repair (RT-004).

RT-004: companion verify previously returned verify_ok = true on a run
whose nested evidence bytes had been tampered, because only the eight
top-level REQUIRED_PATHS were hash-checked. These tests prove the two
attacks now fail at the Companion layer:

  attack 1: flip bytes in a nested evidence file
  attack 2: flip bytes AND rewrite the nested checksum entry to match
            (caught by the Aletheia manifest bundled_file_sha256 binding)
"""

import os
import unittest

from companion_lib import canonical, deep_checksums, verifier
from companion_lib.checksums import sha256_bytes
from companion_lib.errors import VerifyError

from tests._helpers import TempCase


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    canonical.atomic_write_bytes(path, data)


class DeepChecksumsUnit(unittest.TestCase):
    """Unit tests against a minimal synthetic tree."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name
        self.nested = os.path.join(self.out, "coordinator_output", "part")
        self.payload = b"payload-bytes"
        _write(os.path.join(self.nested, "inner", "data.bin"), self.payload)
        _write(os.path.join(self.nested, "part_checksums.txt"),
               ("%s  inner/data.bin\n" % sha256_bytes(self.payload))
               .encode("utf-8"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_clean_tree_passes_and_counts(self):
        self.assertEqual(deep_checksums.verify_deep(self.out), 1)

    def test_top_level_companion_checksums_is_excluded(self):
        _write(os.path.join(self.out, "companion_checksums.txt"),
               b"not  a  valid  format\n")
        self.assertEqual(deep_checksums.verify_deep(self.out), 1)

    def test_tampered_nested_file_fails(self):
        _write(os.path.join(self.nested, "inner", "data.bin"), b"tampered")
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_missing_listed_file_fails(self):
        os.remove(os.path.join(self.nested, "inner", "data.bin"))
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_three_field_sentinel_format_accepted(self):
        _write(os.path.join(self.nested, "checksums.txt"),
               ("label_sha256  %s  inner/data.bin\n"
                % sha256_bytes(self.payload)).encode("utf-8"))
        self.assertEqual(deep_checksums.verify_deep(self.out), 2)

    def test_malformed_line_fails(self):
        _write(os.path.join(self.nested, "checksums.txt"), b"one-field-only\n")
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_uppercase_digest_fails(self):
        digest = sha256_bytes(self.payload).upper()
        _write(os.path.join(self.nested, "checksums.txt"),
               ("%s  inner/data.bin\n" % digest).encode("utf-8"))
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_duplicate_entry_fails(self):
        line = "%s  inner/data.bin\n" % sha256_bytes(self.payload)
        _write(os.path.join(self.nested, "checksums.txt"),
               (line + line).encode("utf-8"))
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_path_traversal_entry_fails(self):
        _write(os.path.join(self.nested, "checksums.txt"),
               ("%s  ../escape.bin\n" % sha256_bytes(b"x")).encode("utf-8"))
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_absolute_path_entry_fails(self):
        _write(os.path.join(self.nested, "checksums.txt"),
               ("%s  /etc/hostname\n" % sha256_bytes(b"x")).encode("utf-8"))
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_manifest_binding_checks_bundled_file(self):
        bundle = os.path.join(self.out, "coordinator_output", "aletheia_bundle")
        evidence = b"evidence-bytes"
        _write(os.path.join(bundle, "evidence", "evidence_001.bin"), evidence)
        canonical.write_canonical(
            os.path.join(bundle, "evidence_manifest.json"),
            {"bundled_file_path": "evidence/evidence_001.bin",
             "bundled_file_sha256": sha256_bytes(evidence)})
        self.assertTrue(
            deep_checksums.verify_aletheia_manifest_binding(self.out))

    def test_manifest_binding_catches_checksum_fixup_attack(self):
        bundle = os.path.join(self.out, "coordinator_output", "aletheia_bundle")
        evidence = b"evidence-bytes"
        _write(os.path.join(bundle, "evidence", "evidence_001.bin"), evidence)
        canonical.write_canonical(
            os.path.join(bundle, "evidence_manifest.json"),
            {"bundled_file_path": "evidence/evidence_001.bin",
             "bundled_file_sha256": sha256_bytes(evidence)})
        # attacker tampers evidence AND rewrites the nested checksum entry
        tampered = b"Xvidence-bytes"
        _write(os.path.join(bundle, "evidence", "evidence_001.bin"), tampered)
        _write(os.path.join(bundle, "evidence_checksums.txt"),
               ("%s  evidence/evidence_001.bin\n"
                % sha256_bytes(tampered)).encode("utf-8"))
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_manifest_without_binding_fields_is_skipped(self):
        bundle = os.path.join(self.out, "coordinator_output", "aletheia_bundle")
        canonical.write_canonical(
            os.path.join(bundle, "evidence_manifest.json"),
            {"aletheia_status": "VERIFIED_PRESENT"})
        self.assertFalse(
            deep_checksums.verify_aletheia_manifest_binding(self.out))

    def test_declared_binding_with_missing_file_fails(self):
        bundle = os.path.join(self.out, "coordinator_output", "aletheia_bundle")
        canonical.write_canonical(
            os.path.join(bundle, "evidence_manifest.json"),
            {"bundled_file_path": "evidence/evidence_001.bin",
             "bundled_file_sha256": sha256_bytes(b"whatever")})
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)


class SourceRunBinding(unittest.TestCase):
    """Labeled provenance entries bind to the source run when it exists."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name
        self.run_bytes = b'{"sentinel": "run"}\n'
        self.case_dir = os.path.join(
            self.out, "coordinator_output", "case_bundle_v02", "sentinel_case")
        _write(os.path.join(self.case_dir, "checksums.txt"),
               ("source_run_sha256  %s  sentinel_run.json\n"
                % sha256_bytes(self.run_bytes)).encode("utf-8"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_matching_source_run_passes(self):
        _write(os.path.join(self.out, "coordinator_output", "sentinel_run",
                            "sentinel_run.json"), self.run_bytes)
        self.assertEqual(deep_checksums.verify_deep(self.out), 1)

    def test_tampered_source_run_fails(self):
        _write(os.path.join(self.out, "coordinator_output", "sentinel_run",
                            "sentinel_run.json"), self.run_bytes + b" ")
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_absent_source_run_is_provenance_only(self):
        # nothing to bind against: recorded hash only, no failure, not counted
        self.assertEqual(deep_checksums.verify_deep(self.out), 0)

    def test_unlabeled_missing_sibling_still_fails(self):
        _write(os.path.join(self.case_dir, "checksums.txt"),
               ("%s  sentinel_run.json\n"
                % sha256_bytes(self.run_bytes)).encode("utf-8"))
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)


class RawManifestFallback(unittest.TestCase):
    """The Coordinator's documented case_manifest replacement is accepted;
    anything short of the exact documented shape still fails."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name
        self.bundle = os.path.join(
            self.out, "coordinator_output", "case_bundle_v02")
        self.raw = b'{"case_bundle_version": "0.2.0"}\n'
        _write(os.path.join(self.bundle, "raw_case_bundle_manifest.json"),
               self.raw)
        canonical.write_canonical(
            os.path.join(self.bundle, "case_manifest.json"),
            {"raw_case_bundle_manifest_preserved": True,
             "raw_case_bundle_manifest": "raw_case_bundle_manifest.json",
             "source": "coordinator_compatibility_summary"})
        _write(os.path.join(self.bundle, "bundle_checksums.txt"),
               ("%s  case_manifest.json\n" % sha256_bytes(self.raw))
               .encode("utf-8"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_documented_replacement_is_accepted(self):
        self.assertEqual(deep_checksums.verify_deep(self.out), 1)

    def test_tampered_raw_manifest_still_fails(self):
        _write(os.path.join(self.bundle, "raw_case_bundle_manifest.json"),
               self.raw + b" ")
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_fallback_requires_declared_preservation(self):
        canonical.write_canonical(
            os.path.join(self.bundle, "case_manifest.json"),
            {"source": "coordinator_compatibility_summary"})
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_fallback_never_applies_to_other_entries(self):
        _write(os.path.join(self.bundle, "bundle_checksums.txt"),
               ("%s  other_file.json\n" % sha256_bytes(self.raw))
               .encode("utf-8"))
        _write(os.path.join(self.bundle, "other_file.json"), b"different")
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)


class EvidenceDirCompleteness(unittest.TestCase):
    """Files planted in the evidence directory without a checksum entry
    must fail verification (evidence added unexpectedly)."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name
        self.bundle = os.path.join(self.out, "coordinator_output",
                                   "aletheia_bundle")
        evidence = b"real-evidence"
        _write(os.path.join(self.bundle, "evidence", "evidence_001.bin"),
               evidence)
        _write(os.path.join(self.bundle, "evidence_checksums.txt"),
               ("%s  evidence/evidence_001.bin\n" % sha256_bytes(evidence))
               .encode("utf-8"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_complete_evidence_dir_passes(self):
        self.assertEqual(deep_checksums.verify_deep(self.out), 1)

    def test_planted_evidence_file_fails(self):
        _write(os.path.join(self.bundle, "evidence", "planted.bin"),
               b"planted")
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_planted_file_in_subdirectory_fails(self):
        _write(os.path.join(self.bundle, "evidence", "sub", "hidden.bin"),
               b"hidden")
        with self.assertRaises(VerifyError):
            deep_checksums.verify_deep(self.out)

    def test_absent_layout_is_skipped(self):
        import tempfile
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(
                deep_checksums.verify_evidence_dir_completeness(empty), 0)


class DeepChecksumsCompanionRun(TempCase):
    """End-to-end: a completed Companion run must fail verify after tamper."""

    def _completed_run(self):
        outcome = self.run_companion()
        self.assertTrue(outcome.completed)
        return outcome.out_dir

    def test_clean_completed_run_still_verifies(self):
        out = self._completed_run()
        result = verifier.verify(out)
        self.assertTrue(result.ok)

    def test_tampered_nested_checksum_target_fails_companion_verify(self):
        out = self._completed_run()
        # tamper a file listed ONLY in the coordinator's nested checksum
        # file, never in the top-level REQUIRED_PATHS — before this repair,
        # companion verify returned ok on exactly this tamper (RT-004)
        target = os.path.join(out, "coordinator_output",
                              "workflow_request_copy.json")
        with open(target, "rb") as handle:
            data = handle.read()
        canonical.atomic_write_bytes(target, data + b" ")
        with self.assertRaises(VerifyError):
            verifier.verify(out)
