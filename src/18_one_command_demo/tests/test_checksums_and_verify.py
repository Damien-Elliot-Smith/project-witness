import os

from one_command_demo_lib import engine, checksums, canonical, verifier
from one_command_demo_lib.errors import VerifyError
from one_command_demo_lib.runner import FakeConnectedDemoRunner
from tests._helpers import WrapperCase


def _read_lines(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read().splitlines()


class TestChecksumsAndVerify(WrapperCase):
    def good_out(self, name="out"):
        tmp, cfg, _ = self.make_config()
        out = self.out_dir(tmp, name)
        engine.run_wrapper(cfg, out, runner=FakeConnectedDemoRunner(honest=True))
        return out

    def _rewrite_checksums(self, out, text):
        canonical.atomic_write_bytes(
            os.path.join(out, checksums.CHECKSUMS_FILE), text.encode("utf-8"))

    def _lines(self, out):
        return _read_lines(os.path.join(out, checksums.CHECKSUMS_FILE))

    def test_checksums_valid(self):
        checksums.verify_checksums(self.good_out())

    def test_duplicate_checksum_key_refused(self):
        out = self.good_out()
        line = self._lines(out)[0]
        self._rewrite_checksums(out, line + "\n" + line + "\n")
        with self.assertRaises(VerifyError):
            checksums.verify_checksums(out)

    def test_unknown_checksum_key_refused(self):
        out = self.good_out()
        self._rewrite_checksums(out, "%s  extra.json\n" % ("0" * 64))
        with self.assertRaises(VerifyError):
            checksums.verify_checksums(out)

    def test_uppercase_digest_refused(self):
        out = self.good_out()
        lines = [ln.split("  ")[0].upper() + "  " + ln.split("  ")[1]
                 for ln in self._lines(out)]
        self._rewrite_checksums(out, "\n".join(lines) + "\n")
        with self.assertRaises(VerifyError):
            checksums.verify_checksums(out)

    def test_hash_mismatch_refused(self):
        out = self.good_out()
        lines = [("1" * 64) + "  " + ln.split("  ")[1] for ln in self._lines(out)]
        self._rewrite_checksums(out, "\n".join(lines) + "\n")
        with self.assertRaises(VerifyError):
            checksums.verify_checksums(out)

    def test_unknown_top_level_file_refused(self):
        out = self.good_out()
        with open(os.path.join(out, "stray.txt"), "w") as handle:
            handle.write("x")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_absolute_path_in_report_refused(self):
        out = self.good_out()
        report = canonical.load_json(os.path.join(out, checksums.REPORT_FILE))
        report["known_limitations"].append("see /home/someone/secret/path")
        canonical.write_canonical(os.path.join(out, checksums.REPORT_FILE), report)
        canonical.atomic_write_bytes(os.path.join(out, checksums.CHECKSUMS_FILE),
                                     checksums.build_checksums_text(out))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_truth_like_claim_in_report_refused(self):
        out = self.good_out()
        report = canonical.load_json(os.path.join(out, checksums.REPORT_FILE))
        report["known_limitations"].append("the evidence is true")
        canonical.write_canonical(os.path.join(out, checksums.REPORT_FILE), report)
        canonical.atomic_write_bytes(os.path.join(out, checksums.CHECKSUMS_FILE),
                                     checksums.build_checksums_text(out))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_valid_output_verifies(self):
        self.assertTrue(verifier.verify(self.good_out()))
