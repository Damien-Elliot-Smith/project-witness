"""Tests for the v0.3.1 real subprocess runner.

These tests assert the SubprocessComponentRunner builds the correct frozen-CLI
command shapes and records the right statuses, using an injectable recording
executor. NO subprocess is spawned and NO real frozen component is required, so
this file is part of the default freeze gate.
"""

import json
import os

from coordinator_v03_lib import component_runners as cr
from coordinator_v03_lib.component_runners import (
    SubprocessComponentRunner, WorkflowContext, ComponentResult,
    cmd_sentinel_create, cmd_sentinel_close, cmd_sentinel_replay,
    cmd_histor_import_sentinel, cmd_aletheia_bundle, cmd_histor_import_aletheia,
    cmd_bridge_convert, cmd_odin_reason, cmd_histor_import_odin,
    cmd_case_bundle_build, cmd_case_bundle_verify)
from coordinator_v03_lib.errors import (
    SENTINEL_PASS_STRICT, ALETHEIA_VERIFIED_PRESENT, BRIDGE_CONVERTED,
    ODIN_CONSISTENT, HISTOR_SENTINEL, HISTOR_ALETHEIA, HISTOR_ODIN,
    CASE_BUNDLE_VERIFIED)
from tests._helpers import TempCase


def _opt(argv, flag):
    return argv[argv.index(flag) + 1]


class _RecordingExecutor:
    """Injectable executor: records argv, writes the canned output each frozen
    CLI would produce, and never spawns a process."""

    def __init__(self):
        self.calls = []
        self.case_id = "case_x"

    def run(self, cwd, argv):
        self.calls.append((cwd, list(argv)))
        sub = argv[1] if len(argv) > 1 else ""
        if argv[0] == "sentinel.py" and sub == "create":
            # write a deterministic raw run file the runner hashes for case_id,
            # and derive the SAME case_id the runner will compute from its bytes.
            import hashlib as _h
            text = json.dumps({"run_id": _opt(argv, "--run-id"),
                               "receipts": [1, 2, 3]})
            with open(_opt(argv, "--run"), "w", encoding="utf-8") as fh:
                fh.write(text)
            self.case_id = "case_" + _h.sha256(text.encode("utf-8")).hexdigest()[:16]
            return cr.ExecResult(0, "", "")
        if argv[0] == "sentinel.py" and sub == "replay":
            return cr.ExecResult(0, "verdict: PASS_STRICT (all receipts)\n", "")
        if sub == "import-sentinel":
            self._write(_opt(argv, "--out"), "case_summary.json", {
                "case_id": self.case_id, "sentinel_replay_verdict": "PASS_STRICT",
                "import_status": "IMPORTED"})
        elif sub == "bundle-file":
            self._write(_opt(argv, "--out"), "evidence_manifest.json", {
                "case_id": _opt(argv, "--case-id"),
                "evidence_id": _opt(argv, "--evidence-id"),
                "evidence_status": "VERIFIED_PRESENT"})
        elif sub == "import-evidence":
            self._write(_opt(argv, "--out"), "evidence_case_summary.json", {
                "case_id": self.case_id, "import_status": "IMPORTED_VERIFIED_ALETHEIA"})
        elif sub == "convert":
            out = _opt(argv, "--out")
            self._write(out, "bridge_report.json", {"bridge_status": "CONVERTED"})
            self._write(out, "odin_claims.json", {"case_id": self.case_id, "claims": []})
        elif sub == "reason":
            self._write(_opt(argv, "--out"), "reasoning_report.json", {
                "reasoning_status": "CONSISTENT"})
        elif sub == "import-reasoning":
            self._write(_opt(argv, "--out"), "odin_case_summary.json", {
                "case_id": self.case_id, "import_status": "IMPORTED_VERIFIED_ODIN"})
        elif sub == "build":
            self._write(_opt(argv, "--out"), "case_manifest.json", {
                "case_id": self.case_id, "bundle_status": "BUNDLED_VERIFIED_CASE"})
        return cr.ExecResult(0, "", "")

    @staticmethod
    def _write(out_dir, name, obj):
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh)


class TestCommandShapes(TempCase):
    """The pure builders produce the exact frozen-CLI argv."""

    def test_sentinel_create_shape(self):
        self.assertEqual(
            cmd_sentinel_create("R", "rid", "qid", "case_dir", "ALLOW"),
            ["sentinel.py", "create", "--run", "R", "--run-id", "rid",
             "--request-id", "qid", "--target-path", "case_dir",
             "--allowed-root", "ALLOW"])

    def test_sentinel_create_target_is_relative(self):
        # absolute targets break Sentinel replay (sandbox repoint) -> must be relative
        self.assertFalse(os.path.isabs(cr.SENTINEL_TARGET_REL))

    def test_sentinel_close_and_replay_shape(self):
        self.assertEqual(cmd_sentinel_close("R"),
                         ["sentinel.py", "close", "--run", "R"])
        self.assertEqual(cmd_sentinel_replay("R"),
                         ["sentinel.py", "replay", "--run", "R"])

    def test_histor_import_sentinel_shape(self):
        self.assertEqual(
            cmd_histor_import_sentinel("SR", "RUN", "OUT"),
            ["histor_lite.py", "import-sentinel", "--sentinel-root", "SR",
             "--run", "RUN", "--out", "OUT"])

    def test_aletheia_bundle_shape(self):
        self.assertEqual(
            cmd_aletheia_bundle("F", "cid", "eid", "OUT"),
            ["aletheia.py", "bundle-file", "--file", "F", "--case-id", "cid",
             "--evidence-id", "eid", "--out", "OUT"])

    def test_histor_import_aletheia_shape(self):
        self.assertEqual(
            cmd_histor_import_aletheia("AR", "B", "OUT"),
            ["histor_aletheia.py", "import-evidence", "--aletheia-root", "AR",
             "--bundle", "B", "--out", "OUT"])

    def test_bridge_convert_shape(self):
        self.assertEqual(
            cmd_bridge_convert("AR", "OR", "B", "OUT"),
            ["bridge.py", "convert", "--aletheia-root", "AR", "--odin-root", "OR",
             "--bundle", "B", "--out", "OUT"])

    def test_odin_reason_shape(self):
        self.assertEqual(
            cmd_odin_reason("C", "OUT"),
            ["odin.py", "reason", "--claims", "C", "--out", "OUT"])

    def test_histor_import_odin_shape(self):
        self.assertEqual(
            cmd_histor_import_odin("OR", "RUN", "OUT"),
            ["histor_odin.py", "import-reasoning", "--odin-root", "OR",
             "--run", "RUN", "--out", "OUT"])

    def test_case_bundle_build_shape(self):
        self.assertEqual(
            cmd_case_bundle_build("S", "A", "O", "OUT"),
            ["case_bundle_v02.py", "build", "--sentinel-case", "S",
             "--aletheia-case", "A", "--odin-case", "O", "--out", "OUT"])

    def test_case_bundle_verify_shape(self):
        self.assertEqual(
            cmd_case_bundle_verify("B"),
            ["case_bundle_v02.py", "verify", "--bundle", "B"])


class TestRealRunnerWiring(TempCase):
    """The runner is wired (no NotImplementedError) and drives the CLIs in order
    with an injected executor, recording real statuses."""

    def _setup(self):
        base = os.path.join(self.work, "roots")
        keys = ("sentinel_root", "histor_lite_root", "aletheia_root",
                "histor_aletheia_root", "bridge_root", "odin_root",
                "histor_odin_root", "case_bundle_v02_root")
        roots = {}
        for k in keys:
            d = os.path.join(base, k)
            os.makedirs(d, exist_ok=True)
            roots[k] = d
        ev = os.path.join(self.work, "evidence.txt")
        with open(ev, "w", encoding="utf-8") as fh:
            fh.write("evidence")
        out = os.path.join(self.work, "out")
        os.makedirs(out, exist_ok=True)
        ctx = WorkflowContext(out, "case_demo_001", "evidence_demo_001", ev)
        ex = _RecordingExecutor()
        runner = SubprocessComponentRunner(roots, executor=ex)
        return runner, ctx, ex

    def test_full_sequence_completes_with_real_statuses(self):
        runner, ctx, ex = self._setup()
        r1 = runner.sentinel_create_directory(ctx)
        self.assertTrue(r1.ok)
        self.assertEqual(r1.status, SENTINEL_PASS_STRICT)
        self.assertTrue(ctx.case_id and ctx.case_id.startswith("case_"))
        results = [
            (runner.histor_import_sentinel(ctx), HISTOR_SENTINEL),
            (runner.aletheia_bundle(ctx), ALETHEIA_VERIFIED_PRESENT),
            (runner.histor_import_aletheia(ctx), HISTOR_ALETHEIA),
            (runner.bridge_convert(ctx), BRIDGE_CONVERTED),
            (runner.odin_reason(ctx), ODIN_CONSISTENT),
            (runner.histor_import_odin(ctx), HISTOR_ODIN),
            (runner.case_bundle_build(ctx), CASE_BUNDLE_VERIFIED),
            (runner.case_bundle_verify(ctx), CASE_BUNDLE_VERIFIED),
        ]
        for res, expected in results:
            self.assertIsInstance(res, ComponentResult)
            self.assertTrue(res.ok, res.detail)
            self.assertEqual(res.status, expected)

    def test_runner_is_not_a_stub(self):
        runner, ctx, _ = self._setup()
        # the v0.3.0 stub raised NotImplementedError; v0.3.1 must not.
        try:
            runner.sentinel_create_directory(ctx)
        except NotImplementedError:
            self.fail("SubprocessComponentRunner is still an unwired stub")

    def test_subcommand_order_matches_workflow(self):
        runner, ctx, ex = self._setup()
        runner.sentinel_create_directory(ctx)
        runner.histor_import_sentinel(ctx)
        runner.aletheia_bundle(ctx)
        runner.histor_import_aletheia(ctx)
        runner.bridge_convert(ctx)
        runner.odin_reason(ctx)
        runner.histor_import_odin(ctx)
        runner.case_bundle_build(ctx)
        runner.case_bundle_verify(ctx)
        scripts = [argv[0] for _, argv in ex.calls]
        subs = [argv[1] for _, argv in ex.calls]
        self.assertEqual(scripts[:3], ["sentinel.py", "sentinel.py", "sentinel.py"])
        self.assertEqual(subs[:3], ["create", "close", "replay"])
        self.assertIn("import-sentinel", subs)
        self.assertEqual(subs[-1], "verify")

    def test_missing_root_fails_closed_not_raises(self):
        runner, ctx, _ = self._setup()
        runner.component_roots["aletheia_root"] = "/no/such/root"
        ctx.case_id = "case_x"
        res = runner.aletheia_bundle(ctx)
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "FAILED")

    def test_nonzero_exit_fails_closed(self):
        runner, ctx, ex = self._setup()
        ctx.case_id = "case_x"

        def boom(cwd, argv):
            return cr.ExecResult(2, "", "boom")
        ex.run = boom
        res = runner.aletheia_bundle(ctx)
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "FAILED")


class TestCaseBundleCompatibilitySummary(TempCase):
    """v0.3.2: after a real BUNDLED_VERIFIED_CASE, the coordinator writes a
    labelled compatibility summary carrying evidence_id and preserves the raw
    Case Bundle manifest."""

    def _setup(self):
        base = os.path.join(self.work, "roots")
        keys = ("sentinel_root", "histor_lite_root", "aletheia_root",
                "histor_aletheia_root", "bridge_root", "odin_root",
                "histor_odin_root", "case_bundle_v02_root")
        roots = {}
        for k in keys:
            d = os.path.join(base, k)
            os.makedirs(d, exist_ok=True)
            roots[k] = d
        ev = os.path.join(self.work, "evidence.txt")
        with open(ev, "w", encoding="utf-8") as fh:
            fh.write("evidence")
        out = os.path.join(self.work, "out")
        os.makedirs(out, exist_ok=True)
        ctx = WorkflowContext(out, "case_demo_001", "evidence_demo_001", ev)
        runner = SubprocessComponentRunner(roots, executor=_RecordingExecutor())
        return runner, ctx, out

    def _run_through_case_bundle(self, runner, ctx):
        runner.sentinel_create_directory(ctx)
        runner.histor_import_sentinel(ctx)
        runner.aletheia_bundle(ctx)
        runner.histor_import_aletheia(ctx)
        runner.bridge_convert(ctx)
        runner.odin_reason(ctx)
        runner.histor_import_odin(ctx)
        runner.case_bundle_build(ctx)
        return runner.case_bundle_verify(ctx)

    def _manifest(self, out):
        with open(os.path.join(out, "case_bundle_v02", "case_manifest.json"),
                  encoding="utf-8") as fh:
            return json.load(fh)

    def test_summary_includes_evidence_id(self):
        runner, ctx, out = self._setup()
        res = self._run_through_case_bundle(runner, ctx)
        self.assertTrue(res.ok, res.detail)
        m = self._manifest(out)
        self.assertEqual(m["evidence_id"], ctx.evidence_id)
        self.assertEqual(m["case_id"], ctx.case_id)
        self.assertEqual(m["bundle_status"], "BUNDLED_VERIFIED_CASE")

    def test_summary_is_labelled_as_coordinator_summary(self):
        runner, ctx, out = self._setup()
        self._run_through_case_bundle(runner, ctx)
        m = self._manifest(out)
        self.assertEqual(m["source"], "coordinator_compatibility_summary")
        self.assertTrue(m["raw_case_bundle_manifest_preserved"])
        self.assertEqual(m["raw_case_bundle_manifest"], "raw_case_bundle_manifest.json")

    def test_raw_case_bundle_manifest_preserved_without_evidence_id(self):
        runner, ctx, out = self._setup()
        self._run_through_case_bundle(runner, ctx)
        raw_path = os.path.join(out, "case_bundle_v02", "raw_case_bundle_manifest.json")
        self.assertTrue(os.path.isfile(raw_path))
        with open(raw_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        # the raw Case Bundle manifest never carried evidence_id
        self.assertNotIn("evidence_id", raw)
        self.assertNotIn("source", raw)

    def test_summary_only_written_after_bundled_verified_case(self):
        # If the real Case Bundle did NOT return BUNDLED_VERIFIED_CASE, no summary
        # and no raw file are written, and the step fails closed.
        runner, ctx, out = self._setup()
        ctx.case_id = "case_demo_001"
        bundle = os.path.join(out, "case_bundle_v02")
        os.makedirs(bundle, exist_ok=True)
        with open(os.path.join(bundle, "case_manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"case_id": ctx.case_id, "bundle_status": "FAILED_SOMETHING"}, fh)

        class _VerifyOnly:
            def run(self, cwd, argv):
                return cr.ExecResult(0, "", "")
        runner.executor = _VerifyOnly()
        res = runner.case_bundle_verify(ctx)
        self.assertFalse(res.ok)
        self.assertFalse(os.path.exists(
            os.path.join(bundle, "raw_case_bundle_manifest.json")))
        with open(os.path.join(bundle, "case_manifest.json"), encoding="utf-8") as fh:
            m = json.load(fh)
        self.assertNotIn("evidence_id", m)
        self.assertNotIn("source", m)
