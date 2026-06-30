import os

from stack_verifier_lib import report as report_mod
from stack_verifier_lib.errors import CheckError
from tests._helpers import TempCase, COORD


class TestSourceVerifier(TempCase):
    def test_source_checksum_mismatch_refused(self):
        src = self.coord_source()
        # corrupt a file that is NOT canonical-checked by structure but IS hashed
        path = os.path.join(src, "sentinel_run", "run_report.json")
        with open(path, "ab") as h:
            h.write(b" ")
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, src)

    def test_non_workflow_completed_refused(self):
        src = self.coord_source(workflow_status="FAILED_SENTINEL")
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, src)
