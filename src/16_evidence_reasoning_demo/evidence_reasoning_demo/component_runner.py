# evidence_reasoning_demo/component_runner.py
# The boundary to the four frozen components. At runtime each operation is invoked
# via subprocess against the real frozen CLI. The runner is injectable so unit
# tests use an in-process fake (the default suite never spawns subprocesses).
#
# A runner exposes:
#   aletheia_bundle(evidence_file, case_id, evidence_id, out_dir)
#   aletheia_verify(bundle_dir)
#   bridge_convert(aletheia_root, odin_root, bundle_dir, out_dir)
#   bridge_verify(run_dir)
#   odin_reason(claims_path, out_dir)
#   odin_verify(run_dir)
# Each returns True on success or raises StepError(<demo_status>, msg) on failure.

import os
import subprocess
import sys

from evidence_reasoning_demo.errors import require, StepError, ComponentPathError
from evidence_reasoning_demo import versions


def _run(argv, demo_status_on_fail, timeout=180):
    new_session = {"start_new_session": True} if os.name == "posix" else {}
    try:
        proc = subprocess.Popen(
            argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL, close_fds=True, text=True, **new_session)
        out, err = proc.communicate(timeout=timeout)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass
        raise StepError(demo_status_on_fail, f"timed out: {argv[:3]}")
    except OSError as e:
        raise StepError(demo_status_on_fail, f"spawn failed: {e}")
    if rc != 0:
        tail = (err or out or "").strip().splitlines()[-1:]
        raise StepError(demo_status_on_fail,
                        f"component failed (rc={rc}): {tail}")
    return True


class SubprocessComponentRunner:
    """Runs the real frozen component CLIs via subprocess."""

    def __init__(self, *, aletheia_root, bridge_root, odin_root):
        self.aletheia_root = aletheia_root
        self.bridge_root = bridge_root
        self.odin_root = odin_root

    def _cli(self, root, name, reason):
        cli = os.path.join(root, name)
        require(os.path.isfile(cli), f"component CLI not found: {cli!r}",
                ComponentPathError, reason=reason)
        return cli

    def aletheia_bundle(self, evidence_file, case_id, evidence_id, out_dir):
        cli = self._cli(self.aletheia_root, "aletheia.py", "ALETHEIA_CLI_MISSING")
        return _run([sys.executable, cli, "bundle-file", "--file", evidence_file,
                     "--case-id", case_id, "--evidence-id", evidence_id,
                     "--out", out_dir], versions.FAILED_ALETHEIA_BUNDLE)

    def aletheia_verify(self, bundle_dir):
        cli = self._cli(self.aletheia_root, "aletheia.py", "ALETHEIA_CLI_MISSING")
        return _run([sys.executable, cli, "verify", "--bundle", bundle_dir],
                    versions.FAILED_ALETHEIA_VERIFY)

    def bridge_convert(self, aletheia_root, odin_root, bundle_dir, out_dir):
        cli = self._cli(self.bridge_root, "bridge.py", "BRIDGE_CLI_MISSING")
        return _run([sys.executable, cli, "convert",
                     "--aletheia-root", aletheia_root, "--odin-root", odin_root,
                     "--bundle", bundle_dir, "--out", out_dir],
                    versions.FAILED_BRIDGE_CONVERT)

    def bridge_verify(self, run_dir):
        cli = self._cli(self.bridge_root, "bridge.py", "BRIDGE_CLI_MISSING")
        return _run([sys.executable, cli, "verify", "--run", run_dir],
                    versions.FAILED_BRIDGE_VERIFY)

    def odin_reason(self, claims_path, out_dir):
        cli = self._cli(self.odin_root, "odin.py", "ODIN_CLI_MISSING")
        return _run([sys.executable, cli, "reason", "--claims", claims_path,
                     "--out", out_dir], versions.FAILED_ODIN_REASON)

    def odin_verify(self, run_dir):
        cli = self._cli(self.odin_root, "odin.py", "ODIN_CLI_MISSING")
        return _run([sys.executable, cli, "verify", "--run", run_dir],
                    versions.FAILED_ODIN_VERIFY)
