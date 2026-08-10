"""Move 79 adoption-gate INTEGRATION tests (B5).

These invoke the complete named adoption gate, so they are RECURSIVE relative
to the gate and must NEVER be run by the gate itself. The named gate runs only
self_tests.py and gate_unit_tests.py; it does not run this file.

Run manually for the full Python test family:

    python3 -B verify/agreement_harness_v01/self_tests.py
    python3 -B verify/agreement_harness_v01/gate_unit_tests.py
    python3 -B verify/agreement_harness_v01/gate_integration_tests.py
"""

import os
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
NAMED_GATE = os.path.join(ROOT, "tools", "check_move79_instrument_adoption.sh")
SH = shutil.which("sh")


def _dummy_zip(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("proj/rust/Cargo.toml", b"x\n")


class NamedGateInputs(unittest.TestCase):
    """B6: both mandatory inputs are validated up front."""

    def _run(self, env_extra, drop=()):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for k in drop:
            env.pop(k, None)
        env.update(env_extra)
        return subprocess.run([SH, NAMED_GATE], cwd=ROOT, env=env,
                              capture_output=True, text=True)

    def test_missing_real_move78_is_usage(self):
        tmp = tempfile.mkdtemp()
        try:
            d = os.path.join(tmp, "d.zip")
            _dummy_zip(d)
            r = self._run({"REAL_705": d}, drop=("REAL_MOVE78",))
            self.assertEqual(r.returncode, 2, r.stdout[-300:])
            self.assertIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: USAGE", r.stdout)
            self.assertIn("REAL_MOVE78", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_real_705_is_usage(self):
        tmp = tempfile.mkdtemp()
        try:
            d = os.path.join(tmp, "d.zip")
            _dummy_zip(d)
            r = self._run({"REAL_MOVE78": d}, drop=("REAL_705",))
            self.assertEqual(r.returncode, 2, r.stdout[-300:])
            self.assertIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: USAGE", r.stdout)
            self.assertIn("REAL_705", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class NamedGateBootstrap(unittest.TestCase):
    """The trusted bootstrap runs FIRST, from the literal Termux prefix. Off
    Termux the gate cannot establish trust and refuses to fabricate a verdict."""

    def _run(self, env_extra, drop=()):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for k in drop:
            env.pop(k, None)
        env.update(env_extra)
        return subprocess.run([SH, NAMED_GATE], cwd=ROOT, env=env,
                              capture_output=True, text=True)

    def test_named_gate_missing_preload_outcome_matches_host(self):
        # Authoritative user-facing contract for a missing production preload,
        # with no host inference baked into an expectation:
        #   - real Termux (literal readlink + prefix present, no preload) ->
        #     MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (missing Termux exec
        #     preload) and exit 1;
        #   - desktop (literal readlink absent) -> the gate refuses at script
        #     canonicalisation with INCONCLUSIVE_RUST_UNAVAILABLE / exit 3.
        literal_rl = "/data/data/com.termux/files/usr/bin/readlink"
        literal_pfx = "/data/data/com.termux/files/usr"
        tmp = tempfile.mkdtemp()
        try:
            dm = os.path.join(tmp, "m.txt")
            with open(dm, "w") as h:
                h.write("x")
            r = self._run({"REAL_MOVE78": dm, "REAL_705": dm},
                          drop=("LD_PRELOAD", "PREFIX"))
            tailout = r.stdout[-600:]
            # a missing preload must never surface as a low-level exec error
            self.assertNotIn("Permission denied", r.stdout + r.stderr, tailout)
            if os.path.exists(literal_rl) and os.path.isdir(literal_pfx):
                # real Termux, no preload -> deterministic missing-preload FAIL/1
                self.assertIn(
                    "MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL "
                    "(missing Termux exec preload)", r.stdout, tailout)
                self.assertEqual(r.returncode, 1, tailout)
                for forbidden in ("INCONCLUSIVE_RUST_UNAVAILABLE",
                                  "FAIL (untrusted script path)",
                                  "FAIL (untrusted environment)"):
                    self.assertNotIn(forbidden, r.stdout, tailout)
            else:
                # desktop (literal readlink absent) -> INCONCLUSIVE/3
                self.assertIn("INCONCLUSIVE_RUST_UNAVAILABLE", r.stdout, tailout)
                self.assertEqual(r.returncode, 3, tailout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_non_termux_host_is_inconclusive(self):
        # No literal Termux prefix here -> INCONCLUSIVE, never PASS, and the
        # gate stops before any preflight/provenance (no trust, no verdict).
        tmp = tempfile.mkdtemp()
        try:
            d = os.path.join(tmp, "d.zip")
            _dummy_zip(d)
            r = self._run({"REAL_MOVE78": d, "REAL_705": d}, drop=("PREFIX",))
            self.assertEqual(r.returncode, 3, r.stdout[-400:])
            self.assertIn("INCONCLUSIVE_RUST_UNAVAILABLE", r.stdout)
            self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_hostile_fake_environment_is_rejected(self):
        # A fully-fake environment (fake PREFIX, fake PATH with fake
        # sh/python3/cargo/rustc, dummy non-ZIP archives), launched by the REAL
        # shell, must be refused with no adoption PASS and none of the fake
        # programs invoked. Off Termux the literal trusted readlink is absent,
        # so the gate refuses at the script-canonicalisation boundary
        # (INCONCLUSIVE) before it could source or run anything; the
        # PREFIX-mismatch FAIL/1 path is covered at the unit level
        # (BootstrapTrust.test_prefix_mismatch_is_rejected).
        tmp = tempfile.mkdtemp()
        try:
            dm = os.path.join(tmp, "move78.txt")
            with open(dm, "w") as h:
                h.write("not a zip")
            d5 = os.path.join(tmp, "m705.txt")
            with open(d5, "w") as h:
                h.write("not a zip")
            fp = os.path.join(tmp, "fakepfx", "bin")
            os.makedirs(fp)
            invdir = os.path.join(tmp, "inv"); os.makedirs(invdir)
            for c in ("sh", "python3", "cargo", "rustc", "readlink", "timeout",
                      "sha256sum", "mktemp", "dirname", "tr"):
                with open(os.path.join(fp, c), "w") as h:
                    h.write('#!/bin/sh\nprintf x >> "%s/%s"\nexit 0\n'
                            % (invdir, c))
                os.chmod(os.path.join(fp, c), 0o755)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                       REAL_MOVE78=dm, REAL_705=d5,
                       PREFIX=os.path.dirname(fp),
                       PATH=fp + os.pathsep + os.environ["PATH"])
            r = subprocess.run([SH, NAMED_GATE], cwd=ROOT, env=env,
                               capture_output=True, text=True)
            self.assertIn(r.returncode, (1, 3), r.stdout[-400:])
            self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
            self.assertEqual(os.listdir(invdir), [],
                             "a fake program was invoked: %s"
                             % os.listdir(invdir))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


    def test_fake_dirname_cannot_redirect_root(self):
        # B1: a fake `dirname` first on PATH tries to redirect ROOT to a
        # fabricated candidate tree (fake bootstrap/lib/flow). The gate computes
        # ROOT with shell built-ins only, so the fake is never consulted, the
        # fabricated tree is never sourced, and no adoption PASS is produced.
        tmp = tempfile.mkdtemp()
        try:
            fake_root = os.path.join(tmp, "evil")
            os.makedirs(os.path.join(fake_root, "tools"))
            marker = os.path.join(tmp, "sourced_marker")
            for f in ("gate_bootstrap.sh", "gate_lib.sh", "gate_flow.sh"):
                with open(os.path.join(fake_root, "tools", f), "w") as h:
                    h.write("#!/bin/sh\nprintf x >> '%s'\n" % marker)
            fakebin = os.path.join(tmp, "fakebin")
            os.makedirs(fakebin)
            dinv = os.path.join(tmp, "dirname_inv")
            with open(os.path.join(fakebin, "dirname"), "w") as h:
                h.write("#!/bin/sh\nprintf x >> '%s'\nprintf '%s'\n"
                        % (dinv, os.path.join(fake_root, "tools")))
            os.chmod(os.path.join(fakebin, "dirname"), 0o755)
            dm = os.path.join(tmp, "m78.txt")
            with open(dm, "w") as h:
                h.write("not a zip")
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                       REAL_MOVE78=dm, REAL_705=dm,
                       PATH=fakebin + os.pathsep + os.environ["PATH"])
            env.pop("PREFIX", None)
            r = subprocess.run([SH, NAMED_GATE], cwd=ROOT, env=env,
                               capture_output=True, text=True)
            self.assertIn(r.returncode, (1, 3), r.stdout[-400:])
            self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
            self.assertFalse(os.path.exists(marker),
                             "a fabricated tree file was sourced")
            self.assertFalse(os.path.exists(dinv),
                             "the fake dirname was invoked")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_symlink_alias_cannot_source_fake_modules(self):
        # v17-B1: a SYMLINK to the genuine gate inside an attacker tree, with
        # fake adjacent modules, must not cause the gate to source them. The
        # gate canonicalises $0 with the literal trusted readlink before
        # sourcing; off Termux (that readlink absent) it refuses at the
        # canonicalisation boundary (INCONCLUSIVE). Either way, no fabricated
        # module is sourced and no adoption PASS is produced.
        tmp = tempfile.mkdtemp()
        try:
            evil = os.path.join(tmp, "evil", "tools")
            os.makedirs(evil)
            marker = os.path.join(tmp, "fake_sourced")
            for f in ("gate_bootstrap.sh", "gate_lib.sh", "gate_flow.sh",
                      "check_package_hygiene.sh", "check_adopted_immutable.sh"):
                with open(os.path.join(evil, f), "w") as h:
                    h.write("#!/bin/sh\nprintf x >> '%s'\n" % marker)
            alias = os.path.join(evil, "check_move79_instrument_adoption.sh")
            os.symlink(NAMED_GATE, alias)
            dm = os.path.join(tmp, "m.txt")
            with open(dm, "w") as h:
                h.write("x")
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                       REAL_MOVE78=dm, REAL_705=dm)
            env.pop("PREFIX", None)
            r = subprocess.run([SH, alias], env=env,
                               capture_output=True, text=True)
            self.assertIn(r.returncode, (1, 3), r.stdout[-400:])
            self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
            self.assertFalse(os.path.exists(marker),
                             "a fabricated adjacent module was sourced")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ScriptCanonicalisation(unittest.TestCase):
    """v17-B1: the canonicalisation ALGORITHM the gate uses — readlink -f on the
    script target resolves a symlink alias to the genuine tree, and ROOT is
    derived from the real path. (The gate uses the LITERAL trusted readlink,
    only present on Termux; here the system readlink stands in to prove the
    logic that runs there.)"""

    def test_readlink_resolves_symlink_and_root_derivation(self):
        tmp = tempfile.mkdtemp()
        try:
            genuine_tools = os.path.join(tmp, "genuine", "tools")
            os.makedirs(genuine_tools)
            genuine = os.path.join(
                genuine_tools, "check_move79_instrument_adoption.sh")
            with open(genuine, "w") as h:
                h.write("#!/bin/sh\n:\n")
            evil_tools = os.path.join(tmp, "evil", "tools")
            os.makedirs(evil_tools)
            alias = os.path.join(
                evil_tools, "check_move79_instrument_adoption.sh")
            os.symlink(genuine, alias)
            # the exact shell the gate runs to canonicalise + derive ROOT:
            script = (
                'SCRIPT_REAL=$(readlink -f -- "$1"); '
                'case "$SCRIPT_REAL" in '
                '*/tools/check_move79_instrument_adoption.sh) : ;; '
                '*) echo BADPATH; exit 1 ;; esac; '
                '[ -f "$SCRIPT_REAL" ] || { echo NOTFILE; exit 1; }; '
                '_SD=${SCRIPT_REAL%/*}; ROOT=${_SD%/*}; '
                'echo "REAL=$SCRIPT_REAL"; echo "ROOT=$ROOT"')
            r = subprocess.run([SH, "-c", script, "sh", alias],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("REAL=" + os.path.realpath(genuine), r.stdout)
            self.assertIn("ROOT=" + os.path.realpath(
                os.path.join(tmp, "genuine")), r.stdout)
            self.assertNotIn(os.path.join(tmp, "evil"), r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _preload_prefix(tmp, with_lib=True):
    """A controlled trusted prefix with real coreutils, cargo/rustc stubs, and a
    REAL (empty, cleanly loadable) libtermux-exec.so so the nested-exec probe
    can run with the preload restored on a Linux desktop."""
    pfx = os.path.join(tmp, "pfx")
    os.makedirs(os.path.join(pfx, "bin"))
    os.makedirs(os.path.join(pfx, "lib"))
    for c in ("sh", "python3", "timeout", "sha256sum", "mktemp", "readlink",
              "rm", "find", "grep", "sed", "tr", "sort", "wc", "head", "cat",
              "mkdir", "chmod", "cut", "env"):
        src = shutil.which(c)
        if src:
            shutil.copy(os.path.realpath(src), os.path.join(pfx, "bin", c))
            os.chmod(os.path.join(pfx, "bin", c), 0o755)
    for c in ("cargo", "rustc"):
        p = os.path.join(pfx, "bin", c)
        with open(p, "w") as h:
            h.write('#!/bin/sh\nif [ "$1" = --version ]; then '
                    'echo "%s 1.96.0 (x)"; fi\nexit 0\n' % c)
        os.chmod(p, 0o755)
    if with_lib:
        so = os.path.join(pfx, "lib", "libtermux-exec.so")
        r = subprocess.run(["cc", "-shared", "-x", "c", "-", "-o", so],
                           input="", capture_output=True, text=True)
        if r.returncode != 0:      # fall back to a stub if no compiler
            with open(so, "wb") as h:
                h.write(b"\x7fELF")
    return pfx


# Mirrors the named gate's exact pre-trust ordering, against a controlled
# prefix, so the capture->unset->source->resolve(require=1)->restore->probe
# sequence can be exercised without the literal Termux prefix.
_ORDER_HARNESS = r"""#!/bin/sh
set -u
GATE_INHERITED_LD_PRELOAD=${LD_PRELOAD-}
printf '%s' "$GATE_INHERITED_LD_PRELOAD" > "$CAP_FILE"
unset LD_PRELOAD LD_LIBRARY_PATH PYTHONPATH PYTHONHOME 2>/dev/null || true
"$REAL_SH" -c 'printf "%s" "${LD_PRELOAD-UNSET}"' > "$CHILD_BEFORE_FILE"
[ -n "${POST_INJECT-}" ] && export LD_PRELOAD="$POST_INJECT"
. "$BOOT"
. "$LIB"
_gate_resolve_from "$PFX" "$GATE_INHERITED_LD_PRELOAD" 1
RC=$?
echo "RESOLVE_RC=$RC"
if [ "$RC" -ne 0 ]; then echo "PRELOAD_FAIL=${GATE_PRELOAD_FAIL:-}"; exit "$RC"; fi
echo "RESTORED=[${LD_PRELOAD-unset}]"
if gate_nested_exec_probe; then echo "NESTED=PASS"; else echo "NESTED=FAIL"; fi
"""


class NamedGatePreloadOrder(unittest.TestCase):
    """v20: the production ordering — capture LD_PRELOAD BEFORE unset, run
    external commands while it is absent, validate the CAPTURED value, restore
    exactly it, and hand it to the nested-exec probe."""

    def _run(self, preload_value, post_inject=None):
        tmp = tempfile.mkdtemp()
        pfx = _preload_prefix(tmp)
        cap = os.path.join(tmp, "cap")
        childf = os.path.join(tmp, "child_before")
        harness = os.path.join(tmp, "order.sh")
        with open(harness, "w") as h:
            h.write(_ORDER_HARNESS)
        env = dict(os.environ, BOOT=GATE_BOOTSTRAP, LIB=GATE_LIB, PFX=pfx,
                   REAL_SH=SH, CAP_FILE=cap, CHILD_BEFORE_FILE=childf,
                   PYTHONDONTWRITEBYTECODE="1")
        # substitute the real lib path into the requested value
        val = preload_value.replace("{LIB}",
                                    os.path.join(pfx, "lib", "libtermux-exec.so"))
        if val:
            env["LD_PRELOAD"] = val
        else:
            env.pop("LD_PRELOAD", None)
        if post_inject:
            env["POST_INJECT"] = post_inject.replace(
                "{LIB}", os.path.join(pfx, "lib", "libtermux-exec.so"))
        r = subprocess.run([SH, harness], env=env, capture_output=True,
                           text=True)
        captured = None
        if os.path.exists(cap):
            with open(cap) as h:
                captured = h.read()
        child_before = None
        if os.path.exists(childf):
            with open(childf) as h:
                child_before = h.read()
        out = r.stdout
        shutil.rmtree(tmp, ignore_errors=True)
        return r.returncode, out, captured, child_before, pfx

    def test_legitimate_preload_captured_unset_validated_restored_probed(self):
        libval = "{LIB}"
        rc, out, captured, child_before, pfx = self._run(libval)
        lib = os.path.join(pfx, "lib", "libtermux-exec.so")
        self.assertEqual(captured, lib, "preload not captured before unset")
        self.assertEqual(child_before, "UNSET",
                         "external command saw LD_PRELOAD before validation")
        self.assertIn("RESOLVE_RC=0", out)
        self.assertIn("RESTORED=[%s]" % lib, out)
        self.assertIn("NESTED=PASS", out)
        self.assertEqual(rc, 0, out)

    def test_no_post_sanitisation_read_replaces_captured(self):
        # a hostile LD_PRELOAD re-injected AFTER capture/unset must be ignored;
        # validation uses the captured legitimate value and restores only it.
        rc, out, captured, child_before, pfx = self._run(
            "{LIB}", post_inject="/tmp/evil-injected.so")
        lib = os.path.join(pfx, "lib", "libtermux-exec.so")
        self.assertEqual(captured, lib)
        self.assertIn("RESTORED=[%s]" % lib, out)
        self.assertNotIn("evil-injected", out)
        self.assertIn("NESTED=PASS", out)

    def test_empty_production_preload_fails(self):
        rc, out, captured, child_before, pfx = self._run("")
        self.assertNotEqual(rc, 0)
        self.assertIn("TERMUX_EXEC_PRELOAD_CHECK: FAIL", out)
        self.assertIn("PRELOAD_FAIL=missing", out)

    def test_injected_extra_entry_fails(self):
        rc, out, captured, child_before, pfx = self._run("{LIB}:/tmp/other.so")
        self.assertNotEqual(rc, 0)
        self.assertIn("PRELOAD_FAIL=invalid", out)

    def test_missing_library_fails(self):
        tmp = tempfile.mkdtemp()
        try:
            pfx = _preload_prefix(tmp, with_lib=False)
            cap = os.path.join(tmp, "cap"); childf = os.path.join(tmp, "cb")
            harness = os.path.join(tmp, "o.sh")
            with open(harness, "w") as h:
                h.write(_ORDER_HARNESS)
            lib = os.path.join(pfx, "lib", "libtermux-exec.so")
            env = dict(os.environ, BOOT=GATE_BOOTSTRAP, LIB=GATE_LIB, PFX=pfx,
                       REAL_SH=SH, CAP_FILE=cap, CHILD_BEFORE_FILE=childf,
                       LD_PRELOAD=lib, PYTHONDONTWRITEBYTECODE="1")
            r = subprocess.run([SH, harness], env=env, capture_output=True,
                               text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("PRELOAD_FAIL=invalid", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


_SANITISED_SUITES_HARNESS = r"""#!/bin/sh
set -u
. "$BOOT"
. "$LIB"
# establish the production-style sanitised environment against a controlled
# prefix: loader vars sanitised, the legitimate preload validated and restored,
# trusted commands resolved, PATH replaced (prefix first). A backstop dir (never
# /system/bin) supplies the desktop toolchain the suites' own subprocesses use.
_gate_test_resolve_prefix "$PFX" "$PFX/lib/libtermux-exec.so" \
    || { echo "RESOLVE_FAIL"; exit 1; }
export PATH="$PFX/bin:$BACKSTOP"
export PYTHONDONTWRITEBYTECODE=1
case ":$PATH:" in *:/system/bin:*) echo "SYSTEM_BIN_PRESENT"; exit 1 ;; esac
cd "$ROOT" || { echo "CD_FAIL"; exit 1; }
"$PFX/bin/python3" -B verify/agreement_harness_v01/self_tests.py >"$SO" 2>&1
echo "SELF_RC=$?"
"$PFX/bin/python3" -B verify/agreement_harness_v01/gate_unit_tests.py >"$UO" 2>&1
echo "UNIT_RC=$?"
"""


class SanitisedEnvSuites(unittest.TestCase):
    """Repair 3: the harness and gate-unit suites must PASS under the same
    environment the production gate establishes (preload restored, loader vars
    sanitised, PATH replaced) and must not rely on /system/bin."""

    def test_suites_pass_under_sanitised_environment(self):
        tmp = tempfile.mkdtemp()
        try:
            pfx = _preload_prefix(tmp)
            so = os.path.join(tmp, "self_out")
            uo = os.path.join(tmp, "unit_out")
            harness = os.path.join(tmp, "suites.sh")
            with open(harness, "w") as h:
                h.write(_SANITISED_SUITES_HARNESS)
            # backstop supplies the desktop toolchain (cc/as/ld/awk/...); it is
            # the inherited PATH, which on this host contains no /system/bin.
            backstop = os.environ.get("PATH", "/usr/bin:/bin")
            self.assertNotIn("/system/bin", backstop.split(os.pathsep),
                             "test host PATH unexpectedly includes /system/bin")
            env = dict(os.environ, BOOT=GATE_BOOTSTRAP, LIB=GATE_LIB, PFX=pfx,
                       ROOT=ROOT, BACKSTOP=backstop, SO=so, UO=uo,
                       PYTHONDONTWRITEBYTECODE="1")
            env.pop("LD_PRELOAD", None)
            r = subprocess.run([SH, harness], env=env, capture_output=True,
                               text=True, timeout=600)
            self.assertIn("SELF_RC=0", r.stdout,
                          "harness self-tests failed under sanitised env\n"
                          + self._tail(so))
            self.assertIn("UNIT_RC=0", r.stdout,
                          "gate-unit tests failed under sanitised env\n"
                          + self._tail(uo))
            self.assertNotIn("SYSTEM_BIN_PRESENT", r.stdout)
            # emit the required markers
            print("HARNESS_SELF_TESTS: PASS")
            print("GATE_UNIT_TESTS: PASS")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @staticmethod
    def _tail(path):
        try:
            with open(path) as h:
                return "".join(h.readlines()[-25:])
        except OSError:
            return "(no output captured)"


_TIMEOUT_HARNESS = r"""#!/bin/sh
set -u
. "$BOOT"
. "$LIB"
_gate_test_resolve_prefix "$PFX" "$PFX/lib/libtermux-exec.so" \
    || { echo "RESOLVE_FAIL"; exit 1; }
[ -f "$PROBE" ] && echo "PROBE_EXISTS=yes" || echo "PROBE_EXISTS=no"
echo "ARGV=[$TRUSTED_TIMEOUT 30 $TRUSTED_READLINK -f $PROBE]"
OUT=$("$TRUSTED_TIMEOUT" 30 "$TRUSTED_READLINK" -f "$PROBE" 2>"$ERRF"); RC=$?
echo "TIMEOUT_RC=$RC"
echo "TIMEOUT_STDOUT=$OUT"
[ -n "$OUT" ] && echo "CHILD_REACHED=yes" || echo "CHILD_REACHED=no"
printf 'TIMEOUT_STDERR='; cat "$ERRF"; echo
"""


class ProductionTimeout(unittest.TestCase):
    """TEST B (v22): the ACTUAL validated trusted timeout entrypoint launches an
    ACTUAL trusted child (readlink) under the validated libtermux-exec preload,
    with explicit rc/stdout/stderr/child-reached evidence captured. This is the
    real production claim (timeout is used for the measurements) — NOT a copied
    binary nested-exec'ing another copied binary in a bare prefix."""

    def test_trusted_timeout_launches_trusted_child_under_preload(self):
        tmp = tempfile.mkdtemp()
        try:
            pfx = _preload_prefix(tmp)
            probe = os.path.join(tmp, "probe.txt")
            with open(probe, "w") as h:
                h.write("data")
            errf = os.path.join(tmp, "err")
            harness = os.path.join(tmp, "to.sh")
            with open(harness, "w") as h:
                h.write(_TIMEOUT_HARNESS)
            env = dict(os.environ, BOOT=GATE_BOOTSTRAP, LIB=GATE_LIB, PFX=pfx,
                       PROBE=probe, ERRF=errf, PYTHONDONTWRITEBYTECODE="1")
            env.pop("LD_PRELOAD", None)
            r = subprocess.run([SH, harness], env=env, capture_output=True,
                               text=True, timeout=120)
            out = r.stdout
            # explicit evidence must be present and correct
            self.assertIn("PROBE_EXISTS=yes", out, out)
            self.assertIn("CHILD_REACHED=yes", out, out + r.stderr)
            self.assertIn("TIMEOUT_RC=0", out, out + r.stderr)
            self.assertIn("TIMEOUT_STDOUT=" + os.path.realpath(probe), out, out)
            # stderr from the timeout child must be empty
            self.assertIn("TIMEOUT_STDERR=\n", out + "\n",
                          "timeout child produced stderr:\n" + out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class NamedGateStructure(unittest.TestCase):
    """No recursion by construction."""

    def test_gate_runs_unit_tests_not_integration(self):
        with open(NAMED_GATE) as h:
            code = "\n".join(ln for ln in h.read().splitlines()
                             if not ln.lstrip().startswith("#"))
        self.assertIn("gate_unit_tests.py", code,
                      "gate does not run the gate unit tests")
        self.assertNotIn("gate_integration_tests", code,
                         "gate runs the recursive integration tests")
        self.assertNotIn("GATE_SELFTEST", code,
                         "gate still honours a GATE_SELFTEST bypass")

    def test_bootstrap_precedes_first_preflight(self):
        with open(NAMED_GATE) as h:
            code = "\n".join(ln for ln in h.read().splitlines()
                             if not ln.lstrip().startswith("#"))
        self.assertIn("gate_bootstrap", code, "gate never bootstraps trust")
        b = code.index('gate_bootstrap "$GATE_INHERITED_LD_PRELOAD"')
        p = code.index("check_package_hygiene")
        self.assertLess(b, p,
                        "trusted bootstrap does not precede the first preflight")

    def test_gate_canonicalises_script_target_with_literal_readlink(self):
        with open(NAMED_GATE) as h:
            code = "\n".join(ln for ln in h.read().splitlines()
                             if not ln.lstrip().startswith("#"))
        # canonicalise $0 with the LITERAL trusted readlink before sourcing
        self.assertIn("/data/data/com.termux/files/usr/bin/readlink", code)
        self.assertIn('-f -- "$0"', code)
        self.assertIn("SCRIPT_REAL", code)
        # ROOT derived from the real script path, not textual $0 via cd -P
        self.assertNotIn('cd -P "$_SCRIPT_DIR/.."', code)
        self.assertIn("ROOT=${_SCRIPT_DIR%/*}", code)
        # the canonicalisation happens before any module is sourced
        c = code.index("SCRIPT_REAL=")
        s = code.index(". \"$ROOT/tools/gate_bootstrap.sh\"")
        self.assertLess(c, s, "modules sourced before canonicalising $0")

    def test_preload_captured_before_unset_and_passed_to_bootstrap(self):
        with open(NAMED_GATE) as h:
            code = "\n".join(ln for ln in h.read().splitlines()
                             if not ln.lstrip().startswith("#"))
        # capture assignment exists and uses the inherited value
        self.assertIn("GATE_INHERITED_LD_PRELOAD=${LD_PRELOAD-}", code)
        cap = code.index("GATE_INHERITED_LD_PRELOAD=${LD_PRELOAD-}")
        unset = code.index("unset PYTHONPATH")
        # capture MUST occur textually before the loader-var unset
        self.assertLess(cap, unset,
                        "LD_PRELOAD unset before it is captured")
        # the captured value is what is handed to the bootstrap
        self.assertIn('gate_bootstrap "$GATE_INHERITED_LD_PRELOAD"', code)
        boot = code.index('gate_bootstrap "$GATE_INHERITED_LD_PRELOAD"')
        self.assertLess(unset, boot)
        # no post-sanitisation ${LD_PRELOAD} read feeds validation
        self.assertNotIn('gate_bootstrap "${LD_PRELOAD', code)

    def test_selftests_do_not_launch_the_named_gate(self):
        with open(os.path.join(HERE, "self_tests.py")) as h:
            self.assertNotIn("check_move79_instrument_adoption", h.read())

    def test_unit_tests_do_not_launch_the_named_gate(self):
        with open(os.path.join(HERE, "gate_unit_tests.py")) as h:
            self.assertNotIn("check_move79_instrument_adoption", h.read())


GATE_LIB = os.path.join(ROOT, "tools", "gate_lib.sh")
GATE_FLOW = os.path.join(ROOT, "tools", "gate_flow.sh")
GATE_BOOTSTRAP = os.path.join(ROOT, "tools", "gate_bootstrap.sh")


def _which(name):
    return shutil.which(name)


# Controlled full-gate fixture. It drives the REAL gate_run_flow, supplying the
# trusted interpreters and a version-correct building cargo through TRUSTED_*
# (exactly as gate_bootstrap would on Termux) and stubbing only the three named
# seams. gate_build_once_production is NOT overridden. No production
# environment-variable bypass exists; the fixture is a separate script.
_FIXTURE = r"""#!/bin/sh
set -u
. "$GATE_BOOTSTRAP"
. "$GATE_LIB"
. "$GATE_FLOW"
export EXPECT_TOTAL=85 EXPECT_AGREE=74 EXPECT_PY_ONLY=6 EXPECT_RS_ONLY=3 \
       EXPECT_DIV=2
export EXPECT_DIV_IDS="stage_manifest_json_invalid stage_report_field_missing_repaired"

# trusted commands, as bootstrap would resolve them on Termux:
TRUSTED_SH="$RTSH"; TRUSTED_PYTHON3="$RTPY"; TRUSTED_TIMEOUT="$RTTIMEOUT"
TRUSTED_MKTEMP="$RTMKTEMP"; TRUSTED_READLINK="$RTREADLINK"
TRUSTED_SHA256SUM="$RTSHA"; TRUSTED_CARGO="${RTCARGO:-}"

flow_run_provenance() { echo 'RUST_PROVENANCE_CHECK: PASS' > "$1"; return 0; }
flow_run_checker() { echo 'RUST_WORKSPACE_CHECK: PASS' > "$1"; return 0; }
flow_run_measurement() {
    printf '%s\n' "$2" >> "$FIXTURE_RECORD"
    printf 'start:%s\n' "$1" >> "${FIXTURE_ORDERLOG:-/dev/null}"
    if [ "${FIXTURE_SLEEP:-0}" != 0 ]; then
        # exec so the backgrounded PID is the real (killable) child.
        exec sleep "$FIXTURE_SLEEP"
    fi
    "$TRUSTED_PYTHON3" - "$1" "${FIXTURE_PAYLOAD_MODE:-summary}" > "$3" <<'PY'
import sys, json
order, mode = sys.argv[1], sys.argv[2]
if mode == "malformed":
    sys.stdout.write('{not valid json'); raise SystemExit(0)
if mode == "envelope":
    print(json.dumps({"execution_order": order, "overall_status": "FAIL",
     "reason_code": "CAPABILITY_GAP_CASE_NOT_ISOLATED",
     "detail": "tamper_top_level_report: out-of-scope Rust rejected at shared "
               "stage 'hashes' (DECLARED_HASH_MISMATCH)"}))
    raise SystemExit(0)
if mode == "incomplete":
    print(json.dumps({"execution_order": order, "overall_status": "FAIL",
     "reason_code": "X", "summary": {"total_cases": 85}}))
    raise SystemExit(0)
print(json.dumps({"execution_order": order, "overall_status": "FAIL",
 "reason_code": "BEHAVIOURAL_DIVERGENCE_DETECTED", "summary": {
 "total_cases": 85, "shared_agreement_cases_passed": 74,
 "python_only_cases_passed": 6, "rust_only_cases_passed": 3, "divergences": 2,
 "divergent_cases": ["stage_manifest_json_invalid",
 "stage_report_field_missing_repaired"], "unmapped_reasons": 0,
 "missing_diagnostics": 0, "rust_lane_validated": True}}))
PY
    case "${FIXTURE_STDERR_MODE:-empty}" in
        warning) printf 'ResourceWarning: simulated unclosed file\n' > "$4" ;;
        traceback) printf 'Traceback (most recent call last):\n  RuntimeError: boom\n' > "$4" ;;
        *) : > "$4" ;;
    esac
    return 1
}
gate_install_traps
gate_run_flow
"""


def _building_cargo(tmp):
    """A trusted cargo stub that builds a VERSION-CORRECT fake binary."""
    p = os.path.join(tmp, "trusted_cargo")
    with open(p, "w") as h:
        h.write('#!/bin/sh\n'
                'if [ "$1" = --version ]; then echo "cargo 1.96.0 (abc)"; exit 0; fi\n'
                'if [ "$1" = build ]; then mkdir -p target/debug; '
                'printf \'#!/bin/sh\\necho \\047{"version":"0.0.8-step79-diagnostics",'
                '"verdict":"INCONCLUSIVE"}\\047\\n\' > target/debug/witness-verify; '
                'chmod +x target/debug/witness-verify; fi\nexit 0\n')
    os.chmod(p, 0o755)
    return p


class ControlledFullGate(unittest.TestCase):
    """Blocker 3: drive the REAL gate_run_flow to a complete adoption decision
    with stub seams and trusted commands, WITHOUT any production bypass. The
    trusted production builder is never overridden."""

    def _work(self, tmp):
        work = os.path.join(tmp, "work")
        os.makedirs(os.path.join(work, "rust"))
        os.makedirs(os.path.join(work, "tools"))
        with open(os.path.join(work, "rust", "Cargo.toml"), "w") as h:
            h.write("[workspace]\n")
        shutil.copy(os.path.join(ROOT, "tools", "read_version.py"),
                    os.path.join(work, "tools", "read_version.py"))
        return work

    def _run(self, tmp, trusted_cargo=None, path_extra=None,
             stderr_mode="empty", payload_mode="summary"):
        work = self._work(tmp)
        record = os.path.join(tmp, "measure_record")
        fixture = os.path.join(tmp, "fixture.sh")
        tmpdir = os.path.join(tmp, "flowtmp")
        os.makedirs(tmpdir)
        with open(fixture, "w") as h:
            h.write(_FIXTURE)
        env = dict(os.environ, GATE_LIB=GATE_LIB, GATE_FLOW=GATE_FLOW,
                   GATE_BOOTSTRAP=GATE_BOOTSTRAP, FIXTURE_RECORD=record,
                   FIXTURE_STDERR_MODE=stderr_mode,
                   FIXTURE_PAYLOAD_MODE=payload_mode, TMPDIR=tmpdir,
                   RTSH=_which("sh"), RTPY=_which("python3"),
                   RTTIMEOUT=_which("timeout"), RTMKTEMP=_which("mktemp"),
                   RTREADLINK=_which("readlink"), RTSHA=_which("sha256sum"),
                   PYTHONDONTWRITEBYTECODE="1")
        if trusted_cargo:
            env["RTCARGO"] = trusted_cargo
        else:
            env.pop("RTCARGO", None)
        if path_extra:
            env["PATH"] = path_extra + os.pathsep + env["PATH"]
        r = subprocess.run([SH, fixture], cwd=work, env=env,
                           capture_output=True, text=True)
        rec = []
        if os.path.exists(record):
            with open(record) as h:
                rec = [ln.strip() for ln in h if ln.strip()]
        leftover = os.listdir(tmpdir)
        return r, rec, work, leftover

    def test_error_envelope_fails_closed_without_keyerror(self):
        # v27: a measurement response that is a valid error envelope (no summary)
        # must fail closed with a measurement error — never KeyError('summary'),
        # never a traceback, and never a misleading "expected 85, got ?" cascade.
        tmp = tempfile.mkdtemp()
        try:
            cargo = _building_cargo(tmp)
            r, rec, work, leftover = self._run(tmp, trusted_cargo=cargo,
                                               payload_mode="envelope")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (measurement)",
                          r.stdout)
            self.assertIn("error envelope", r.stdout)
            self.assertIn("CAPABILITY_GAP_CASE_NOT_ISOLATED", r.stdout)
            self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
            # no traceback / KeyError anywhere, and no false count cascade
            self.assertNotIn("Traceback", r.stdout + r.stderr)
            self.assertNotIn("KeyError", r.stdout + r.stderr)
            self.assertNotIn("expected 85 cases, got", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_malformed_json_fails_closed(self):
        tmp = tempfile.mkdtemp()
        try:
            cargo = _building_cargo(tmp)
            r, rec, work, leftover = self._run(tmp, trusted_cargo=cargo,
                                               payload_mode="malformed")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (measurement)",
                          r.stdout)
            self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
            self.assertNotIn("Traceback", r.stdout + r.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_incomplete_summary_fails_closed(self):
        tmp = tempfile.mkdtemp()
        try:
            cargo = _building_cargo(tmp)
            r, rec, work, leftover = self._run(tmp, trusted_cargo=cargo,
                                               payload_mode="incomplete")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: FAIL (measurement)",
                          r.stdout)
            self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
            self.assertNotIn("KeyError", r.stdout + r.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_clean_case_reaches_instrument_pass_system_fail(self):
        tmp = tempfile.mkdtemp()
        try:
            cargo = _building_cargo(tmp)
            r, rec, work, leftover = self._run(tmp, trusted_cargo=cargo)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
            self.assertIn("SYSTEM_AGREEMENT_RESULT: FAIL", r.stdout)
            self.assertIn("BEHAVIOURAL_DIVERGENCE_DETECTED", r.stdout)
            self.assertIn("exactly 2 known divergences", r.stdout)
            # all three measurements used the exact final built binary
            self.assertEqual(len(rec), 3, rec)
            self.assertEqual(set(rec), {"rust/target/debug/witness-verify"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_flow_leaves_no_temp_files(self):
        # B5: the flow removes every measurement temp it created.
        tmp = tempfile.mkdtemp()
        try:
            cargo = _building_cargo(tmp)
            r, rec, work, leftover = self._run(tmp, trusted_cargo=cargo)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertEqual(leftover, [], "flow leaked temp files: %s" % leftover)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_warning_stderr_prevents_adoption(self):
        tmp = tempfile.mkdtemp()
        try:
            cargo = _building_cargo(tmp)
            r, rec, work, leftover = self._run(tmp, trusted_cargo=cargo,
                                               stderr_mode="warning")
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_traceback_stderr_prevents_adoption(self):
        tmp = tempfile.mkdtemp()
        try:
            cargo = _building_cargo(tmp)
            r, rec, work, leftover = self._run(tmp, trusted_cargo=cargo,
                                               stderr_mode="traceback")
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_trusted_cargo_with_fake_path_is_inconclusive(self):
        # A fake PATH cargo, but NO trusted cargo -> INCONCLUSIVE; the flow
        # never uses PATH, so the fake is never invoked and no measurement runs.
        tmp = tempfile.mkdtemp()
        try:
            fakebin = os.path.join(tmp, "fakebin")
            os.makedirs(fakebin)
            fake_rec = os.path.join(tmp, "fake_inv")
            with open(os.path.join(fakebin, "cargo"), "w") as h:
                h.write("#!/bin/sh\nprintf x >> '%s'\nexit 0\n" % fake_rec)
            os.chmod(os.path.join(fakebin, "cargo"), 0o755)
            r, rec, work, leftover = self._run(tmp, trusted_cargo=None,
                                               path_extra=fakebin)
            self.assertEqual(r.returncode, 3, r.stdout)
            self.assertIn("INCONCLUSIVE_RUST_UNAVAILABLE", r.stdout)
            self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", r.stdout)
            self.assertFalse(os.path.exists(fake_rec),
                             "PATH fake cargo was invoked")
            self.assertEqual(rec, [], "measurement ran without a trusted build")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SignalHandling(unittest.TestCase):
    """B3: an interruption during a measurement cleans up and terminates
    immediately, and cannot continue into the next measurement."""

    def _work(self, tmp):
        work = os.path.join(tmp, "work")
        os.makedirs(os.path.join(work, "rust"))
        os.makedirs(os.path.join(work, "tools"))
        with open(os.path.join(work, "rust", "Cargo.toml"), "w") as h:
            h.write("[workspace]\n")
        shutil.copy(os.path.join(ROOT, "tools", "read_version.py"),
                    os.path.join(work, "tools", "read_version.py"))
        return work

    def _interrupt(self, sig):
        tmp = tempfile.mkdtemp()
        try:
            cargo = _building_cargo(tmp)
            work = self._work(tmp)
            record = os.path.join(tmp, "measure_record")
            orderlog = os.path.join(tmp, "orderlog")
            tmpdir = os.path.join(tmp, "flowtmp")
            os.makedirs(tmpdir)
            fixture = os.path.join(tmp, "fixture.sh")
            with open(fixture, "w") as h:
                h.write(_FIXTURE)
            out = open(os.path.join(tmp, "out.txt"), "w")
            env = dict(os.environ, GATE_LIB=GATE_LIB, GATE_FLOW=GATE_FLOW,
                       GATE_BOOTSTRAP=GATE_BOOTSTRAP, FIXTURE_RECORD=record,
                       FIXTURE_ORDERLOG=orderlog, FIXTURE_SLEEP="6",
                       TMPDIR=tmpdir, RTSH=_which("sh"), RTPY=_which("python3"),
                       RTTIMEOUT=_which("timeout"), RTMKTEMP=_which("mktemp"),
                       RTREADLINK=_which("readlink"), RTSHA=_which("sha256sum"),
                       RTCARGO=cargo, PYTHONDONTWRITEBYTECODE="1")
            proc = subprocess.Popen([SH, fixture], cwd=work, env=env,
                                    stdout=out, stderr=subprocess.STDOUT)
            # wait until the first measurement has started
            started = False
            for _ in range(100):
                if os.path.exists(orderlog):
                    with open(orderlog) as h:
                        if "start:original" in h.read():
                            started = True
                            break
                time.sleep(0.05)
            self.assertTrue(started, "measurement never started")
            time.sleep(0.2)
            proc.send_signal(sig)
            rc = proc.wait(timeout=10)
            out.close()
            with open(orderlog) as h:
                log = h.read()
            with open(os.path.join(tmp, "out.txt")) as h:
                stdout = h.read()
            leftover = os.listdir(tmpdir)
            return rc, log, stdout, leftover
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_TERM_stops_before_next_measurement_and_cleans(self):
        rc, log, stdout, leftover = self._interrupt(signal.SIGTERM)
        self.assertNotEqual(rc, 0, "gate did not exit nonzero on TERM")
        self.assertIn("start:original", log)
        self.assertNotIn("start:reversed", log,
                         "gate continued into the next measurement after TERM")
        self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", stdout)
        self.assertEqual(leftover, [],
                         "temp files remained after interruption: %s" % leftover)

    def test_INT_stops_before_next_measurement_and_cleans(self):
        rc, log, stdout, leftover = self._interrupt(signal.SIGINT)
        self.assertNotEqual(rc, 0, "gate did not exit nonzero on INT")
        self.assertIn("start:original", log)
        self.assertNotIn("start:reversed", log,
                         "gate continued into the next measurement after INT")
        self.assertNotIn("MOVE_79_INSTRUMENT_ADOPTION_GATE: PASS", stdout)
        self.assertEqual(leftover, [],
                         "temp files remained after interruption: %s" % leftover)


class FlowHarnessPathFixed(unittest.TestCase):
    """B3: the reviewed harness path is fixed; FLOW_H cannot redirect it."""

    def test_flow_h_env_does_not_change_harness_dir(self):
        script = ('. "%s"\n. "%s"\necho "DIR=$GATE_HARNESS_DIR"'
                  % (GATE_LIB, GATE_FLOW))
        r = subprocess.run([SH, "-c", script],
                           env=dict(os.environ, FLOW_H="/tmp/fake-harness"),
                           capture_output=True, text=True)
        self.assertIn("DIR=verify/agreement_harness_v01", r.stdout)
        self.assertNotIn("/tmp/fake-harness", r.stdout)

    def test_flow_source_does_not_read_flow_h_env(self):
        with open(GATE_FLOW) as h:
            code = "\n".join(ln for ln in h.read().splitlines()
                             if not ln.lstrip().startswith("#"))
        self.assertNotIn("${FLOW_H", code)
        self.assertNotIn("$FLOW_H", code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
