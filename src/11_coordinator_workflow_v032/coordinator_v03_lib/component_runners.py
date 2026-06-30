"""Lower-component runners for Coordinator v0.3.

FakeComponentRunner    -- deterministic, in-process; used by the default unit
                          tests and selfcheck. No subprocesses, no real frozen
                          component folders.
SubprocessComponentRunner -- documented adapter that would call frozen components
                          via subprocess. Used only in the manual integration
                          smoke test; NOT part of the freeze gate.
"""

import hashlib
import json
import os
import subprocess
import sys

from . import canonical
from .errors import (
    SENTINEL_PASS_STRICT, ALETHEIA_VERIFIED_PRESENT, BRIDGE_CONVERTED,
    ODIN_CONSISTENT, ODIN_CONTRADICTION, ODIN_INVALID_INPUT,
    HISTOR_SENTINEL, HISTOR_ALETHEIA, HISTOR_ODIN, CASE_BUNDLE_VERIFIED,
)

_PREDICATES = ["evidence.present", "evidence.integrity_verified"]


class ComponentResult:
    def __init__(self, ok, status, detail=""):
        self.ok = bool(ok)
        self.status = status
        self.detail = detail


class WorkflowContext:
    def __init__(self, out_dir, case_directory_name, evidence_id, evidence_file):
        self.out_dir = out_dir
        self.case_directory_name = case_directory_name
        self.evidence_id = evidence_id
        self.evidence_file = evidence_file
        self.case_id = None


def _derive_case_id(case_directory_name):
    digest = hashlib.sha256(case_directory_name.encode("utf-8")).hexdigest()
    return "case_" + digest[:16]


class FakeComponentRunner:
    """Deterministic in-process stand-in for the frozen lower components."""

    def __init__(self, fail_op=None, odin_status=ODIN_CONSISTENT,
                 case_bundle_status=CASE_BUNDLE_VERIFIED):
        self.fail_op = fail_op
        self.odin_status = odin_status
        self.case_bundle_status = case_bundle_status

    def _write(self, ctx, rel, obj):
        path = os.path.join(ctx.out_dir, rel)
        canonical.write_canonical(path, obj)

    def sentinel_create_directory(self, ctx):
        if self.fail_op == "SENTINEL_CREATE_DIRECTORY":
            return ComponentResult(False, "FAIL")
        ctx.case_id = _derive_case_id(ctx.case_directory_name)
        self._write(ctx, "sentinel_run/run_report.json", {
            "sentinel_status": SENTINEL_PASS_STRICT,
            "action_type": "CREATE_DIRECTORY",
            "case_id": ctx.case_id,
            "evidence_id": ctx.evidence_id,
            "case_directory_name": ctx.case_directory_name,
        })
        return ComponentResult(True, SENTINEL_PASS_STRICT)

    def histor_import_sentinel(self, ctx):
        if self.fail_op == "HISTOR_IMPORT_SENTINEL":
            return ComponentResult(False, "FAILED")
        self._write(ctx, "histor_sentinel_case/case_summary.json", {
            "histor_sentinel_status": HISTOR_SENTINEL,
            "case_id": ctx.case_id,
        })
        return ComponentResult(True, HISTOR_SENTINEL)

    def aletheia_bundle(self, ctx):
        if self.fail_op == "ALETHEIA_BUNDLE_FILE":
            return ComponentResult(False, "FAILED")
        self._write(ctx, "aletheia_bundle/evidence_manifest.json", {
            "aletheia_status": ALETHEIA_VERIFIED_PRESENT,
            "case_id": ctx.case_id,
            "evidence_id": ctx.evidence_id,
            "predicate": "evidence.present",
        })
        return ComponentResult(True, ALETHEIA_VERIFIED_PRESENT)

    def histor_import_aletheia(self, ctx):
        if self.fail_op == "HISTOR_IMPORT_ALETHEIA":
            return ComponentResult(False, "FAILED")
        self._write(ctx, "histor_aletheia_case/evidence_case_summary.json", {
            "histor_aletheia_status": HISTOR_ALETHEIA,
            "case_id": ctx.case_id,
            "evidence_id": ctx.evidence_id,
        })
        return ComponentResult(True, HISTOR_ALETHEIA)

    def bridge_convert(self, ctx):
        if self.fail_op == "BRIDGE_CONVERT_ALETHEIA_TO_ODIN":
            return ComponentResult(False, "FAILED")
        self._write(ctx, "bridge_output/odin_claims.json", {
            "bridge_status": BRIDGE_CONVERTED,
            "case_id": ctx.case_id,
            "evidence_id": ctx.evidence_id,
            "predicates": list(_PREDICATES),
        })
        return ComponentResult(True, BRIDGE_CONVERTED)

    def odin_reason(self, ctx):
        status = self.odin_status
        self._write(ctx, "odin_output/reasoning_report.json", {
            "odin_reasoning_status": status,
            "case_id": ctx.case_id,
            "predicates": list(_PREDICATES),
        })
        ok = status in (ODIN_CONSISTENT, ODIN_CONTRADICTION)
        if self.fail_op == "ODIN_REASON":
            ok = False
        return ComponentResult(ok, status)

    def histor_import_odin(self, ctx):
        if self.fail_op == "HISTOR_IMPORT_ODIN":
            return ComponentResult(False, "FAILED")
        self._write(ctx, "histor_odin_case/odin_case_summary.json", {
            "histor_odin_status": HISTOR_ODIN,
            "case_id": ctx.case_id,
        })
        return ComponentResult(True, HISTOR_ODIN)

    def case_bundle_build(self, ctx):
        status = self.case_bundle_status
        self._write(ctx, "case_bundle_v02/case_manifest.json", {
            "case_bundle_status": status,
            "case_id": ctx.case_id,
            "evidence_id": ctx.evidence_id,
        })
        ok = (status == CASE_BUNDLE_VERIFIED) and self.fail_op != "CASE_BUNDLE_V02_BUILD"
        return ComponentResult(ok, status)

    def case_bundle_verify(self, ctx):
        path = os.path.join(ctx.out_dir, "case_bundle_v02/case_manifest.json")
        try:
            manifest = canonical.load_json(path)
        except (OSError, ValueError):
            return ComponentResult(False, "FAILED")
        status = manifest.get("case_bundle_status")
        ok = (status == CASE_BUNDLE_VERIFIED) and self.fail_op != "CASE_BUNDLE_V02_VERIFY"
        return ComponentResult(ok, status)


# ---------------------------------------------------------------------------
# Real subprocess runner (v0.3.1 repair).
#
# v0.3.0 shipped SubprocessComponentRunner as an unwired manual-integration
# stub: every method raised NotImplementedError, so a real connected run could
# never complete (Move 30 returned DEMO_BLOCKED / MANUAL_INTEGRATION_REQUIRED).
#
# v0.3.1 wires the SAME nine workflow steps to the already-frozen lower
# component CLIs via subprocess, using the CLI contracts present in those frozen
# packages. No workflow step, action type, or Atlas term is added or changed;
# the coordinator output schema is byte-for-byte the v0.3.0 contract (the
# verifier's REQUIRED_PATHS / REQUIRED_DIRS / Atlas-status set are unchanged).
# Each method runs the real frozen CLI, reads the component's REAL status from
# its own output, and records that result under the coordinator's fixed
# vocabulary. Success is never asserted unless the real CLI exited 0 AND its
# recorded status is the expected one.
#
# An injectable executor keeps the default unit suite subprocess-free: the tests
# assert the command shapes built here without spawning any process, and the
# freeze gate never touches a real frozen component.
# ---------------------------------------------------------------------------

# coordinator subdir -> required canonical file (mirrors checksums.REQUIRED_PATHS)
SENTINEL_DIR = "sentinel_run"
HISTOR_SENTINEL_DIR = "histor_sentinel_case"
ALETHEIA_DIR = "aletheia_bundle"
HISTOR_ALETHEIA_DIR = "histor_aletheia_case"
BRIDGE_DIR = "bridge_output"
ODIN_DIR = "odin_output"
HISTOR_ODIN_DIR = "histor_odin_case"
CASE_BUNDLE_DIR = "case_bundle_v02"
# v0.3.2 evidence_id compatibility repair: the raw Case Bundle v0.2 manifest is
# preserved byte-for-byte here, and the coordinator writes a clearly-labelled
# compatibility summary in its place at case_bundle_v02/case_manifest.json.
CASE_BUNDLE_RAW_MANIFEST = "raw_case_bundle_manifest.json"
CASE_BUNDLE_COMPAT_SOURCE = "coordinator_compatibility_summary"

# run_report.json is the coordinator's required summary (carries case_id /
# evidence_id for the verifier's id-consistency check); the raw Sentinel run
# file lives alongside it and is the input handed to Histor-lite import-sentinel.
SENTINEL_RUN_FILE = SENTINEL_DIR + "/run_report.json"
SENTINEL_RAW_RUN_FILE = SENTINEL_DIR + "/sentinel_run.json"
SENTINEL_ALLOWED_SUBDIR = "_allowed_root"
SENTINEL_TARGET_REL = "case_dir"
SENTINEL_ACTION_TYPE = "CREATE_DIRECTORY"

# Sentinel replay verdicts the importer (and this runner) accept.
SENTINEL_OK_VERDICTS = ("PASS_STRICT", "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS")
ODIN_OK_STATUSES = (ODIN_CONSISTENT, ODIN_CONTRADICTION)


class ExecResult:
    """Outcome of one CLI invocation."""

    __slots__ = ("returncode", "stdout", "stderr")

    def __init__(self, returncode, stdout, stderr):
        self.returncode = int(returncode)
        self.stdout = stdout or ""
        self.stderr = stderr or ""

    @property
    def ok(self):
        return self.returncode == 0


class RealSubprocessExecutor:
    """Default executor: run a frozen CLI from its package root via subprocess.

    Determinism / hygiene: byte-compiled files are suppressed (-B,
    PYTHONDONTWRITEBYTECODE) so a real run never leaves __pycache__ inside a
    frozen root, stdin is closed, and a wall-clock timeout bounds each step.
    """

    def __init__(self, python_exe=None, timeout=600):
        self.python_exe = python_exe or sys.executable
        self.timeout = timeout

    def run(self, cwd, argv):
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        full = [self.python_exe, "-B"] + list(argv)
        proc = subprocess.run(
            full, cwd=cwd, env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=self.timeout, check=False)
        return ExecResult(proc.returncode, proc.stdout, proc.stderr)


# -- pure command builders (argv WITHOUT the python interpreter prefix) -------
# Each returns the argv the executor will run from the named component root.
# Kept as free functions so the default tests can assert command shapes with no
# subprocess and no real component folders.

def cmd_sentinel_create(run_path, run_id, request_id, target_rel, allowed_root):
    return ["sentinel.py", "create", "--run", run_path, "--run-id", run_id,
            "--request-id", request_id, "--target-path", target_rel,
            "--allowed-root", allowed_root]


def cmd_sentinel_close(run_path):
    return ["sentinel.py", "close", "--run", run_path]


def cmd_sentinel_replay(run_path):
    return ["sentinel.py", "replay", "--run", run_path]


def cmd_histor_import_sentinel(sentinel_root, run_path, out_dir):
    return ["histor_lite.py", "import-sentinel", "--sentinel-root", sentinel_root,
            "--run", run_path, "--out", out_dir]


def cmd_aletheia_bundle(evidence_file, case_id, evidence_id, out_dir):
    return ["aletheia.py", "bundle-file", "--file", evidence_file,
            "--case-id", case_id, "--evidence-id", evidence_id, "--out", out_dir]


def cmd_histor_import_aletheia(aletheia_root, bundle_dir, out_dir):
    return ["histor_aletheia.py", "import-evidence", "--aletheia-root",
            aletheia_root, "--bundle", bundle_dir, "--out", out_dir]


def cmd_bridge_convert(aletheia_root, odin_root, bundle_dir, out_dir):
    return ["bridge.py", "convert", "--aletheia-root", aletheia_root,
            "--odin-root", odin_root, "--bundle", bundle_dir, "--out", out_dir]


def cmd_odin_reason(claims_path, out_dir):
    return ["odin.py", "reason", "--claims", claims_path, "--out", out_dir]


def cmd_histor_import_odin(odin_root, run_dir, out_dir):
    return ["histor_odin.py", "import-reasoning", "--odin-root", odin_root,
            "--run", run_dir, "--out", out_dir]


def cmd_case_bundle_build(sentinel_case, aletheia_case, odin_case, out_dir):
    return ["case_bundle_v02.py", "build", "--sentinel-case", sentinel_case,
            "--aletheia-case", aletheia_case, "--odin-case", odin_case,
            "--out", out_dir]


def cmd_case_bundle_verify(bundle_dir):
    return ["case_bundle_v02.py", "verify", "--bundle", bundle_dir]


class ComponentCLIError(Exception):
    """A frozen component CLI failed or returned an unexpected status."""


class SubprocessComponentRunner:
    """Wire the nine v0.2 workflow steps to the frozen lower-component CLIs.

    component_roots: the request's component_roots dict (sentinel_root,
        histor_lite_root, aletheia_root, histor_aletheia_root, bridge_root,
        odin_root, histor_odin_root, case_bundle_v02_root, ...).
    executor: anything with .run(cwd, argv) -> ExecResult. Defaults to the real
        subprocess executor; tests inject a recording/stub executor so the
        default suite never spawns a process.

    On any failure (missing root, non-zero exit, or an unexpected real status)
    the step returns ComponentResult(ok=False, ...); the workflow then records
    the matching FAILED_* status and short-circuits, exactly like the fake
    runner's failure path. Success is recorded only when the real CLI exits 0
    and its own output carries the expected status.
    """

    def __init__(self, component_roots, executor=None, python_exe=None):
        self.component_roots = dict(component_roots or {})
        self.executor = executor or RealSubprocessExecutor(python_exe=python_exe)

    # -- helpers -------------------------------------------------------------
    def _root(self, key):
        root = self.component_roots.get(key)
        if not root or not os.path.isdir(root):
            raise ComponentCLIError(
                "component root %r is missing or not a directory: %r" % (key, root))
        return os.path.abspath(root)

    def _exec(self, root_key, argv):
        result = self.executor.run(self._root(root_key), argv)
        if not result.ok:
            raise ComponentCLIError(
                "%s exited %d: %s" % (argv[0], result.returncode,
                                      (result.stderr or result.stdout).strip()[:300]))
        return result

    @staticmethod
    def _ensure_dir(path):
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def _read_status(path, field):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get(field)

    def _out(self, ctx, rel):
        return os.path.join(ctx.out_dir, rel)

    # -- step 1: Sentinel CREATE_DIRECTORY ----------------------------------
    def sentinel_create_directory(self, ctx):
        try:
            sent_dir = self._out(ctx, SENTINEL_DIR)
            self._ensure_dir(sent_dir)
            allowed = os.path.join(sent_dir, SENTINEL_ALLOWED_SUBDIR)
            self._ensure_dir(allowed)
            raw_run = self._out(ctx, SENTINEL_RAW_RUN_FILE)
            tag = hashlib.sha256(
                (ctx.case_directory_name or "case").encode("utf-8")).hexdigest()
            run_id = "coordinator_run_" + tag[:12]
            request_id = "coordinator_req_" + tag[:12]
            # A RELATIVE target is required: Sentinel replay repoints the manifest
            # root at a fresh sandbox and replays the saved request byte-for-byte,
            # so an absolute target would fall outside the sandbox and re-derive
            # as a block (receipt-count mismatch -> FAIL -> import refused).
            self._exec("sentinel_root", cmd_sentinel_create(
                raw_run, run_id, request_id, SENTINEL_TARGET_REL, allowed))
            self._exec("sentinel_root", cmd_sentinel_close(raw_run))
            replay = self._exec("sentinel_root", cmd_sentinel_replay(raw_run))
            verdict = None
            for v in SENTINEL_OK_VERDICTS:
                if v in replay.stdout:
                    verdict = v
                    break
            if verdict is None:
                return ComponentResult(
                    False, "FAILED", "sentinel replay verdict not accepted")
            # case_id is derived from the run-file hash, identical to the formula
            # Histor-lite uses (case_ + sha256(run)[:16]); this keeps every
            # downstream case record on one consistent, real case id.
            with open(raw_run, "rb") as fh:
                run_bytes = fh.read()
            ctx.case_id = "case_" + hashlib.sha256(run_bytes).hexdigest()[:16]
            # The coordinator's required summary carries the workflow ids so the
            # verifier's id-consistency check passes; the raw Sentinel run sits
            # beside it and is the input to Histor-lite import-sentinel.
            canonical.write_canonical(self._out(ctx, SENTINEL_RUN_FILE), {
                "action_type": SENTINEL_ACTION_TYPE,
                "sentinel_status": verdict,
                "sentinel_replay_verdict": verdict,
                "case_id": ctx.case_id,
                "evidence_id": ctx.evidence_id,
                "case_directory_name": ctx.case_directory_name,
                "run_id": run_id,
                "request_id": request_id,
                "sentinel_run_file": os.path.basename(raw_run),
            })
            return ComponentResult(True, verdict)
        except (ComponentCLIError, OSError, ValueError) as exc:
            return ComponentResult(False, "FAILED", str(exc))

    # -- step 2: Histor-lite import the Sentinel run ------------------------
    def histor_import_sentinel(self, ctx):
        try:
            out_dir = self._out(ctx, HISTOR_SENTINEL_DIR)
            raw_run = self._out(ctx, SENTINEL_RAW_RUN_FILE)
            self._exec("histor_lite_root", cmd_histor_import_sentinel(
                self._root("sentinel_root"), raw_run, out_dir))
            summary = os.path.join(out_dir, "case_summary.json")
            verdict = self._read_status(summary, "sentinel_replay_verdict")
            import_status = self._read_status(summary, "import_status")
            if verdict not in SENTINEL_OK_VERDICTS or import_status != "IMPORTED":
                return ComponentResult(
                    False, "FAILED",
                    "histor sentinel import not accepted: %r/%r" % (
                        import_status, verdict))
            return ComponentResult(True, HISTOR_SENTINEL)
        except (ComponentCLIError, OSError, ValueError) as exc:
            return ComponentResult(False, "FAILED", str(exc))

    # -- step 3: Aletheia bundle the evidence file --------------------------
    def aletheia_bundle(self, ctx):
        try:
            out_dir = self._out(ctx, ALETHEIA_DIR)
            self._exec("aletheia_root", cmd_aletheia_bundle(
                ctx.evidence_file, ctx.case_id, ctx.evidence_id, out_dir))
            manifest = os.path.join(out_dir, "evidence_manifest.json")
            status = self._read_status(manifest, "evidence_status")
            if status != ALETHEIA_VERIFIED_PRESENT:
                return ComponentResult(
                    False, "FAILED", "aletheia evidence_status %r" % status)
            return ComponentResult(True, ALETHEIA_VERIFIED_PRESENT)
        except (ComponentCLIError, OSError, ValueError) as exc:
            return ComponentResult(False, "FAILED", str(exc))

    # -- step 4: Histor-lite import the Aletheia bundle ---------------------
    def histor_import_aletheia(self, ctx):
        try:
            out_dir = self._out(ctx, HISTOR_ALETHEIA_DIR)
            self._exec("histor_aletheia_root", cmd_histor_import_aletheia(
                self._root("aletheia_root"), self._out(ctx, ALETHEIA_DIR), out_dir))
            summary = os.path.join(out_dir, "evidence_case_summary.json")
            status = self._read_status(summary, "import_status")
            if status != HISTOR_ALETHEIA:
                return ComponentResult(
                    False, "FAILED", "histor aletheia import_status %r" % status)
            return ComponentResult(True, HISTOR_ALETHEIA)
        except (ComponentCLIError, OSError, ValueError) as exc:
            return ComponentResult(False, "FAILED", str(exc))

    # -- step 5: Bridge convert Aletheia bundle to ODIN claims --------------
    def bridge_convert(self, ctx):
        try:
            out_dir = self._out(ctx, BRIDGE_DIR)
            self._exec("bridge_root", cmd_bridge_convert(
                self._root("aletheia_root"), self._root("odin_root"),
                self._out(ctx, ALETHEIA_DIR), out_dir))
            report = os.path.join(out_dir, "bridge_report.json")
            status = self._read_status(report, "bridge_status")
            if status != BRIDGE_CONVERTED:
                return ComponentResult(
                    False, "FAILED", "bridge_status %r" % status)
            return ComponentResult(True, BRIDGE_CONVERTED)
        except (ComponentCLIError, OSError, ValueError) as exc:
            return ComponentResult(False, "FAILED", str(exc))

    # -- step 6: ODIN reason over the bridged claims ------------------------
    def odin_reason(self, ctx):
        try:
            out_dir = self._out(ctx, ODIN_DIR)
            claims = os.path.join(self._out(ctx, BRIDGE_DIR), "odin_claims.json")
            self._exec("odin_root", cmd_odin_reason(claims, out_dir))
            report = os.path.join(out_dir, "reasoning_report.json")
            status = self._read_status(report, "reasoning_status")
            if status not in ODIN_OK_STATUSES:
                return ComponentResult(
                    False, status or "FAILED", "odin reasoning_status %r" % status)
            # CONSISTENT or CONTRADICTION_DETECTED are both real, accepted
            # outcomes; the genuine value is reported, never normalised.
            return ComponentResult(True, status)
        except (ComponentCLIError, OSError, ValueError) as exc:
            return ComponentResult(False, "FAILED", str(exc))

    # -- step 7: Histor-lite import the ODIN reasoning run ------------------
    def histor_import_odin(self, ctx):
        try:
            out_dir = self._out(ctx, HISTOR_ODIN_DIR)
            self._exec("histor_odin_root", cmd_histor_import_odin(
                self._root("odin_root"), self._out(ctx, ODIN_DIR), out_dir))
            summary = os.path.join(out_dir, "odin_case_summary.json")
            status = self._read_status(summary, "import_status")
            if status != HISTOR_ODIN:
                return ComponentResult(
                    False, "FAILED", "histor odin import_status %r" % status)
            return ComponentResult(True, HISTOR_ODIN)
        except (ComponentCLIError, OSError, ValueError) as exc:
            return ComponentResult(False, "FAILED", str(exc))

    # -- step 8: Case Bundle v0.2 build ------------------------------------
    def case_bundle_build(self, ctx):
        try:
            out_dir = self._out(ctx, CASE_BUNDLE_DIR)
            self._exec("case_bundle_v02_root", cmd_case_bundle_build(
                self._out(ctx, HISTOR_SENTINEL_DIR),
                self._out(ctx, HISTOR_ALETHEIA_DIR),
                self._out(ctx, HISTOR_ODIN_DIR), out_dir))
            manifest = os.path.join(out_dir, "case_manifest.json")
            status = self._read_status(manifest, "bundle_status")
            if status != CASE_BUNDLE_VERIFIED:
                return ComponentResult(
                    False, status or "FAILED", "case bundle build %r" % status)
            return ComponentResult(True, CASE_BUNDLE_VERIFIED)
        except (ComponentCLIError, OSError, ValueError) as exc:
            return ComponentResult(False, "FAILED", str(exc))

    # -- step 9: Case Bundle v0.2 verify -----------------------------------
    def case_bundle_verify(self, ctx):
        try:
            bundle = self._out(ctx, CASE_BUNDLE_DIR)
            self._exec("case_bundle_v02_root", cmd_case_bundle_verify(bundle))
            manifest_path = os.path.join(bundle, "case_manifest.json")
            with open(manifest_path, "rb") as fh:
                raw_bytes = fh.read()
            raw = json.loads(raw_bytes.decode("utf-8"))
            status = raw.get("bundle_status")
            if status != CASE_BUNDLE_VERIFIED:
                return ComponentResult(
                    False, status or "FAILED", "case bundle verify %r" % status)
            # Honesty guard: the real Case Bundle case_id must already match the
            # workflow case_id before we augment anything.
            if raw.get("case_id") != ctx.case_id:
                return ComponentResult(
                    False, "FAILED", "case bundle case_id mismatch")
            # Only AFTER a real BUNDLED_VERIFIED_CASE: preserve the raw Case
            # Bundle manifest byte-for-byte, then write a coordinator
            # compatibility summary carrying the workflow evidence_id. Case
            # Bundle v0.2 records case_id + bundle_status but no evidence_id;
            # Unified Manifest v0.1 and Stack Verifier v0.1 require it. The
            # summary is explicitly labelled so no reader mistakes it for native
            # Case Bundle output.
            canonical.atomic_write_bytes(
                os.path.join(bundle, CASE_BUNDLE_RAW_MANIFEST), raw_bytes)
            summary = dict(raw)
            summary["evidence_id"] = ctx.evidence_id
            summary["source"] = CASE_BUNDLE_COMPAT_SOURCE
            summary["raw_case_bundle_manifest_preserved"] = True
            summary["raw_case_bundle_manifest"] = CASE_BUNDLE_RAW_MANIFEST
            canonical.write_canonical(manifest_path, summary)
            return ComponentResult(True, CASE_BUNDLE_VERIFIED)
        except (ComponentCLIError, OSError, ValueError) as exc:
            return ComponentResult(False, "FAILED", str(exc))
