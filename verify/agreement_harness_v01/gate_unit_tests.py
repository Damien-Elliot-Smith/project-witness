"""Move 79 adoption-gate UNIT tests (B5).

Non-recursive: none of these invoke the named adoption gate, so the gate runs
them unconditionally as a preflight without recursing. They drive the real
tools/gate_lib.sh helpers and the provenance module directly.

Covers: the marker/exit matrix, warning precedence (B2), the target/build
helpers, CARGO-override isolation of the production builder (B1), provenance
against controlled baselines incl. scope enumeration (B3) and pin metadata
(B4), and the no-cargo environment.

The recursive whole-gate tests live in gate_integration_tests.py and are NOT
run by the gate.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GATE_LIB = os.path.join(ROOT, "tools", "gate_lib.sh")
SH = shutil.which("sh")

sys.path.insert(0, os.path.join(ROOT, "tools"))
import verify_rust_provenance as PROV  # noqa: E402
sys.path.insert(0, HERE)
import gate_test_fixtures as _fixtures  # noqa: E402


GATE_BOOTSTRAP = os.path.join(ROOT, "tools", "gate_bootstrap.sh")


def _lib_call(func_args, cwd=None, env=None):
    """Source gate_bootstrap.sh + gate_lib.sh and call a function."""
    script = ". %s\n. %s\n%s \"$@\"" % (GATE_BOOTSTRAP, GATE_LIB, func_args[0])
    return subprocess.run([SH, "-c", script, "sh"] + list(func_args[1:]),
                          cwd=cwd, env=env, capture_output=True, text=True)


_COREUTILS = ("sh", "python3", "timeout", "sha256sum", "mktemp", "readlink")
# On real Termux $PREFIX/bin holds the full coreutils set; a controlled test
# prefix must copy the ones the gate uses after it narrows PATH.
_EXTRA_COREUTILS = ("rm", "find", "grep", "sed", "tr", "sort", "wc", "head",
                    "cat", "mkdir", "chmod", "ls", "dirname", "cut", "env")


def _copy_prefix(tmp, cargo_ver="1.96.0", rustc_ver="1.96.0",
                 record_cargo=None, cargo_builds=False):
    """A controlled trusted prefix: real coreutils COPIED under the prefix
    (so readlink -f stays beneath it) plus stub cargo/rustc."""
    pfx = os.path.join(tmp, "pfx")
    os.makedirs(os.path.join(pfx, "bin"))
    for c in _COREUTILS + _EXTRA_COREUTILS:
        src = shutil.which(c)
        if src:
            shutil.copy(os.path.realpath(src), os.path.join(pfx, "bin", c))
            os.chmod(os.path.join(pfx, "bin", c), 0o755)
    rec = ("printf x >> '%s'\n" % record_cargo) if record_cargo else ""
    build = ('if [ "$1" = build ]; then mkdir -p target/debug; '
             'printf "#!/bin/sh\\necho real\\n" > target/debug/witness-verify; '
             'chmod +x target/debug/witness-verify; fi\n') if cargo_builds else ""
    with open(os.path.join(pfx, "bin", "cargo"), "w") as h:
        h.write('#!/bin/sh\n%s'
                'if [ "$1" = --version ]; then echo "cargo %s (abc)"; exit 0; fi\n'
                '%sexit 0\n' % (rec, cargo_ver, build))
    os.chmod(os.path.join(pfx, "bin", "cargo"), 0o755)
    with open(os.path.join(pfx, "bin", "rustc"), "w") as h:
        h.write('#!/bin/sh\nif [ "$1" = --version ]; then '
                'echo "rustc %s (abc)"; fi\nexit 0\n' % rustc_ver)
    os.chmod(os.path.join(pfx, "bin", "rustc"), 0o755)
    return pfx


class MarkerExitMatrix(unittest.TestCase):
    """B2 marker layer: only exact marker/exit pairs are accepted."""

    def _c(self, out, rc):
        return _lib_call(["classify_workspace_marker", out, str(rc)]).stdout.strip()

    def test_pass(self):
        self.assertEqual(self._c("RUST_WORKSPACE_CHECK: PASS", 0), "PASS")

    def test_pass_wrong_exit(self):
        self.assertEqual(self._c("RUST_WORKSPACE_CHECK: PASS", 1), "FAIL")

    def test_exit0_no_marker(self):
        self.assertEqual(self._c("NOT_THE_REQUIRED_MARKER", 0), "FAIL")

    def test_unavail(self):
        self.assertEqual(
            self._c("RUST_WORKSPACE_CHECK: INCONCLUSIVE_TOOLCHAIN_UNAVAILABLE",
                    3), "UNAVAIL")

    def test_unavail_wrong_exit(self):
        self.assertEqual(
            self._c("RUST_WORKSPACE_CHECK: INCONCLUSIVE_TOOLCHAIN_UNAVAILABLE",
                    0), "FAIL")

    def test_non_standalone(self):
        self.assertEqual(self._c("x RUST_WORKSPACE_CHECK: PASS y", 0), "FAIL")

    def test_both_markers(self):
        self.assertEqual(
            self._c("RUST_WORKSPACE_CHECK: PASS\n"
                    "RUST_WORKSPACE_CHECK: INCONCLUSIVE_TOOLCHAIN_UNAVAILABLE",
                    0), "FAIL")


class WarningPrecedence(unittest.TestCase):
    """B2: any warning text forces FAIL before marker classification, so a
    warning can never be masked as PASS or INCONCLUSIVE."""

    def _r(self, out, rc):
        return _lib_call(["classify_workspace_result", out, str(rc)]).stdout.strip()

    def test_clean_pass_is_pass(self):
        self.assertEqual(self._r("RUST_WORKSPACE_CHECK: PASS", 0), "PASS")

    def test_clean_unavailable_is_unavail(self):
        self.assertEqual(
            self._r("RUST_WORKSPACE_CHECK: INCONCLUSIVE_TOOLCHAIN_UNAVAILABLE",
                    3), "UNAVAIL")

    def test_warning_plus_pass_is_fail(self):
        blob = "ResourceWarning: simulated unclosed file\n" \
               "RUST_WORKSPACE_CHECK: PASS"
        self.assertEqual(self._r(blob, 0), "FAIL")

    def test_warning_plus_unavailable_is_fail(self):
        # the exact v12 hole: warning + unavailable + exit 3 must NOT be UNAVAIL
        blob = "ResourceWarning: simulated unclosed file\n" \
               "RUST_WORKSPACE_CHECK: INCONCLUSIVE_TOOLCHAIN_UNAVAILABLE"
        self.assertEqual(self._r(blob, 3), "FAIL")

    def test_exception_ignored_is_fail(self):
        blob = "Exception ignored in: <_io.FileIO ...>\n" \
               "RUST_WORKSPACE_CHECK: PASS"
        self.assertEqual(self._r(blob, 0), "FAIL")


class _StubTree:
    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="gate_")
        os.makedirs(os.path.join(self.tmp, "rust"))
        with open(os.path.join(self.tmp, "rust", "Cargo.toml"), "w") as h:
            h.write("[workspace]\n")

    def stub_cargo(self, ok=True, makes_binary=True, record=None):
        path = os.path.join(self.tmp, "stub_%s_%s" % (ok, makes_binary))
        lines = ["#!/bin/sh\n"]
        if record:
            lines.append('printf x >> "%s"\n' % record)
        if ok and makes_binary:
            lines.append('if [ "$1" = build ]; then\n'
                         "  mkdir -p target/debug\n"
                         "  printf '#!/bin/sh\\necho stub\\n' "
                         "> target/debug/witness-verify\n"
                         "  chmod +x target/debug/witness-verify\n"
                         "fi\nexit 0\n")
        elif ok and not makes_binary:
            lines.append("exit 0\n")
        else:
            lines.append('echo "simulated build failure" >&2\nexit 101\n')
        with open(path, "w") as h:
            h.write("".join(lines))
        os.chmod(path, 0o755)
        return path

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TargetAndBuildHelpers(unittest.TestCase):
    """B3: target sequence and the stub build helper (test-only builder)."""

    def test_preexisting_target_fails(self):
        t = _StubTree()
        try:
            os.makedirs(os.path.join(t.tmp, "rust", "target", "debug"))
            self.assertNotEqual(
                _lib_call(["gate_assert_no_target"], cwd=t.tmp).returncode, 0)
        finally:
            t.close()

    def test_clean_target_removes_tree(self):
        t = _StubTree()
        try:
            os.makedirs(os.path.join(t.tmp, "rust", "target", "debug"))
            with open(os.path.join(t.tmp, "rust", "target", "debug",
                                   "witness-verify"), "w") as h:
                h.write("STALE")
            self.assertEqual(
                _lib_call(["gate_clean_target"], cwd=t.tmp).returncode, 0)
            self.assertFalse(os.path.exists(
                os.path.join(t.tmp, "rust", "target")))
        finally:
            t.close()

    def test_stub_build_produces_exactly_the_binary(self):
        t = _StubTree()
        try:
            cargo = t.stub_cargo()
            r = _lib_call(["gate_build_once_with_stub"], cwd=t.tmp,
                          env=dict(os.environ, CARGO=cargo))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(),
                             "rust/target/debug/witness-verify")
        finally:
            t.close()

    def test_failed_build_leaves_no_stale_binary(self):
        t = _StubTree()
        try:
            binp = os.path.join(t.tmp, "rust", "target", "debug",
                                "witness-verify")
            os.makedirs(os.path.dirname(binp))
            with open(binp, "w") as h:
                h.write("STALE")
            os.chmod(binp, 0o755)
            self.assertEqual(
                _lib_call(["gate_clean_target"], cwd=t.tmp).returncode, 0)
            self.assertFalse(os.path.exists(binp))
            cargo = t.stub_cargo(ok=False)
            r = _lib_call(["gate_build_once_with_stub"], cwd=t.tmp,
                          env=dict(os.environ, CARGO=cargo))
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(os.path.exists(binp))
        finally:
            t.close()

    def test_build_that_makes_no_binary_fails(self):
        t = _StubTree()
        try:
            cargo = t.stub_cargo(ok=True, makes_binary=False)
            r = _lib_call(["gate_build_once_with_stub"], cwd=t.tmp,
                          env=dict(os.environ, CARGO=cargo))
            self.assertNotEqual(r.returncode, 0)
        finally:
            t.close()


class ToolchainResolution(unittest.TestCase):
    """B1/B5: production builds only with the bootstrap-resolved TRUSTED_CARGO;
    the test-only resolver enforces under-prefix, versions, and env sanitize."""

    def _tree(self):
        t = tempfile.mkdtemp(prefix="tc_")
        os.makedirs(os.path.join(t, "rust"))
        with open(os.path.join(t, "rust", "Cargo.toml"), "w") as h:
            h.write("[workspace]\n")
        return t

    def _boot_call(self, script, cwd, env):
        return subprocess.run(
            [SH, "-c", ". %s\n. %s\n%s" % (GATE_BOOTSTRAP, GATE_LIB, script)],
            cwd=cwd, env=env, capture_output=True, text=True)

    def test_valid_prefix_resolves(self):
        work = self._tree(); pdir = tempfile.mkdtemp()
        pfx = _copy_prefix(pdir)
        try:
            r = subprocess.run(
                [SH, "-c", ". %s\n. %s\n_gate_test_resolve_prefix \"$1\" && "
                 "echo OK $TRUSTED_CARGO" % (GATE_BOOTSTRAP, GATE_LIB),
                 "sh", pfx], cwd=work, env=dict(os.environ),
                capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("OK", r.stdout)
            self.assertIn(pfx, r.stdout)
        finally:
            shutil.rmtree(work, ignore_errors=True)
            shutil.rmtree(pdir, ignore_errors=True)

    def test_production_builder_uses_TRUSTED_CARGO_ignores_path_and_cargo(self):
        work = self._tree(); pdir = tempfile.mkdtemp()
        real_rec = os.path.join(pdir, "real_inv")
        fake_rec = os.path.join(pdir, "fake_inv")
        fakebin = os.path.join(pdir, "fakebin"); os.makedirs(fakebin)
        with open(os.path.join(fakebin, "cargo"), "w") as h:
            h.write("#!/bin/sh\nprintf x >> '%s'\nexit 0\n" % fake_rec)
        os.chmod(os.path.join(fakebin, "cargo"), 0o755)
        # a trusted cargo stub that builds and records
        trusted = os.path.join(pdir, "trusted_cargo")
        with open(trusted, "w") as h:
            h.write("#!/bin/sh\nprintf x >> '%s'\n"
                    'if [ "$1" = build ]; then mkdir -p target/debug; '
                    'printf "#!/bin/sh\\necho r\\n" > target/debug/witness-verify; '
                    "chmod +x target/debug/witness-verify; fi\nexit 0\n" % real_rec)
        os.chmod(trusted, 0o755)
        try:
            env = dict(os.environ, TRUSTED_CARGO=trusted,
                       PATH=fakebin + os.pathsep + os.environ["PATH"],
                       CARGO="/nonexistent/fake", PYTHONDONTWRITEBYTECODE="1")
            r = _lib_call(["gate_build_once_production"], cwd=work, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(),
                             "rust/target/debug/witness-verify")
            self.assertFalse(os.path.exists(fake_rec),
                             "PATH/CARGO fake was invoked")
            self.assertTrue(os.path.exists(real_rec),
                            "TRUSTED_CARGO was not invoked")
        finally:
            shutil.rmtree(work, ignore_errors=True)
            shutil.rmtree(pdir, ignore_errors=True)

    def test_production_builder_without_trusted_cargo_fails(self):
        work = self._tree()
        try:
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            env.pop("TRUSTED_CARGO", None)
            r = _lib_call(["gate_build_once_production"], cwd=work, env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(os.path.exists(
                os.path.join(work, "rust", "target")))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_wrong_version_is_fail(self):
        work = self._tree(); pdir = tempfile.mkdtemp()
        pfx = _copy_prefix(pdir, cargo_ver="1.90.0")
        try:
            r = subprocess.run(
                [SH, "-c", ". %s\n. %s\n_gate_test_resolve_prefix \"$1\""
                 % (GATE_BOOTSTRAP, GATE_LIB), "sh", pfx],
                cwd=work, env=dict(os.environ), capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
        finally:
            shutil.rmtree(work, ignore_errors=True)
            shutil.rmtree(pdir, ignore_errors=True)

    def test_prefix_escape_is_fail(self):
        work = self._tree(); pdir = tempfile.mkdtemp()
        pfx = _copy_prefix(pdir)
        outside = os.path.join(pdir, "outside_cargo")
        with open(outside, "w") as h:
            h.write('#!/bin/sh\nif [ "$1" = --version ]; then '
                    'echo "cargo 1.96.0"; fi\nexit 0\n')
        os.chmod(outside, 0o755)
        os.remove(os.path.join(pfx, "bin", "cargo"))
        os.symlink(outside, os.path.join(pfx, "bin", "cargo"))
        try:
            r = subprocess.run(
                [SH, "-c", ". %s\n. %s\n_gate_test_resolve_prefix \"$1\""
                 % (GATE_BOOTSTRAP, GATE_LIB), "sh", pfx],
                cwd=work, env=dict(os.environ), capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
        finally:
            shutil.rmtree(work, ignore_errors=True)
            shutil.rmtree(pdir, ignore_errors=True)

    def test_env_sanitized_and_rustc_pinned(self):
        work = self._tree(); pdir = tempfile.mkdtemp()
        pfx = _copy_prefix(pdir)
        try:
            script = ('_gate_test_resolve_prefix "$1" >/dev/null; '
                      'echo "F=[${RUSTFLAGS-unset}] T=[${CARGO_TARGET_DIR-unset}]'
                      ' W=[${RUSTC_WRAPPER-unset}] R=[$RUSTC] H=[$CARGO_HOME]"')
            r = subprocess.run(
                [SH, "-c", ". %s\n. %s\n%s" % (GATE_BOOTSTRAP, GATE_LIB, script),
                 "sh", pfx], cwd=work,
                env=dict(os.environ, RUSTFLAGS="-Cbad", CARGO_TARGET_DIR="/evil",
                         RUSTC_WRAPPER="/evil/w"),
                capture_output=True, text=True)
            self.assertIn("F=[unset]", r.stdout)
            self.assertIn("T=[unset]", r.stdout)
            self.assertIn("W=[unset]", r.stdout)
            self.assertIn(pfx, r.stdout)  # RUSTC pinned + fresh CARGO_HOME
        finally:
            shutil.rmtree(work, ignore_errors=True)
            shutil.rmtree(pdir, ignore_errors=True)

    def test_resolution_invokes_no_inherited_path_command(self):
        # B2: with recording fakes first on PATH, resolving a controlled prefix
        # must not invoke ANY of them (no tr/sed/awk/grep/head/tail/dirname/
        # python3/sh, and the prefix's own cargo/rustc — not the PATH ones).
        work = self._tree(); pdir = tempfile.mkdtemp()
        pfx = _copy_prefix(pdir)
        fakebin = os.path.join(pdir, "fakebin"); os.makedirs(fakebin)
        invdir = os.path.join(pdir, "inv"); os.makedirs(invdir)
        for c in ("tr", "sed", "awk", "grep", "head", "tail", "dirname",
                  "python3", "sh", "cargo", "rustc", "readlink", "printf"):
            with open(os.path.join(fakebin, c), "w") as h:
                h.write('#!/bin/sh\nprintf x >> "%s/%s"\nexit 0\n' % (invdir, c))
            os.chmod(os.path.join(fakebin, c), 0o755)
        try:
            env = dict(os.environ,
                       PATH=fakebin + os.pathsep + os.environ["PATH"])
            r = subprocess.run(
                [SH, "-c", ". %s\n. %s\n_gate_test_resolve_prefix \"$1\""
                 % (GATE_BOOTSTRAP, GATE_LIB), "sh", pfx],
                cwd=work, env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            invoked = sorted(os.listdir(invdir))
            self.assertEqual(invoked, [],
                             "resolution invoked inherited PATH commands: %s"
                             % invoked)
        finally:
            shutil.rmtree(work, ignore_errors=True)
            shutil.rmtree(pdir, ignore_errors=True)


class BootstrapTrust(unittest.TestCase):
    """B1/B2: production bootstrap trusts only the literal prefix."""

    def test_prefix_mismatch_is_rejected(self):
        pdir = tempfile.mkdtemp()
        pfx = _copy_prefix(pdir)  # any dir != the literal
        try:
            r = subprocess.run(
                [SH, "-c", ". %s\ngate_bootstrap" % GATE_BOOTSTRAP],
                env=dict(os.environ, PREFIX=pfx), capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stderr)
        finally:
            shutil.rmtree(pdir, ignore_errors=True)

    def test_absent_prefix_is_inconclusive_controlled(self):
        # Host-INDEPENDENT: the absent-prefix -> INCONCLUSIVE/3 branch is
        # exercised via the test helper with an explicit, definitely-nonexistent
        # prefix. It does NOT infer absence from whether the developer machine
        # happens to contain the literal Termux path.
        missing = os.path.join(tempfile.gettempdir(),
                               "no_such_prefix_%d_%d" % (os.getpid(), id(self)))
        self.assertFalse(os.path.exists(missing))
        r = subprocess.run(
            [SH, "-c", ". %s\n. %s\n_gate_test_resolve_prefix \"$1\"; echo RC=$?"
             % (GATE_BOOTSTRAP, GATE_LIB), "sh", missing],
            capture_output=True, text=True)
        self.assertIn("RC=3", r.stdout, r.stdout + r.stderr)

    def test_missing_preload_classified_before_external_exec(self):
        # v26: a missing preload must be classified by shell BUILT-INS before any
        # external command. On real Termux the readlink used downstream cannot
        # execute without libtermux-exec.so, so classification must precede it.
        # Host-INDEPENDENT: gate_bootstrap "" yields the same authoritative state
        # everywhere, and the absence of "Permission denied" proves no external
        # readlink was attempted first.
        env = dict(os.environ)
        env.pop("PREFIX", None)
        env.pop("LD_PRELOAD", None)
        r = subprocess.run(
            [SH, "-c",
             '. %s\ngate_bootstrap ""\nrc=$?\n'
             'printf "RC=%%s\\n" "$rc"\n'
             'printf "GATE_PRELOAD_FAIL=%%s\\n" "${GATE_PRELOAD_FAIL-}"'
             % GATE_BOOTSTRAP],
            env=env, capture_output=True, text=True)
        self.assertIn("RC=1", r.stdout, r.stdout + r.stderr)
        self.assertIn("GATE_PRELOAD_FAIL=missing", r.stdout, r.stdout + r.stderr)
        self.assertIn("no inherited Termux exec preload", r.stderr, r.stderr)
        self.assertNotIn("Permission denied", r.stderr,
                         "an external command ran before missing-preload "
                         "classification: %s" % r.stderr)

    def test_single_cargo_home_created_and_cleaned(self):
        # B5: resolving once creates exactly one CARGO_HOME; gate_cleanup removes it.
        pdir = tempfile.mkdtemp()
        pfx = _copy_prefix(pdir)
        try:
            script = ('_gate_test_resolve_prefix "$1" >/dev/null; '
                      'echo "HOME=$CARGO_HOME"; '
                      '[ -d "$CARGO_HOME" ] && echo EXISTS; '
                      'gate_cleanup; '
                      '[ -d "$CARGO_HOME" ] && echo STILL || echo GONE')
            r = subprocess.run(
                [SH, "-c", ". %s\n. %s\n%s" % (GATE_BOOTSTRAP, GATE_LIB, script),
                 "sh", pfx], env=dict(os.environ),
                capture_output=True, text=True)
            self.assertIn("EXISTS", r.stdout)
            self.assertIn("GONE", r.stdout)
            self.assertNotIn("STILL", r.stdout)
        finally:
            shutil.rmtree(pdir, ignore_errors=True)


_MULTICALL_C = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>
#include <stdint.h>
#include <libgen.h>
typedef struct { uint32_t s[8]; uint64_t n; unsigned char b[64]; size_t bl; } sha;
static uint32_t ror(uint32_t x,int n){return (x>>n)|(x<<(32-n));}
static const uint32_t K[64]={
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static void sblk(sha*c,const unsigned char*p){uint32_t w[64],a,b,cc,d,e,f,g,h,t1,t2;int i;
 for(i=0;i<16;i++)w[i]=(p[i*4]<<24)|(p[i*4+1]<<16)|(p[i*4+2]<<8)|p[i*4+3];
 for(i=16;i<64;i++){uint32_t s0=ror(w[i-15],7)^ror(w[i-15],18)^(w[i-15]>>3);
  uint32_t s1=ror(w[i-2],17)^ror(w[i-2],19)^(w[i-2]>>10);w[i]=w[i-16]+s0+w[i-7]+s1;}
 a=c->s[0];b=c->s[1];cc=c->s[2];d=c->s[3];e=c->s[4];f=c->s[5];g=c->s[6];h=c->s[7];
 for(i=0;i<64;i++){uint32_t S1=ror(e,6)^ror(e,11)^ror(e,25);uint32_t ch=(e&f)^((~e)&g);
  t1=h+S1+ch+K[i]+w[i];uint32_t S0=ror(a,2)^ror(a,13)^ror(a,22);uint32_t mj=(a&b)^(a&cc)^(b&cc);
  t2=S0+mj;h=g;g=f;f=e;e=d+t1;d=cc;cc=b;b=a;a=t1+t2;}
 c->s[0]+=a;c->s[1]+=b;c->s[2]+=cc;c->s[3]+=d;c->s[4]+=e;c->s[5]+=f;c->s[6]+=g;c->s[7]+=h;}
static void sinit(sha*c){c->s[0]=0x6a09e667;c->s[1]=0xbb67ae85;c->s[2]=0x3c6ef372;c->s[3]=0xa54ff53a;
 c->s[4]=0x510e527f;c->s[5]=0x9b05688c;c->s[6]=0x1f83d9ab;c->s[7]=0x5be0cd19;c->n=0;c->bl=0;}
static void supd(sha*c,const unsigned char*p,size_t l){c->n+=l;while(l){c->b[c->bl++]=*p++;l--;
 if(c->bl==64){sblk(c,c->b);c->bl=0;}}}
static void sfin(sha*c,unsigned char*o){uint64_t bits=c->n*8;unsigned char pad=0x80;supd(c,&pad,1);
 unsigned char z=0;while(c->bl!=56)supd(c,&z,1);unsigned char L[8];int i;
 for(i=0;i<8;i++)L[i]=(bits>>(56-i*8))&0xff;supd(c,L,8);
 for(i=0;i<8;i++){o[i*4]=(c->s[i]>>24)&0xff;o[i*4+1]=(c->s[i]>>16)&0xff;o[i*4+2]=(c->s[i]>>8)&0xff;o[i*4+3]=c->s[i]&0xff;}}
static int do_sha(int ac,char**av){if(ac<2)return 1;FILE*f=fopen(av[1],"rb");if(!f)return 1;
 sha c;sinit(&c);unsigned char buf[4096];size_t r;while((r=fread(buf,1,sizeof buf,f))>0)supd(&c,buf,r);
 fclose(f);unsigned char o[32];sfin(&c,o);int i;for(i=0;i<32;i++)printf("%02x",o[i]);printf("  %s\n",av[1]);return 0;}
static int do_readlink(int ac,char**av){int i=1;if(i<ac&&strcmp(av[i],"-f")==0)i++;if(i>=ac)return 1;
 char rp[PATH_MAX];if(!realpath(av[i],rp))return 1;printf("%s\n",rp);return 0;}
static int do_mktemp(int ac,char**av){int dir=0,i;for(i=1;i<ac;i++)if(strcmp(av[i],"-d")==0)dir=1;
 char tmpl[PATH_MAX];const char*td=getenv("TMPDIR");if(!td)td="/tmp";
 snprintf(tmpl,sizeof tmpl,"%s/tmp.XXXXXX",td);
 if(dir){char*p=mkdtemp(tmpl);if(!p)return 1;printf("%s\n",p);}
 else{int fd=mkstemp(tmpl);if(fd<0)return 1;close(fd);printf("%s\n",tmpl);}return 0;}
static int do_timeout(int ac,char**av){int i=1;if(i<ac&&strcmp(av[i],"-k")==0)i+=2;if(i<ac)i++;
 if(i>=ac)return 1;execvp(av[i],&av[i]);return 127;}
int main(int ac,char**av){char*b=basename(av[0]);
 if(ac>=2&&(!strcmp(av[1],"--help")||!strcmp(av[1],"--version"))){printf("%s (multicall)\n",b);return 0;}
 if(!strcmp(b,"readlink"))return do_readlink(ac,av);
 if(!strcmp(b,"mktemp"))return do_mktemp(ac,av);
 if(!strcmp(b,"sha256sum"))return do_sha(ac,av);
 if(!strcmp(b,"timeout"))return do_timeout(ac,av);
 if(!strcmp(b,"coreutils")){fprintf(stderr,"coreutils: applet identity required\n");return 1;}
 return 1;}
'''

_MC_APPLETS = ("readlink", "sha256sum", "mktemp", "timeout")


def _host_multicall():
    """A real native multicall on the host (Termux coreutils, or busybox),
    identified by all four applets sharing one canonical target. None if the
    host ships separate binaries (e.g. stock Debian)."""
    reals = []
    for a in _MC_APPLETS:
        w = shutil.which(a)
        if not w:
            return None
        reals.append(os.path.realpath(w))
    if len(set(reals)) == 1:
        return reals[0]
    bb = shutil.which("busybox")
    return os.path.realpath(bb) if bb else None


def _build_native_multicall(dest):
    """Place a NATIVE multicall executable at dest. Prefer a real host multicall
    (copied); else compile the self-contained C multicall with cc. Returns True
    on success, False if neither is possible (caller should skip)."""
    host = _host_multicall()
    if host:
        shutil.copy(host, dest)
        os.chmod(dest, 0o755)
        return True
    cc = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")
    if not cc:
        return False
    src = dest + ".c"
    with open(src, "w") as h:
        h.write(_MULTICALL_C)
    r = subprocess.run([cc, "-O2", "-o", dest, src],
                       capture_output=True, text=True)
    try:
        os.remove(src)
    except OSError:
        pass
    return r.returncode == 0 and os.path.exists(dest)


def _multicall_prefix(tmp, cargo_ver="1.96.0", rustc_ver="1.96.0",
                      break_applet=None, escape_applet=None):
    """A Termux-style trusted prefix: readlink/sha256sum/mktemp/timeout are
    relative symlink entrypoints into ONE NATIVE multicall binary that
    dispatches on argv[0] (no shell dispatcher, no exec of host applets).
    sh/python3 are direct copies; cargo/rustc are direct stubs. Returns
    (prefix, multicall_path), or None if no native multicall can be built."""
    pfx = os.path.join(tmp, "pfx")
    os.makedirs(os.path.join(pfx, "bin"))
    mc = os.path.join(pfx, "bin", "coreutils")
    if not _build_native_multicall(mc):
        return None
    for a in _MC_APPLETS:
        target = "coreutils"
        if a == break_applet:
            target = "does_not_exist"          # broken applet symlink
        elif a == escape_applet:
            outside = os.path.join(tmp, "outside_mc")
            shutil.copy(mc, outside)
            os.chmod(outside, 0o755)
            target = outside                    # canonical target escapes prefix
        os.symlink(target, os.path.join(pfx, "bin", a))
    for c in ("sh", "python3"):
        shutil.copy(os.path.realpath(shutil.which(c)),
                    os.path.join(pfx, "bin", c))
        os.chmod(os.path.join(pfx, "bin", c), 0o755)
    for c, ver in (("cargo", cargo_ver), ("rustc", rustc_ver)):
        p = os.path.join(pfx, "bin", c)
        with open(p, "w") as h:
            h.write('#!/bin/sh\nif [ "$1" = --version ]; then '
                    'echo "%s %s (x)"; fi\nexit 0\n' % (c, ver))
        os.chmod(p, 0o755)
    return pfx, mc


class MulticallApplet(unittest.TestCase):
    """v18: Termux coreutils is a multicall binary. The bootstrap must INVOKE
    each applet ENTRYPOINT (preserving argv[0] identity) while validating the
    shared canonical target — never invoke the canonical target directly."""

    def _boot(self, prefix, body):
        return subprocess.run(
            [SH, "-c", ". %s\n. %s\n_gate_test_resolve_prefix \"$1\" || "
             "{ echo RESOLVE_RC=$?; exit 7; }\n%s"
             % (GATE_BOOTSTRAP, GATE_LIB, body), "sh", prefix],
            env=dict(os.environ), capture_output=True, text=True)

    def _prefix(self, tmp, **kw):
        res = _multicall_prefix(tmp, **kw)
        if res is None:
            self.skipTest("no native multicall on this host; the Termux "
                          "coreutils multicall path is verified in production")
        return res

    def test_entrypoints_and_shared_canonical_target(self):
        tmp = tempfile.mkdtemp()
        try:
            pfx, mc = self._prefix(tmp)
            r = self._boot(
                pfx,
                'echo "MK=$TRUSTED_MKTEMP|$TRUSTED_MKTEMP_REAL"\n'
                'echo "RL=$TRUSTED_READLINK|$TRUSTED_READLINK_REAL"\n'
                'echo "SH256=$TRUSTED_SHA256SUM|$TRUSTED_SHA256SUM_REAL"\n'
                'echo "TO=$TRUSTED_TIMEOUT|$TRUSTED_TIMEOUT_REAL"')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            reals = []
            for line in r.stdout.splitlines():
                if "|" not in line:
                    continue
                ep, real = line.split("=", 1)[1].split("|")
                # entrypoint keeps the applet basename; canonical is coreutils
                self.assertTrue(ep.endswith(("/mktemp", "/readlink",
                                             "/sha256sum", "/timeout")))
                self.assertEqual(os.path.realpath(real), os.path.realpath(mc))
                self.assertNotEqual(ep, real)   # not silently exchanged
                reals.append(os.path.realpath(real))
            self.assertEqual(len(set(reals)), 1)  # all share one multicall file
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @staticmethod
    def _extract_help(out):
        """Return (help_text, rc) from a BEGIN/END-delimited timeout --help
        capture. Parses the COMPLETE multiline block (BusyBox puts the
        multi-call banner on line 1 and 'Usage: timeout' on a later line)."""
        lines = out.splitlines()
        b = lines.index("TIMEOUT_HELP_BEGIN")
        e = lines.index("TIMEOUT_HELP_END")
        body = lines[b + 1:e]
        rc = None
        help_lines = []
        for ln in body:
            if ln.startswith("TIMEOUT_HELP_RC="):
                rc = int(ln.split("=", 1)[1])
            else:
                help_lines.append(ln)
        return "\n".join(help_lines), rc

    @staticmethod
    def _timeout_identity_ok(block):
        # a timeout-specific reference anywhere in the COMPLETE help block
        b = block.lower()
        return ("usage: timeout" in b) or ("timeout" in b)

    def test_applet_identities_self_contained(self):
        # TEST A (v22/v23): prove each applet DISPATCHES correctly using only
        # self-contained forms. mktemp/readlink/sha256sum are self-contained;
        # timeout identity is proven via its own --help output (parsed in FULL,
        # multiline), NOT by requiring the copied timeout to nested-exec another
        # copied binary. The real trusted timeout launching a real trusted child
        # is TEST B, under the validated preload.
        tmp = tempfile.mkdtemp()
        try:
            pfx, mc = self._prefix(tmp)
            probe = os.path.join(tmp, "probe.txt")
            with open(probe, "w") as h:
                h.write("data")
            r = self._boot(
                pfx,
                'D=$("$TRUSTED_MKTEMP" -d) && [ -d "$D" ] && echo MKTEMP_D_OK && rm -rf "$D"\n'
                'echo "RL=$("$TRUSTED_READLINK" -f "%s")"\n'
                '"$TRUSTED_SHA256SUM" "%s" >/dev/null && echo SHA_OK\n'
                'echo TIMEOUT_HELP_BEGIN\n'
                '"$TRUSTED_TIMEOUT" --help 2>&1\n'
                'echo "TIMEOUT_HELP_RC=$?"\n'
                'echo TIMEOUT_HELP_END'
                % (probe, probe))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("MKTEMP_D_OK", r.stdout)          # mktemp dispatched
            self.assertIn("RL=" + os.path.realpath(probe), r.stdout)  # readlink
            self.assertIn("SHA_OK", r.stdout)               # sha256sum dispatched
            help_text, rc = self._extract_help(r.stdout)
            self.assertEqual(rc, 0, "timeout --help rc=%r\n%s" % (rc, help_text))
            self.assertTrue(help_text.strip(), "timeout --help produced no output")
            self.assertTrue(
                self._timeout_identity_ok(help_text),
                "timeout entrypoint did not identify as timeout in its full "
                "help block:\n%s" % help_text)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _run_timeout_help(self, timeout_path):
        script = ('echo TIMEOUT_HELP_BEGIN\n'
                  '"%s" --help 2>&1\n'
                  'echo "TIMEOUT_HELP_RC=$?"\n'
                  'echo TIMEOUT_HELP_END\n' % timeout_path)
        out = subprocess.run([SH, "-c", script],
                             capture_output=True, text=True).stdout
        return self._extract_help(out)

    def test_timeout_identity_busybox_multiline_help(self):
        # v23 regression: BusyBox help begins with the multi-call banner and
        # names timeout only on a LATER line. The parser must inspect the whole
        # block, not just line 1.
        tmp = tempfile.mkdtemp()
        try:
            to = os.path.join(tmp, "timeout")
            with open(to, "w") as h:
                h.write("#!/bin/sh\n"
                        'if [ "$1" = --help ]; then\n'
                        "printf 'BusyBox v1.37.0 (2024-01-01) multi-call binary.\\n\\n"
                        "Usage: timeout [-s SIG] [-k KILL_SECS] SECS PROG ARGS\\n'\n"
                        "exit 0\nfi\nexit 1\n")
            os.chmod(to, 0o755)
            help_text, rc = self._run_timeout_help(to)
            self.assertEqual(rc, 0)
            # first line must NOT be relied upon (it names BusyBox, not timeout)
            self.assertNotIn("timeout", help_text.splitlines()[0].lower())
            self.assertTrue(self._timeout_identity_ok(help_text), help_text)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_timeout_identity_coreutils_firstline_help(self):
        # v23 regression: GNU coreutils help names timeout on the FIRST line.
        tmp = tempfile.mkdtemp()
        try:
            to = os.path.join(tmp, "timeout")
            with open(to, "w") as h:
                h.write("#!/bin/sh\n"
                        'if [ "$1" = --help ]; then\n'
                        "printf 'Usage: timeout [OPTION] DURATION COMMAND [ARG]...\\n"
                        "Start COMMAND, and kill it if still running after DURATION.\\n'\n"
                        "exit 0\nfi\nexit 1\n")
            os.chmod(to, 0o755)
            help_text, rc = self._run_timeout_help(to)
            self.assertEqual(rc, 0)
            self.assertIn("timeout", help_text.splitlines()[0].lower())
            self.assertTrue(self._timeout_identity_ok(help_text), help_text)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_direct_canonical_target_is_rejected_by_applet(self):
        # invoking the multicall canonical target directly loses applet identity
        tmp = tempfile.mkdtemp()
        try:
            pfx, mc = self._prefix(tmp)
            r = self._boot(
                pfx,
                'if "$TRUSTED_MKTEMP_REAL" -d >/dev/null 2>&1; then '
                'echo DIRECT_OK; else echo DIRECT_FAILS; fi')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("DIRECT_FAILS", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_canonical_target_outside_prefix_fails(self):
        tmp = tempfile.mkdtemp()
        try:
            pfx, mc = self._prefix(tmp, escape_applet="mktemp")
            r = self._boot(pfx, "echo SHOULD_NOT_REACH")
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("SHOULD_NOT_REACH", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_broken_applet_symlink_fails(self):
        tmp = tempfile.mkdtemp()
        try:
            pfx, mc = self._prefix(tmp, break_applet="mktemp")
            r = self._boot(pfx, "echo SHOULD_NOT_REACH")
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("SHOULD_NOT_REACH", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_applet_entrypoint_fails(self):
        tmp = tempfile.mkdtemp()
        try:
            pfx, mc = self._prefix(tmp)
            os.remove(os.path.join(pfx, "bin", "timeout"))
            r = self._boot(pfx, "echo SHOULD_NOT_REACH")
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("SHOULD_NOT_REACH", r.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_resolution_uses_no_inherited_path_command(self):
        tmp = tempfile.mkdtemp()
        try:
            pfx, mc = self._prefix(tmp)
            fakebin = os.path.join(tmp, "fakebin"); os.makedirs(fakebin)
            invdir = os.path.join(tmp, "inv"); os.makedirs(invdir)
            for c in ("readlink", "mktemp", "sha256sum", "timeout", "tr",
                      "sed", "awk", "grep", "dirname", "coreutils"):
                with open(os.path.join(fakebin, c), "w") as h:
                    h.write('#!/bin/sh\nprintf x >> "%s/%s"\nexit 0\n'
                            % (invdir, c))
                os.chmod(os.path.join(fakebin, c), 0o755)
            env = dict(os.environ,
                       PATH=fakebin + os.pathsep + os.environ["PATH"])
            r = subprocess.run(
                [SH, "-c", ". %s\n. %s\n_gate_test_resolve_prefix \"$1\""
                 % (GATE_BOOTSTRAP, GATE_LIB), "sh", pfx],
                env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(sorted(os.listdir(invdir)), [],
                             "resolution used inherited PATH commands: %s"
                             % os.listdir(invdir))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class PreloadValidation(unittest.TestCase):
    """v19: the bootstrap preserves the legitimate Termux libtermux-exec.so
    preload (needed for nested exec) while rejecting anything else."""

    def _prefix(self):
        t = tempfile.mkdtemp()
        pfx = os.path.join(t, "pfx")
        os.makedirs(os.path.join(pfx, "lib"))
        os.makedirs(os.path.join(pfx, "bin"))
        shutil.copy(os.path.realpath(shutil.which("readlink")),
                    os.path.join(pfx, "bin", "readlink"))
        os.chmod(os.path.join(pfx, "bin", "readlink"), 0o755)
        return t, pfx

    def _validate(self, pfx, value, require=0):
        script = ('. "%s"\ngate_validate_preload "%s" "%s/bin/readlink" "%s" "%s"; '
                  'echo "RC=$? PRELOAD=[${GATE_PRELOAD-unset}] '
                  'FAIL=[${GATE_PRELOAD_FAIL-unset}]"'
                  % (GATE_BOOTSTRAP, pfx, pfx, value, require))
        r = subprocess.run([SH, "-c", script], capture_output=True, text=True)
        return r.stdout.strip()

    def _mklib(self, pfx):
        p = os.path.join(pfx, "lib", "libtermux-exec.so")
        with open(p, "wb") as h:
            h.write(b"\x7fELF-stub")
        return p

    def test_empty_preload_is_rejected_for_termux_production(self):
        t, pfx = self._prefix()
        try:
            out = self._validate(pfx, "", require=1)
            self.assertIn("RC=1", out)
            self.assertIn("FAIL=[missing]", out)
            self.assertIn("TERMUX_EXEC_PRELOAD_CHECK: FAIL", out)
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_preload_marker_stream_contract(self):
        # Explicit, documented contract for the missing-preload signals, tested
        # DIRECTLY through gate_validate_preload (not indirectly via
        # gate_bootstrap): the TERMUX_EXEC_PRELOAD_CHECK: FAIL marker is a
        # user-facing STDOUT line; the human-readable reason is on STDERR; and
        # GATE_PRELOAD_FAIL=missing is the authoritative variable callers key on.
        t, pfx = self._prefix()
        try:
            script = ('. "%s"\n'
                      'gate_validate_preload "%s" "%s/bin/readlink" "" 1\n'
                      'rc=$?\n'
                      'printf "RC=%%s\\n" "$rc"\n'
                      'printf "FAIL=%%s\\n" "${GATE_PRELOAD_FAIL-}"'
                      % (GATE_BOOTSTRAP, pfx, pfx))
            r = subprocess.run([SH, "-c", script], capture_output=True,
                               text=True)
            self.assertIn("TERMUX_EXEC_PRELOAD_CHECK: FAIL", r.stdout,
                          "marker not on stdout")
            self.assertIn("RC=1", r.stdout)
            self.assertIn("FAIL=missing", r.stdout)
            self.assertIn("no inherited Termux exec preload", r.stderr,
                          "reason not on stderr")
            self.assertNotIn("TERMUX_EXEC_PRELOAD_CHECK", r.stderr)
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_empty_accepted_in_desktop_no_preload_mode(self):
        # generic desktop fixtures may run without a preload (require=0)
        t, pfx = self._prefix()
        try:
            self.assertIn("RC=0 PRELOAD=[]", self._validate(pfx, "", require=0))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_genuine_preload_is_preserved(self):
        t, pfx = self._prefix()
        try:
            lib = self._mklib(pfx)
            out = self._validate(pfx, lib)
            self.assertIn("RC=0", out)
            self.assertIn("PRELOAD=[%s]" % lib, out)
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_outside_prefix_is_rejected(self):
        t, pfx = self._prefix()
        try:
            self._mklib(pfx)
            self.assertIn("RC=1", self._validate(pfx, "/tmp/evil.so"))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_caller_fake_at_noncanonical_path_is_rejected(self):
        t, pfx = self._prefix()
        try:
            self._mklib(pfx)
            fake = os.path.join(t, "libtermux-exec.so")
            with open(fake, "wb") as h:
                h.write(b"fake")
            self.assertIn("RC=1", self._validate(pfx, fake))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_multiple_entries_rejected(self):
        t, pfx = self._prefix()
        try:
            lib = self._mklib(pfx)
            self.assertIn("RC=1", self._validate(pfx, lib + ":/other.so"))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_injected_before_rejected(self):
        t, pfx = self._prefix()
        try:
            lib = self._mklib(pfx)
            self.assertIn("RC=1", self._validate(pfx, "/other.so:" + lib))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_relative_path_rejected(self):
        t, pfx = self._prefix()
        try:
            self._mklib(pfx)
            self.assertIn("RC=1", self._validate(pfx, "libtermux-exec.so"))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_missing_library_rejected(self):
        t, pfx = self._prefix()
        try:
            expected = os.path.join(pfx, "lib", "libtermux-exec.so")
            self.assertIn("RC=1", self._validate(pfx, expected))  # not created
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_symlink_escaping_prefix_rejected(self):
        t, pfx = self._prefix()
        try:
            outside = os.path.join(t, "outside.so")
            with open(outside, "wb") as h:
                h.write(b"x")
            link = os.path.join(pfx, "lib", "libtermux-exec.so")
            os.symlink(outside, link)
            self.assertIn("RC=1", self._validate(pfx, link))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_directory_at_canonical_path_rejected(self):
        t, pfx = self._prefix()
        try:
            os.makedirs(os.path.join(pfx, "lib", "libtermux-exec.so"))
            expected = os.path.join(pfx, "lib", "libtermux-exec.so")
            self.assertIn("RC=1", self._validate(pfx, expected))
        finally:
            shutil.rmtree(t, ignore_errors=True)


class NestedExecProbe(unittest.TestCase):
    """v19: the post-bootstrap probe proves the sanitised trusted environment
    can nest processes, and fails closed on any error/stderr/nonzero."""

    def _probe(self, trusted_py, trusted_sh):
        script = ('. "%s"\nTRUSTED_PYTHON3="%s"; TRUSTED_SH="%s"; '
                  'TRUSTED_MKTEMP="%s"; TRUSTED_TIMEOUT="%s"; '
                  'TRUSTED_READLINK="%s"\n'
                  'if gate_nested_exec_probe; then echo PROBE=PASS; '
                  'else echo PROBE=FAIL; fi'
                  % (GATE_BOOTSTRAP, trusted_py, trusted_sh,
                     shutil.which("mktemp"), shutil.which("timeout"),
                     shutil.which("readlink")))
        return subprocess.run([SH, "-c", script],
                              capture_output=True, text=True).stdout

    def test_working_env_passes(self):
        out = self._probe(shutil.which("python3"), shutil.which("sh"))
        self.assertIn("PROBE=PASS", out)

    def test_failing_python_fails(self):
        t = tempfile.mkdtemp()
        try:
            bad = os.path.join(t, "badpy")
            with open(bad, "w") as h:
                h.write('#!/bin/sh\necho boom >&2\nexit 1\n')
            os.chmod(bad, 0o755)
            self.assertIn("PROBE=FAIL", self._probe(bad, shutil.which("sh")))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_stderr_noise_fails(self):
        t = tempfile.mkdtemp()
        try:
            noisy = os.path.join(t, "noisypy")
            with open(noisy, "w") as h:
                h.write('#!/bin/sh\necho "Traceback (most recent call last):" '
                        '>&2\nexit 0\n')
            os.chmod(noisy, 0o755)
            self.assertIn("PROBE=FAIL", self._probe(noisy, shutil.which("sh")))
        finally:
            shutil.rmtree(t, ignore_errors=True)


class MeasurementStderr(unittest.TestCase):
    """B2: gate_measurement_stderr_clean fails on any stderr bytes."""

    def _clean(self, content):
        t = tempfile.mkdtemp()
        try:
            errf = os.path.join(t, "err")
            with open(errf, "w") as h:
                h.write(content)
            return _lib_call(["gate_measurement_stderr_clean", errf]).returncode
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_empty_stderr_ok(self):
        self.assertEqual(self._clean(""), 0)

    def test_resourcewarning_fails(self):
        self.assertNotEqual(self._clean("ResourceWarning: unclosed file\n"), 0)

    def test_traceback_fails(self):
        self.assertNotEqual(self._clean(
            "Traceback (most recent call last):\n RuntimeError: boom\n"), 0)

    def test_arbitrary_stderr_fails(self):
        self.assertNotEqual(self._clean("one noisy line\n"), 0)

    def test_missing_capture_file_fails(self):
        self.assertNotEqual(
            _lib_call(["gate_measurement_stderr_clean",
                       "/no/such/errf"]).returncode, 0)


def _build_controlled_baseline(tmp, changed=("rust/witness-verify/src/main.rs",),
                               base_extra=None, cand_extra=None,
                               cand_remove=None):
    files = {
        "rust/Cargo.toml": b"[workspace]\n",
        "rust/witness-verify/Cargo.toml": b"name=wv\n",
        "rust/witness-verify/src/main.rs": b"fn main(){}\n",
        "rust/witness-verify/src/sha256.rs": b"// sha\n",
    }
    pinned = sorted(files)
    zpath = os.path.join(tmp, "base.zip")
    with zipfile.ZipFile(zpath, "w") as z:
        for rel, data in files.items():
            z.writestr("proj-main/%s" % rel, data)
        for rel, data in (base_extra or {}).items():
            z.writestr("proj-main/%s" % rel, data)
    cand = os.path.join(tmp, "cand")
    for rel, data in files.items():
        p = os.path.join(cand, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as h:
            h.write(data + (b"// delta\n" if rel in changed else b""))
    for rel, data in (cand_extra or {}).items():
        p = os.path.join(cand, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as h:
            h.write(data)
    if cand_remove:
        os.remove(os.path.join(cand, cand_remove))
    zsha = PROV.sha256_file(zpath)
    base = {rel: hashlib.sha256(data).hexdigest()
            for rel, data in files.items()}
    candh = {rel: hashlib.sha256(
        data + (b"// delta\n" if rel in changed else b"")).hexdigest()
        for rel, data in files.items()}
    pin = {"pinned_paths": pinned, "pinned_path_count": len(pinned),
           "rust_source_sha256": "x",
           "provenance": {"adopted_baseline": {"artifact": PROV.REQUIRED_ARTIFACT,
                                               "sha256": zsha},
                          "baseline_file_sha256": base,
                          "candidate_file_sha256": candh,
                          "files_changed_from_baseline": sorted(changed),
                          "reviewed_delta": "t"}}
    return zpath, cand, pin, zsha


class ProvenanceDerivation(unittest.TestCase):
    """B6/B3/B4: pin derived from real bytes, scope enumerated, metadata
    consistent. Driven with controlled baselines."""

    def test_happy(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(t)
            self.assertEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_wrong_zip_sha(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(t)
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha="0" * 64), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_missing_baseline_file(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(t)
            self.assertNotEqual(
                PROV.verify(os.path.join(t, "nope.zip"), c, p,
                            required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_ambiguous_root(self):
        t = tempfile.mkdtemp()
        try:
            zpath = os.path.join(t, "amb.zip")
            with zipfile.ZipFile(zpath, "w") as z:
                z.writestr("proj-main/rust/Cargo.toml", b"x\n")
                z.writestr("stray.txt", b"x\n")
            zsha = PROV.sha256_file(zpath)
            _, c, p, _ = _build_controlled_baseline(t)
            p["provenance"]["adopted_baseline"]["sha256"] = zsha
            self.assertNotEqual(PROV.verify(zpath, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_falsified_baseline_hashes(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(t)
            for k in p["provenance"]["baseline_file_sha256"]:
                p["provenance"]["baseline_file_sha256"][k] = "0" * 64
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_undeclared_source_change(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(t, changed=())
            with open(os.path.join(c, "rust", "witness-verify", "src",
                                   "sha256.rs"), "ab") as h:
                h.write(b"// sneaky\n")
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_declared_change_not_occurred(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(t, changed=())
            p["provenance"]["files_changed_from_baseline"] = \
                ["rust/witness-verify/src/main.rs"]
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    # B3 scope enumeration
    def test_unpinned_baseline_rs(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(
                t, base_extra={"rust/witness-verify/src/UNPINNED.rs": b"fn x(){}\n"})
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_unpinned_baseline_cargo(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(
                t, base_extra={"rust/extra/Cargo.toml": b"x\n"})
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_extra_candidate_rs(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(
                t, cand_extra={"rust/witness-verify/src/EXTRA.rs": b"fn x(){}\n"})
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_removed_candidate_rs(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(
                t, cand_remove="rust/witness-verify/src/sha256.rs")
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    # B4 metadata
    def test_false_recorded_sha(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(t)
            p["provenance"]["adopted_baseline"]["sha256"] = "0" * 64
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_false_artifact_name(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(t)
            p["provenance"]["adopted_baseline"]["artifact"] = "wrong.zip"
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_false_pinned_count(self):
        t = tempfile.mkdtemp()
        try:
            z, c, p, zsha = _build_controlled_baseline(t)
            p["pinned_path_count"] = 99
            self.assertNotEqual(PROV.verify(z, c, p, required_zip_sha=zsha), [])
        finally:
            shutil.rmtree(t, ignore_errors=True)


class NoCargoEnvironment(unittest.TestCase):
    """The workspace checker reports the toolchain unavailable under a
    deterministic no-Cargo PATH built by the SHARED fixture — no inherited PATH
    directory is enumerated (Android /system/bin & /product/bin are not
    listable)."""

    def test_workspace_checker_unavailable_without_cargo(self):
        tmp, bindir, missing = _fixtures.build_isolated_bin_without_cargo()
        try:
            self.assertEqual(missing, [],
                             "missing required commands: %s" % missing)
            env = {"PATH": bindir, "PYTHONDONTWRITEBYTECODE": "1",
                   "PYTHONWARNINGS": "error::ResourceWarning"}
            if os.environ.get("LD_PRELOAD"):
                env["LD_PRELOAD"] = os.environ["LD_PRELOAD"]
            probe = subprocess.run([SH, "-c", "command -v cargo"], env=env,
                                   capture_output=True, text=True)
            self.assertNotEqual(probe.returncode, 0,
                                "cargo still resolvable: %r" % probe.stdout)
            proc = subprocess.run([SH, "tools/check_rust_workspace.sh"],
                                  cwd=ROOT, env=env, capture_output=True,
                                  text=True)
            self.assertEqual(proc.returncode, 3,
                             proc.stdout[-600:] + proc.stderr[-600:])
            self.assertIn(
                "RUST_WORKSPACE_CHECK: INCONCLUSIVE_TOOLCHAIN_UNAVAILABLE",
                proc.stdout)
            self.assertEqual(proc.stderr.strip(), "",
                             "checker emitted warnings/stderr: %r" % proc.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_shared_fixture_used_no_duplicated_path_enumeration(self):
        # ANTI-DRIFT: the no-Cargo builder lives in ONE shared module and the
        # individual test files must not carry their own PATH-enumerating copy
        # (a duplicate retaining os.listdir over PATH is what broke v23 on
        # Android's non-listable /product/bin). Needles are assembled from
        # fragments so this test's own source does not match them.
        import inspect
        listdir = "os.list" + "dir"
        path_iter = 'for d in os.environ.get("PA' + 'TH"'
        listdir_d = listdir + "(d)"
        self.assertNotIn(listdir, inspect.getsource(_fixtures),
                         "shared fixture enumerates directories")
        for fname in ("self_tests.py", "gate_unit_tests.py",
                      "gate_integration_tests.py"):
            with open(os.path.join(HERE, fname)) as h:
                src = h.read()
            self.assertNotIn(path_iter, src,
                             "%s enumerates inherited PATH" % fname)
            self.assertNotIn("sorted(" + listdir_d + ")", src,
                             "%s lists a PATH directory" % fname)
            self.assertNotIn(listdir_d, src,
                             "%s lists a PATH directory" % fname)


if __name__ == "__main__":
    unittest.main(verbosity=2)
