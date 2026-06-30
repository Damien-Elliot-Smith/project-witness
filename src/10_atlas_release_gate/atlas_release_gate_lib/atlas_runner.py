"""Atlas runner abstraction.

FakeAtlasRunner   -- deterministic, in-process; used by the default unit tests
                     and selfcheck. No subprocesses, no real frozen Atlas needed.
SubprocessAtlasRunner -- thin, best-effort adapter that calls a frozen Atlas v0.1
                     via subprocess. It is NOT part of the freeze gate and is
                     exercised only in the documented manual smoke test.
"""

import os

from . import canonical
from .checksums import sha256_bytes


class AtlasRunResult:
    def __init__(self, ok, detail=""):
        self.ok = bool(ok)
        self.detail = detail


def _registry_path(atlas_root):
    return os.path.join(atlas_root, "registry", "atlas_registry.json")


class FakeAtlasRunner:
    """Deterministic in-process Atlas stand-in.

    Failure-injection flags let tests force each verification stage to fail.
    """

    def __init__(self, fail_registry=False, fail_export=False,
                 fail_export_verify=False, corrupt_export=False):
        self.fail_registry = fail_registry
        self.fail_export = fail_export
        self.fail_export_verify = fail_export_verify
        self.corrupt_export = corrupt_export

    def verify_registry(self, atlas_root):
        if self.fail_registry:
            return AtlasRunResult(False, "forced registry verify failure")
        path = _registry_path(atlas_root)
        if not os.path.isfile(path):
            return AtlasRunResult(False, "registry file missing")
        try:
            obj = canonical.load_json(path)
        except ValueError:
            return AtlasRunResult(False, "registry is not valid JSON")
        if not isinstance(obj, dict):
            return AtlasRunResult(False, "registry root is not an object")
        return AtlasRunResult(True, "registry verified")

    def export_registry(self, atlas_root, export_dir):
        if self.fail_export:
            return AtlasRunResult(False, "forced export failure")
        os.makedirs(export_dir, exist_ok=True)
        registry = canonical.load_json(_registry_path(atlas_root))
        copy_bytes = canonical.canonical_bytes(registry)
        if self.corrupt_export:
            copy_bytes = copy_bytes + b" "  # makes the copy non-canonical
        terms = registry.get("terms", {})
        term_count = len(terms) if isinstance(terms, (dict, list)) else 0
        summary = {
            "atlas_summary_version": "0.1.0",
            "checked_component": "atlas_registry",
            "checked_component_version": "0.1.0",
            "term_count": term_count,
        }
        summary_bytes = canonical.canonical_bytes(summary)
        canonical.atomic_write_bytes(
            os.path.join(export_dir, "atlas_registry_copy.json"), copy_bytes)
        canonical.atomic_write_bytes(
            os.path.join(export_dir, "atlas_summary.json"), summary_bytes)
        inner = [
            "%s  %s" % (sha256_bytes(copy_bytes), "atlas_registry_copy.json"),
            "%s  %s" % (sha256_bytes(summary_bytes), "atlas_summary.json"),
        ]
        inner_bytes = ("\n".join(inner) + "\n").encode("utf-8")
        canonical.atomic_write_bytes(
            os.path.join(export_dir, "atlas_checksums.txt"), inner_bytes)
        return AtlasRunResult(True, "export produced")

    def verify_export(self, export_dir):
        if self.fail_export_verify:
            return AtlasRunResult(False, "forced export verify failure")
        try:
            copy_bytes = canonical.read_bytes(
                os.path.join(export_dir, "atlas_registry_copy.json"))
            summary_bytes = canonical.read_bytes(
                os.path.join(export_dir, "atlas_summary.json"))
            checks_text = canonical.read_bytes(
                os.path.join(export_dir, "atlas_checksums.txt")).decode("utf-8")
        except OSError:
            return AtlasRunResult(False, "export files missing")
        expected = {
            "atlas_registry_copy.json": sha256_bytes(copy_bytes),
            "atlas_summary.json": sha256_bytes(summary_bytes),
        }
        seen = {}
        for line in checks_text.splitlines():
            if not line.strip():
                continue
            parts = line.split("  ")
            if len(parts) != 2:
                return AtlasRunResult(False, "malformed inner checksum line")
            seen[parts[1]] = parts[0]
        if seen != expected:
            return AtlasRunResult(False, "inner checksum mismatch")
        if not canonical.is_canonical_bytes(copy_bytes):
            return AtlasRunResult(False, "registry copy is not canonical")
        return AtlasRunResult(True, "export verified")


class SubprocessAtlasRunner:
    """Adapter that calls a frozen Atlas Registry v0.1 via subprocess.

    Manual smoke test only -- NOT part of the freeze gate and NOT used by the
    default unit tests (which inject an in-process fake Atlas runner instead).

    The command shapes match the frozen Atlas Registry v0.1 CLI contract:

        atlas.py verify        --registry registry/atlas_registry.json
        atlas.py export        --registry registry/atlas_registry.json --out <export_dir>
        atlas.py verify-export --export <export_dir>

    'verify' and 'export' run with cwd set to the Atlas root, so the relative
    '--registry registry/atlas_registry.json' resolves. An injectable 'executor'
    lets tests assert argv/cwd wiring without launching a real subprocess.
    """

    # Relative registry path as required by the frozen Atlas CLI contract.
    REGISTRY_ARG = "registry/atlas_registry.json"

    def __init__(self, python_exe=None, atlas_script="atlas.py", executor=None):
        import sys
        self.python_exe = python_exe or sys.executable
        self.atlas_script = atlas_script
        # executor(cwd, full_argv) -> (returncode, stdout, stderr). Default: real subprocess.
        self._executor = executor
        # Remembered between calls so verify_export can run from the Atlas root
        # (where atlas.py lives). The gate always calls verify_registry /
        # export_registry before verify_export, so this is set by then.
        self._atlas_root = None

    # --- Pure argv builders (no side effects); these are what the tests assert on. ---
    def verify_registry_argv(self):
        return [self.atlas_script, "verify", "--registry", self.REGISTRY_ARG]

    def export_registry_argv(self, export_dir):
        return [self.atlas_script, "export",
                "--registry", self.REGISTRY_ARG, "--out", export_dir]

    def verify_export_argv(self, export_dir):
        return [self.atlas_script, "verify-export", "--export", export_dir]

    # --- Execution ---
    def _execute(self, cwd, argv):
        full_argv = [self.python_exe] + argv
        if self._executor is not None:
            return self._executor(cwd, full_argv)
        import subprocess
        try:
            completed = subprocess.run(
                full_argv, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as exc:
            return (1, "", "subprocess error: %s" % exc)
        return (completed.returncode,
                completed.stdout.decode("utf-8", "replace"),
                completed.stderr.decode("utf-8", "replace"))

    def verify_registry(self, atlas_root):
        self._atlas_root = atlas_root
        rc, out, err = self._execute(atlas_root, self.verify_registry_argv())
        return AtlasRunResult(rc == 0, out or err)

    def export_registry(self, atlas_root, export_dir):
        self._atlas_root = atlas_root
        export_dir = os.path.abspath(export_dir)
        rc, out, err = self._execute(atlas_root, self.export_registry_argv(export_dir))
        return AtlasRunResult(rc == 0, out or err)

    def verify_export(self, export_dir):
        export_dir = os.path.abspath(export_dir)
        # Run from the Atlas root so atlas.py is found; --export is absolute.
        cwd = self._atlas_root if self._atlas_root else os.path.dirname(export_dir)
        rc, out, err = self._execute(cwd, self.verify_export_argv(export_dir))
        return AtlasRunResult(rc == 0, out or err)
