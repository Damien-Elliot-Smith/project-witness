import selfcheck
from tests._helpers import TempCase


class TestSelfcheck(TempCase):
    def test_selfcheck_passes(self):
        self.assertEqual(selfcheck.main(), 0)
