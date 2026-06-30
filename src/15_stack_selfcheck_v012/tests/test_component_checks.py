import os

from stack_selfcheck_lib import report as report_mod
from stack_selfcheck_lib.errors import CheckError
from tests._helpers import TempCase


class TestComponentChecks(TempCase):
    def test_missing_component_root_refused(self):
        inv = self.inventory()
        import shutil
        shutil.rmtree(self.component_root("sentinel_core_v022"))
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    def _drop(self, cid, name):
        inv = self.inventory()
        os.remove(os.path.join(self.component_root(cid), name))
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    def test_missing_readme_refused(self):
        self._drop("histor_lite_v012", "README.md")

    def test_missing_known_limitations_refused(self):
        self._drop("histor_lite_v012", "KNOWN_LIMITATIONS.md")

    def test_missing_release_commands_refused(self):
        self._drop("histor_lite_v012", "RELEASE_COMMANDS.md")

    def test_missing_cli_file_refused(self):
        self._drop("histor_lite_v012", "selfcheck.py")
