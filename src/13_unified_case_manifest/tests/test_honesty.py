import os

from unified_manifest_lib import canonical, verifier, versions
from unified_manifest_lib.errors import VerifyError
from tests._helpers import TempCase

COORD = versions.SOURCE_TYPE_COORDINATOR


class TestHonesty(TempCase):
    def _out(self):
        return self.build_output(COORD, self.coord_source())

    def test_clean_passes(self):
        self.assertTrue(verifier.verify(self._out()).ok)

    def test_truth_claim_in_manifest_fails(self):
        out = self._out()
        man = canonical.load_json(os.path.join(out, "unified_case_manifest.json"))
        man["known_limitations"].append("The evidence is true.")
        canonical.write_canonical(os.path.join(out, "unified_case_manifest.json"), man)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_truth_claim_in_source_index_fails(self):
        out = self._out()
        idx = canonical.load_json(os.path.join(out, "source_index.json"))
        idx["notes"].append("The source is trusted.")
        canonical.write_canonical(os.path.join(out, "source_index.json"), idx)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_truth_claim_flag_in_manifest_fails(self):
        out = self._out()
        man = canonical.load_json(os.path.join(out, "unified_case_manifest.json"))
        man["source_artifacts"][0]["truth_claim"] = True
        canonical.write_canonical(os.path.join(out, "unified_case_manifest.json"), man)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_negated_limitations_allowed(self):
        # the honest "does not prove ... true" lines must not trip the scan
        self.assertTrue(verifier.verify(self._out()).ok)
