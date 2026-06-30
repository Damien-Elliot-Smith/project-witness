from companion_lib import canonical, request_builder, versions
from tests._helpers import TempCase


class TestRequest(TempCase):
    def _req(self):
        roots = {k: "/tmp/%s" % k for k in versions.COMPONENT_ROOT_KEYS}
        return request_builder.build_request(
            "case_001", "evidence_001", "/tmp/e.txt", "/tmp/cases", "case_001", roots)

    def test_request_canonical(self):
        req = self._req()
        self.assertTrue(canonical.is_canonical_bytes(canonical.canonical_bytes(req)))

    def test_request_version_is_0_3_0(self):
        self.assertEqual(self._req()["coordinator_workflow_request_version"], "0.3.0")

    def test_request_includes_atlas_registry_root(self):
        self.assertIn("atlas_registry_root", self._req()["component_roots"])

    def test_request_workflow_and_action_type(self):
        req = self._req()
        self.assertEqual(req["workflow_type"], "CREATE_EVIDENCE_REASONING_CASE")
