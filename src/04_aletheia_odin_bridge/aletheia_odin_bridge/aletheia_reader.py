# aletheia_odin_bridge/aletheia_reader.py
# Read + validate an Aletheia v0.1 evidence_manifest.json, and provide the
# subprocess boundary to frozen Aletheia's `verify`. The runner is injectable so
# unit tests use an in-process fake (no subprocess-heavy default test suite).

import json
import os
import subprocess
import sys

from aletheia_odin_bridge.errors import (
    require, ManifestError, ComponentPathError, AletheiaVerifyError)
from aletheia_odin_bridge.validation import validate_id, is_valid_sha256
from aletheia_odin_bridge import versions

ALETHEIA_CLI = "aletheia.py"
MANIFEST_NAME = "evidence_manifest.json"

# The Aletheia v0.1 manifest fields the bridge relies on (a subset must be
# present and well-formed; the bridge does not re-impose Aletheia's full schema).
_REQUIRED_FIELDS = ("evidence_id", "case_id", "evidence_status",
                    "bundled_file_sha256")


def read_manifest(bundle_dir) -> dict:
    """Load and validate the Aletheia manifest from a bundle directory. Raises
    ManifestError on any problem. Does NOT check evidence_status here."""
    path = os.path.join(bundle_dir, MANIFEST_NAME)
    require(os.path.isfile(path), f"missing {MANIFEST_NAME} in bundle",
            ManifestError, reason="MANIFEST_MISSING")
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:  # noqa: BLE001
        raise ManifestError("MANIFEST_MALFORMED",
                            f"{MANIFEST_NAME} is not valid JSON: {e}")
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest) -> dict:
    """Structural validation of the fields the bridge uses."""
    require(isinstance(manifest, dict), "manifest must be a JSON object",
            ManifestError, reason="MANIFEST_NOT_OBJECT")
    for f in _REQUIRED_FIELDS:
        require(f in manifest, f"manifest missing field {f!r}",
                ManifestError, reason="MANIFEST_FIELD_MISSING")
    validate_id(manifest["evidence_id"], label="evidence_id")
    validate_id(manifest["case_id"], label="case_id")
    require(is_valid_sha256(manifest["bundled_file_sha256"]),
            "manifest bundled_file_sha256 is not a valid lowercase sha256",
            ManifestError, reason="MANIFEST_SHA256_INVALID")
    require(isinstance(manifest["evidence_status"], str),
            "manifest evidence_status must be a string",
            ManifestError, reason="MANIFEST_STATUS_TYPE")
    return manifest


def require_verified_present(manifest) -> None:
    require(manifest["evidence_status"] == versions.ALETHEIA_VERIFIED_PRESENT,
            f"Aletheia evidence_status {manifest['evidence_status']!r} is not "
            f"{versions.ALETHEIA_VERIFIED_PRESENT}; refusing to convert",
            ManifestError, reason="STATUS_NOT_VERIFIED_PRESENT")


class SubprocessAletheiaVerifier:
    """Runs frozen Aletheia `verify --bundle` as a subprocess."""

    def __init__(self, aletheia_root):
        self._root = aletheia_root

    def verify(self, bundle_dir):
        cli = os.path.join(self._root, ALETHEIA_CLI)
        require(os.path.isfile(cli), f"Aletheia CLI not found: {cli!r}",
                ComponentPathError, reason="ALETHEIA_CLI_MISSING")
        argv = [sys.executable, cli, "verify", "--bundle", bundle_dir]
        new_session = {"start_new_session": True} if os.name == "posix" else {}
        try:
            proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL, close_fds=True, text=True, **new_session)
            out, err = proc.communicate(timeout=120)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass
            raise AletheiaVerifyError("ALETHEIA_VERIFY_TIMEOUT",
                                      "Aletheia verify timed out")
        except OSError as e:
            raise AletheiaVerifyError("ALETHEIA_VERIFY_SPAWN_FAILED", str(e))
        if rc != 0:
            raise AletheiaVerifyError(
                "ALETHEIA_VERIFY_FAILED",
                f"Aletheia verify failed (rc={rc}): "
                f"{(err or out or '').strip().splitlines()[-1:]}")
        return True
