# aletheia_odin_bridge/odin_validator.py
# Subprocess boundary to frozen ODIN `validate-claims`. Injectable so unit tests
# use an in-process fake. Writes the candidate claims to a temp file and runs the
# real ODIN validator over them.

import json
import os
import subprocess
import sys
import tempfile

from aletheia_odin_bridge.errors import (
    require, ComponentPathError, OdinValidateError)

ODIN_CLI = "odin.py"


class SubprocessOdinValidator:
    """Runs frozen ODIN `validate-claims --claims` as a subprocess."""

    def __init__(self, odin_root):
        self._root = odin_root

    def validate(self, claim_set):
        cli = os.path.join(self._root, ODIN_CLI)
        require(os.path.isfile(cli), f"ODIN CLI not found: {cli!r}",
                ComponentPathError, reason="ODIN_CLI_MISSING")
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8")
        try:
            json.dump(claim_set, tmp)
            tmp.flush()
            tmp.close()
            argv = [sys.executable, cli, "validate-claims", "--claims", tmp.name]
            new_session = {"start_new_session": True} if os.name == "posix" else {}
            try:
                proc = subprocess.Popen(
                    argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL, close_fds=True, text=True,
                    **new_session)
                out, err = proc.communicate(timeout=120)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except OSError:
                    pass
                raise OdinValidateError("ODIN_VALIDATE_TIMEOUT",
                                        "ODIN validate-claims timed out")
            except OSError as e:
                raise OdinValidateError("ODIN_VALIDATE_SPAWN_FAILED", str(e))
            if rc != 0:
                raise OdinValidateError(
                    "ODIN_VALIDATE_FAILED",
                    f"ODIN validate-claims failed (rc={rc}): "
                    f"{(err or out or '').strip().splitlines()[-1:]}")
            return True
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
