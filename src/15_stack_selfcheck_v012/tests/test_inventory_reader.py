from stack_selfcheck_lib import canonical, report as report_mod
from stack_selfcheck_lib.errors import CheckError
from tests._helpers import TempCase


class TestInventoryReader(TempCase):
    def test_valid_inventory_accepted(self):
        report, _ = report_mod.build_selfcheck_report(self.inventory())
        self.assertEqual(report["stack_selfcheck_status"], "STACK_SELFCHECK_PASSED")

    def test_missing_inventory_refused(self):
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(self.work + "/nope.json")

    def test_non_canonical_inventory_refused(self):
        inv = self.inventory()
        with open(inv, "ab") as f:
            f.write(b" ")
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    def test_extra_top_level_field_refused(self):
        inv = self.inventory()
        data = canonical.load_json(inv); data["extra_field"] = 1
        canonical.write_canonical(inv, data)
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    def test_duplicate_component_id_refused(self):
        inv = self.inventory()
        data = canonical.load_json(inv)
        data["components"].append(dict(data["components"][0]))
        canonical.write_canonical(inv, data)
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    def test_missing_required_component_refused(self):
        inv = self.inventory()
        data = canonical.load_json(inv)
        data["components"] = [c for c in data["components"]
                              if c["component_id"] != "atlas_registry_v01"]
        canonical.write_canonical(inv, data)
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)
