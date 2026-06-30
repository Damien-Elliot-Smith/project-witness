from stack_selfcheck_lib import report as report_mod
from stack_selfcheck_lib.errors import CheckError
from tests._helpers import TempCase


class TestSidecarChecks(TempCase):
    def test_valid_sidecar_accepted(self):
        report, _ = report_mod.build_selfcheck_report(self.inventory())
        self.assertTrue(report["zip_sidecars_valid"])

    def test_sidecar_mismatch_refused(self):
        inv = self.inventory()
        # corrupt a component zip after the sidecar was written
        import os
        from stack_selfcheck_lib import canonical
        data = canonical.load_json(inv)
        zp = next(c["zip_path"] for c in data["components"] if c.get("zip_path"))
        with open(zp, "ab") as f:
            f.write(b"corrupt")
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    def test_missing_sidecar_allowed_when_optional(self):
        # the current component is marked sidecar_optional and ships no zip
        report, checked = report_mod.build_selfcheck_report(self.inventory())
        ids = {c["component_id"] for c in checked}
        self.assertIn("stack_selfcheck_v01", ids)

    def test_missing_sidecar_refused_when_required(self):
        inv = self.inventory(overrides={
            "sentinel_core_v022": {"zip_path": None, "sha256_path": None,
                                   "sidecar_optional": False}})
        # remove the keys so they read as absent
        from stack_selfcheck_lib import canonical
        data = canonical.load_json(inv)
        for c in data["components"]:
            if c["component_id"] == "sentinel_core_v022":
                c.pop("zip_path", None); c.pop("sha256_path", None)
                c["sidecar_optional"] = False
        canonical.write_canonical(inv, data)
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)
