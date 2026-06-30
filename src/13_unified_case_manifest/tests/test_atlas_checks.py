from unified_manifest_lib import manifest as manifest_mod, versions
from unified_manifest_lib.errors import BuildError
from tests._helpers import TempCase

COORD = versions.SOURCE_TYPE_COORDINATOR


class TestAtlasChecks(TempCase):
    def _build(self, **registry_opts):
        src = self.coord_source(registry_opts=registry_opts)
        return manifest_mod.build_manifest_data(COORD, src)

    def test_missing_required_status_refused(self):
        with self.assertRaises(BuildError):
            self._build(omit_status="CONSISTENT")

    def test_missing_required_predicate_refused(self):
        with self.assertRaises(BuildError):
            self._build(omit_predicate="evidence.present")

    def test_atlas_truth_claim_status_refused(self):
        with self.assertRaises(BuildError):
            self._build(truth_claim_status=True)

    def test_atlas_truth_claim_predicate_refused(self):
        with self.assertRaises(BuildError):
            self._build(truth_claim_predicate=True)

    def test_forbidden_action_refused(self):
        with self.assertRaises(BuildError):
            self._build(forbidden_action="WRITE_FILE")
