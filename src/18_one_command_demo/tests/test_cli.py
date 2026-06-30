import contextlib
import io
import os

import one_command_demo
import verify_one_command_demo
from one_command_demo_lib import engine, checksums
from one_command_demo_lib.runner import FakeConnectedDemoRunner
from tests._helpers import WrapperCase


class TestCli(WrapperCase):
    def test_help_works(self):
        for argv in (["-h"], ["run", "-h"], ["selfcheck", "-h"]):
            buf = io.StringIO()
            with self.assertRaises(SystemExit) as ctx:
                with contextlib.redirect_stdout(buf):
                    one_command_demo.main(argv)
            self.assertEqual(ctx.exception.code, 0)
            self.assertIn("usage", buf.getvalue().lower())

    def test_verify_cli_on_good_output(self):
        tmp, cfg, _ = self.make_config()
        out = self.out_dir(tmp)
        engine.run_wrapper(cfg, out, runner=FakeConnectedDemoRunner(honest=True))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = verify_one_command_demo.main(["--run", out])
        self.assertEqual(rc, 0)
        self.assertIn("\"verify_ok\": true", buf.getvalue())

    def test_selfcheck_cli(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = one_command_demo.main(["selfcheck"])
        self.assertEqual(rc, 0)
        self.assertIn("all gates passed", buf.getvalue())
