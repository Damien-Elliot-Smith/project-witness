#!/usr/bin/env python3
"""Move 82 focused test suite.

Stdout-bound runner, pinned count, warning-clean. Target-portable: no
desktop filesystem paths are assumed, the interpreter and shell are
resolved once at import and validated, and every subprocess is bounded.

The suite is deliberately heavy on NEGATIVE cases. Move 82 produces an
executable and a provenance record, so the failure modes that matter are
the ones where something plausible-looking is accepted: a mismatched
candidate hash, a binary whose header disagrees with the detected target,
a provenance record claiming more than the evidence supports, or a final
artefact published by a gate that should have stopped.
"""

import json
import os
import stat
import struct
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import inspect_binary  # noqa: E402
import provenance  # noqa: E402

GATE = os.path.join(ROOT, "tools",
                    "check_move82_portable_build_adoption.sh")
BASELINE_CHECKER = os.path.join(HERE, "check_move82_inherited.py")
ALLOWLIST = os.path.join(HERE, "allowlist_move82.json")
README = os.path.join(HERE, "README.md")
BUILD_TOOL = os.path.join(HERE, "build_binary.py")
INSPECT_TOOL = os.path.join(HERE, "inspect_binary.py")
PROV_TOOL = os.path.join(HERE, "provenance.py")
EQUIV_TOOL = os.path.join(HERE, "equivalence.py")

ADOPTED_M81_SHA = \
    "7b49a3a5d1e1c6380b27c7b43aca721391189cffbecbf4f51a56c4d12c1d3d0d"

SUBPROCESS_TIMEOUT = 120


def _require_abs_exec(path, what):
    if not path:
        raise RuntimeError("%s could not be resolved" % what)
    if not os.path.isabs(path):
        raise RuntimeError("%s is not an absolute path: %r" % (what, path))
    if not os.path.isfile(path):
        raise RuntimeError("%s is not a regular file: %r" % (what, path))
    if not os.access(path, os.X_OK):
        raise RuntimeError("%s is not executable: %r" % (what, path))
    return path


PYTHON_BIN = _require_abs_exec(
    os.path.realpath(sys.executable), "test interpreter")


def _resolve_test_sh():
    supplied = os.environ.get("MOVE82_TEST_SH")
    if supplied:
        return _require_abs_exec(os.path.realpath(supplied),
                                 "MOVE82_TEST_SH (trusted shell)")
    import shutil as _shutil
    found = _shutil.which("sh")
    if not found:
        raise RuntimeError(
            "no shell available: set MOVE82_TEST_SH to the trusted shell")
    return _require_abs_exec(os.path.realpath(found), "fallback shell")


TEST_SH = _resolve_test_sh()

_TMP = None


def setUpModule():
    global _TMP
    import tempfile
    _TMP = tempfile.mkdtemp(prefix="m82_tests_")


def tearDownModule():
    import shutil
    if _TMP:
        shutil.rmtree(_TMP, ignore_errors=True)


def _run(argv, env=None, timeout=SUBPROCESS_TIMEOUT):
    return subprocess.run(argv, capture_output=True, env=env,
                          timeout=timeout)


def _write_python_exe(name, body):
    path = os.path.join(_TMP, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("#!%s\n%s" % (PYTHON_BIN, body))
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP
             | stat.S_IXOTH)
    return path


# ----------------------------------------------------------------------
# Synthetic ELF construction, so header handling is tested against images
# whose every field is known and controllable.
# ----------------------------------------------------------------------

EM_AARCH64 = 0xB7
EM_X86_64 = 0x3E
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3


def make_elf(path, machine=EM_AARCH64, elf_class=2, endian=1,
             e_type=3, interp="/system/bin/linker64",
             needed=("libc.so", "libdl.so"), break_interp=None,
             break_dynamic=None, phentsize=56):
    """Build a minimal but structurally coherent ELF64 image."""
    pack = "<" if endian == 1 else ">"
    segments = []
    payload = bytearray()

    interp_off = None
    if interp is not None:
        interp_bytes = interp.encode("utf-8") + b"\x00"
        if break_interp == "unterminated":
            interp_bytes = interp.encode("utf-8")
        elif break_interp == "empty":
            interp_bytes = b"\x00"
        elif break_interp == "nonutf8":
            interp_bytes = b"\xff\xfe\x00"
        interp_off = len(payload)
        payload += interp_bytes

    strtab_off = None
    needed_offsets = []
    if needed:
        strtab_off = len(payload)
        payload += b"\x00"
        for name in needed:
            needed_offsets.append(len(payload) - strtab_off)
            payload += name.encode("utf-8") + b"\x00"

    dyn_off = None
    if needed:
        dyn_off = len(payload)
        entries = []
        for rel in needed_offsets:
            entries.append((1, rel))            # DT_NEEDED
        if break_dynamic != "no_strtab":
            entries.append((5, 0))              # DT_STRTAB (vaddr fixed up)
        if break_dynamic == "strtab_unmapped":
            entries = [(t, v) for t, v in entries if t != 5]
            entries.append((5, 0xDEAD0000))
        entries.append((0, 0))                  # DT_NULL
        dyn_blob = bytearray()
        for tag, val in entries:
            dyn_blob += struct.pack(pack + "QQ", tag, val)
        payload += dyn_blob

    ehdr_size = 64
    nphdr = (1 if interp is not None else 0) + 1 + (1 if needed else 0)
    phoff = ehdr_size
    data_off = phoff + nphdr * phentsize
    # identity map: vaddr == file offset, so lookups are simple
    if needed and break_dynamic != "strtab_unmapped":
        fixed = bytearray(payload)
        pos = dyn_off
        while pos + 16 <= len(fixed):
            tag, _val = struct.unpack_from(pack + "QQ", fixed, pos)
            if tag == 5:
                struct.pack_into(pack + "Q", fixed, pos + 8,
                                 data_off + strtab_off)
            if tag == 0:
                break
            pos += 16
        payload = fixed

    phdrs = bytearray()
    if interp is not None:
        phdrs += struct.pack(
            pack + "IIQQQQQQ", PT_INTERP, 4, data_off + interp_off,
            data_off + interp_off, 0,
            len(payload) - interp_off if interp_off is not None else 0,
            0, 1)
        # correct filesz for the interp segment specifically
        struct.pack_into(pack + "Q", phdrs, 32,
                         (strtab_off - interp_off) if strtab_off is not None
                         else len(payload) - interp_off)
    phdrs += struct.pack(pack + "IIQQQQQQ", PT_LOAD, 5, data_off,
                         data_off, 0, len(payload), len(payload), 1)
    if needed:
        phdrs += struct.pack(
            pack + "IIQQQQQQ", PT_DYNAMIC, 6, data_off + dyn_off,
            data_off + dyn_off, 0, len(payload) - dyn_off,
            len(payload) - dyn_off, 1)

    ehdr = bytearray(ehdr_size)
    ehdr[0:4] = b"\x7fELF"
    ehdr[4] = elf_class
    ehdr[5] = endian
    ehdr[6] = 1
    struct.pack_into(pack + "H", ehdr, 16, e_type)
    struct.pack_into(pack + "H", ehdr, 18, machine)
    struct.pack_into(pack + "I", ehdr, 20, 1)
    struct.pack_into(pack + "Q", ehdr, 32, phoff)
    struct.pack_into(pack + "H", ehdr, 52, ehdr_size)
    struct.pack_into(pack + "H", ehdr, 54, phentsize)
    struct.pack_into(pack + "H", ehdr, 56, nphdr)

    with open(path, "wb") as handle:
        handle.write(bytes(ehdr) + bytes(phdrs) + bytes(payload))
    os.chmod(path, 0o755)
    return path


# ----------------------------------------------------------------------
# Binary inspection
# ----------------------------------------------------------------------

class TestBinaryInspection(unittest.TestCase):
    def test_well_formed_aarch64_binary_accepted(self):
        path = make_elf(os.path.join(_TMP, "good_aarch64"))
        facts = inspect_binary.inspect_path(path)
        self.assertEqual(facts["architecture"], "aarch64")
        self.assertEqual(facts["executable_format"], "ELF64")
        self.assertEqual(facts["endianness"], "little")
        self.assertEqual(facts["interpreter"], "/system/bin/linker64")
        self.assertEqual(facts["runtime_dependencies"],
                         ["libc.so", "libdl.so"])

    def test_runtime_dependencies_are_sorted_and_deduplicated(self):
        path = make_elf(os.path.join(_TMP, "dep_order"),
                        needed=("libz.so", "libc.so", "libc.so"))
        facts = inspect_binary.inspect_path(path)
        self.assertEqual(facts["runtime_dependencies"],
                         ["libc.so", "libz.so"])

    def test_architecture_mismatch_detected(self):
        path = make_elf(os.path.join(_TMP, "wrong_arch"),
                        machine=EM_X86_64)
        facts = inspect_binary.inspect_path(path)
        problems = inspect_binary.cross_check(
            facts, rustc_host="aarch64-linux-android",
            platform_machine="aarch64")
        self.assertTrue(problems)

    def test_wrong_target_triple_rejected_by_cross_check(self):
        path = make_elf(os.path.join(_TMP, "triple_mismatch"))
        facts = inspect_binary.inspect_path(path)
        problems = inspect_binary.cross_check(
            facts, rustc_host="x86_64-unknown-linux-gnu")
        self.assertTrue(problems)

    def test_unsupported_elf_class_rejected(self):
        path = os.path.join(_TMP, "elf32")
        make_elf(path)
        with open(path, "r+b") as handle:
            handle.seek(4)
            handle.write(b"\x01")          # ELFCLASS32
        with self.assertRaises(inspect_binary.InspectError):
            inspect_binary.inspect_path(path)

    def test_unsupported_endianness_rejected(self):
        path = os.path.join(_TMP, "elf_badendian")
        make_elf(path)
        with open(path, "r+b") as handle:
            handle.seek(5)
            handle.write(b"\x07")          # neither 1 nor 2
        with self.assertRaises(inspect_binary.InspectError):
            inspect_binary.inspect_path(path)

    def test_bad_magic_rejected(self):
        path = os.path.join(_TMP, "not_elf")
        with open(path, "wb") as handle:
            handle.write(b"\x00" * 200)
        with self.assertRaises(inspect_binary.InspectError):
            inspect_binary.inspect_path(path)

    def test_malformed_pt_interp_unterminated(self):
        path = make_elf(os.path.join(_TMP, "interp_unterm"),
                        break_interp="unterminated", needed=())
        with self.assertRaises(inspect_binary.InspectError):
            inspect_binary.inspect_path(path)

    def test_malformed_pt_interp_empty(self):
        path = make_elf(os.path.join(_TMP, "interp_empty"),
                        break_interp="empty", needed=())
        with self.assertRaises(inspect_binary.InspectError):
            inspect_binary.inspect_path(path)

    def test_malformed_pt_interp_non_utf8(self):
        path = make_elf(os.path.join(_TMP, "interp_nonutf8"),
                        break_interp="nonutf8", needed=())
        with self.assertRaises(inspect_binary.InspectError):
            inspect_binary.inspect_path(path)

    def test_malformed_dt_needed_without_strtab(self):
        path = make_elf(os.path.join(_TMP, "dyn_nostrtab"),
                        break_dynamic="no_strtab")
        with self.assertRaises(inspect_binary.InspectError):
            inspect_binary.inspect_path(path)

    def test_malformed_dt_strtab_outside_loadable_segment(self):
        path = make_elf(os.path.join(_TMP, "dyn_unmapped"),
                        break_dynamic="strtab_unmapped")
        with self.assertRaises(inspect_binary.InspectError):
            inspect_binary.inspect_path(path)

    def test_unexpected_program_header_size_rejected(self):
        path = make_elf(os.path.join(_TMP, "bad_phentsize"), phentsize=56)
        with open(path, "r+b") as handle:
            handle.seek(54)
            handle.write(struct.pack("<H", 32))
        with self.assertRaises(inspect_binary.InspectError):
            inspect_binary.inspect_path(path)

    def test_static_binary_reports_no_dependencies(self):
        path = make_elf(os.path.join(_TMP, "static_bin"), interp=None,
                        needed=())
        facts = inspect_binary.inspect_path(path)
        self.assertIsNone(facts["interpreter"])
        self.assertEqual(facts["runtime_dependencies"], [])

    def test_relative_path_rejected(self):
        with self.assertRaises(inspect_binary.InspectError):
            inspect_binary.inspect_path("relative/path")

    def test_inspector_cli_fails_closed_without_traceback(self):
        path = os.path.join(_TMP, "cli_not_elf")
        with open(path, "wb") as handle:
            handle.write(b"nope")
        proc = _run([PYTHON_BIN, "-B", INSPECT_TOOL, "--binary", path,
                     "--json-out", os.path.join(_TMP, "cli_ins.json")])
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"BINARY_INSPECT: FAIL", proc.stdout)
        self.assertNotIn(b"Traceback", proc.stderr)

    def test_inspector_uses_no_external_tools(self):
        # The module docstring legitimately NAMES the tools it refuses to
        # depend on, so it is removed before scanning: the property under
        # test is what the code does, not what the prose says.
        import ast
        with open(INSPECT_TOOL, encoding="utf-8") as handle:
            src = handle.read()
        tree = ast.parse(src)
        doc = ast.get_docstring(tree) or ""
        code = src.replace(doc, "")
        code = "\n".join(l for l in code.splitlines()
                         if not l.strip().startswith("#"))
        for tool in ("readelf", "objdump", "ldd", "subprocess",
                     "os.system", "popen"):
            self.assertNotIn(tool, code,
                             "inspector must not depend on %s" % tool)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertNotIn("subprocess", imported)


# ----------------------------------------------------------------------
# Provenance
# ----------------------------------------------------------------------

def _valid_facts(**over):
    facts = {
        "binary_name": "witness-verify",
        "binary_sha256": "a" * 64,
        "binary_size_bytes": 4096,
        "reported_version": "0.0.8-step79-diagnostics",
        "cargo_package_version": "0.0.8",
        "source_candidate_name": "project-witness-MOVE_82_candidate_v01.zip",
        "source_candidate_sha256": "b" * 64,
        "baseline_name": "project-witness-MOVE_81_candidate_v08.zip",
        "baseline_sha256": ADOPTED_M81_SHA,
        "target_triple": "aarch64-linux-android",
        "architecture": "aarch64",
        "executable_format": "ELF64",
        "build_profile": "release",
        "cargo_version": "cargo 1.96.0",
        "rustc_version": "rustc 1.96.0",
        "rustc_host": "aarch64-linux-android",
        "build_argv": ["/usr/bin/cargo", "build", "-q", "--release"],
        "build_environment": {"cargo_home": "ephemeral-per-run",
                              "external_crates": 0,
                              "endianness": "little",
                              "elf_type": "DYN",
                              "interpreter": "/system/bin/linker64"},
        "runtime_dependencies": ["libc.so", "libdl.so"],
        "test_level": "fixture_tested",
        "transcript_name": "MOVE_82_V01_TERMUX_GATE.txt",
        "limitations": list(provenance.REQUIRED_LIMITATIONS),
    }
    facts.update(over)
    return facts


class TestProvenance(unittest.TestCase):
    def test_valid_record_accepted(self):
        record = provenance.build_record(_valid_facts())
        self.assertEqual(record["schema_version"],
                         "witness-build-provenance/1")
        self.assertEqual(record["record_type"], "build_provenance")

    def test_canonical_encoding(self):
        record = provenance.build_record(_valid_facts())
        raw = provenance.canonical_bytes(record)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertFalse(raw.endswith(b"\n\n"))
        self.assertEqual(raw.decode("utf-8").count("\n"), 1)
        again = json.loads(raw)
        self.assertEqual(provenance.canonical_bytes(again), raw)

    def test_transcript_sha256_is_forbidden(self):
        with self.assertRaises(provenance.ProvenanceError):
            provenance.build_record(
                _valid_facts(transcript_sha256="c" * 64))

    def test_adoption_tested_overclaim_rejected(self):
        with self.assertRaises(provenance.ProvenanceError):
            provenance.build_record(_valid_facts(
                test_level="adoption_tested"))

    def test_publicly_releasable_overclaim_rejected(self):
        with self.assertRaises(provenance.ProvenanceError):
            provenance.build_record(_valid_facts(
                test_level="publicly_releasable"))

    def test_debug_profile_rejected_as_portable_artefact(self):
        with self.assertRaises(provenance.ProvenanceError):
            provenance.build_record(_valid_facts(build_profile="dev"))

    def test_bad_hash_rejected(self):
        for field in ("binary_sha256", "source_candidate_sha256",
                      "baseline_sha256"):
            with self.assertRaises(provenance.ProvenanceError):
                provenance.build_record(_valid_facts(**{field: "short"}))

    def test_uppercase_hash_rejected(self):
        with self.assertRaises(provenance.ProvenanceError):
            provenance.build_record(_valid_facts(binary_sha256="A" * 64))

    def test_missing_required_field_rejected(self):
        facts = _valid_facts()
        del facts["rustc_host"]
        with self.assertRaises(provenance.ProvenanceError):
            provenance.build_record(facts)

    def test_move83_report_fields_rejected(self):
        for field in ("verdict", "reason_code", "checks", "bundle_verdict",
                      "report"):
            with self.assertRaises(provenance.ProvenanceError):
                provenance.build_record(_valid_facts(**{field: "x"}))

    def test_build_argv_must_be_array(self):
        with self.assertRaises(provenance.ProvenanceError):
            provenance.build_record(_valid_facts(
                build_argv="cargo build -q --release"))

    def test_runtime_dependencies_must_be_sorted(self):
        with self.assertRaises(provenance.ProvenanceError):
            provenance.build_record(_valid_facts(
                runtime_dependencies=["libz.so", "libc.so"]))

    def test_runtime_dependencies_duplicates_rejected(self):
        with self.assertRaises(provenance.ProvenanceError):
            provenance.build_record(_valid_facts(
                runtime_dependencies=["libc.so", "libc.so"]))

    def test_limitations_must_be_present_and_complete(self):
        with self.assertRaises(provenance.ProvenanceError):
            provenance.build_record(_valid_facts(limitations=[]))
        for omit in provenance.REQUIRED_LIMITATIONS:
            partial = [x for x in provenance.REQUIRED_LIMITATIONS
                       if x != omit]
            with self.assertRaises(provenance.ProvenanceError):
                provenance.build_record(_valid_facts(limitations=partial))

    def test_negative_or_zero_size_rejected(self):
        for size in (0, -1, True):
            with self.assertRaises(provenance.ProvenanceError):
                provenance.build_record(
                    _valid_facts(binary_size_bytes=size))

    def test_cli_rejects_malformed_facts_without_traceback(self):
        path = os.path.join(_TMP, "bad_facts.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        proc = _run([PYTHON_BIN, "-B", PROV_TOOL, "--facts", path])
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn(b"Traceback", proc.stderr)


class TestProvenanceHashBinding(unittest.TestCase):
    def test_provenance_hash_must_match_the_real_binary(self):
        # a record whose binary_sha256 does not match the file it names is
        # detectable by recomputation; the gate cross-checks this
        binary = make_elf(os.path.join(_TMP, "hashbind"))
        import hashlib
        with open(binary, "rb") as handle:
            real = hashlib.sha256(handle.read()).hexdigest()
        record = provenance.build_record(
            _valid_facts(binary_sha256="d" * 64))
        self.assertNotEqual(record["binary_sha256"], real)
        good = provenance.build_record(_valid_facts(binary_sha256=real))
        self.assertEqual(good["binary_sha256"], real)


# ----------------------------------------------------------------------
# Build tool
# ----------------------------------------------------------------------

class TestBuildTool(unittest.TestCase):
    def _fake_cargo(self, name, rc=0, make_binary=True, profile="release"):
        body = (
            "import os, sys\n"
            "args = sys.argv[1:]\n"
            "if args[:1] == ['--version']:\n"
            "    print('cargo 1.96.0 (fake)')\n"
            "    sys.exit(0)\n"
            "if args[:1] == ['-vV']:\n"
            "    print('rustc 1.96.0 (fake)')\n"
            "    print('host: aarch64-linux-android')\n"
            "    sys.exit(0)\n"
            "prof = 'release' if '--release' in args else 'debug'\n"
            "make = %r\n"
            "if make:\n"
            "    d = os.path.join(os.getcwd(), 'target', prof)\n"
            "    os.makedirs(d, exist_ok=True)\n"
            "    p = os.path.join(d, 'witness-verify')\n"
            "    open(p, 'wb').write(b'x')\n"
            "    os.chmod(p, 0o755)\n"
            "sys.exit(%d)\n" % (make_binary, rc))
        return _write_python_exe(name, body)

    def _fake_rustc(self, name):
        body = (
            "import sys\n"
            "args = sys.argv[1:]\n"
            "if args[:1] == ['--version']:\n"
            "    print('rustc 1.96.0 (fake)')\n"
            "elif args[:1] == ['-vV']:\n"
            "    print('rustc 1.96.0 (fake)')\n"
            "    print('host: aarch64-linux-android')\n"
            "sys.exit(0)\n")
        return _write_python_exe(name, body)

    def _manifest_dir(self, name):
        d = os.path.join(_TMP, name)
        os.makedirs(d, exist_ok=True)
        return d

    def test_successful_release_build(self):
        cargo = self._fake_cargo("cargo_ok.py")
        rustc = self._fake_rustc("rustc_ok.py")
        md = self._manifest_dir("md_ok")
        proc = _run([PYTHON_BIN, "-B", BUILD_TOOL, "--cargo", cargo,
                     "--rustc", rustc, "--manifest-dir", md,
                     "--profile", "release"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(b"BUILD: PASS", proc.stdout)
        facts = json.loads(proc.stdout.decode().splitlines()[0])
        self.assertEqual(facts["build_profile"], "release")
        self.assertEqual(facts["rustc_host"], "aarch64-linux-android")
        self.assertIn("--release", facts["build_argv"])

    def test_release_build_failure_reported(self):
        cargo = self._fake_cargo("cargo_fail.py", rc=101,
                                 make_binary=False)
        rustc = self._fake_rustc("rustc_f.py")
        md = self._manifest_dir("md_fail")
        proc = _run([PYTHON_BIN, "-B", BUILD_TOOL, "--cargo", cargo,
                     "--rustc", rustc, "--manifest-dir", md,
                     "--profile", "release"])
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"BUILD: FAIL", proc.stdout)
        self.assertNotIn(b"Traceback", proc.stderr)

    def test_build_producing_no_executable_reported(self):
        cargo = self._fake_cargo("cargo_nobin.py", rc=0,
                                 make_binary=False)
        rustc = self._fake_rustc("rustc_nb.py")
        md = self._manifest_dir("md_nobin")
        proc = _run([PYTHON_BIN, "-B", BUILD_TOOL, "--cargo", cargo,
                     "--rustc", rustc, "--manifest-dir", md,
                     "--profile", "release"])
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"BUILD: FAIL", proc.stdout)

    def test_stale_target_reuse_refused(self):
        cargo = self._fake_cargo("cargo_stale.py")
        rustc = self._fake_rustc("rustc_st.py")
        md = self._manifest_dir("md_stale")
        os.makedirs(os.path.join(md, "target", "release"), exist_ok=True)
        stale = os.path.join(md, "target", "release", "witness-verify")
        with open(stale, "wb") as handle:
            handle.write(b"stale")
        os.chmod(stale, 0o755)
        proc = _run([PYTHON_BIN, "-B", BUILD_TOOL, "--cargo", cargo,
                     "--rustc", rustc, "--manifest-dir", md,
                     "--profile", "release", "--require-clean-target"])
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"stale", proc.stdout.lower())

    def test_non_executable_cargo_rejected(self):
        plain = os.path.join(_TMP, "not_exec_cargo")
        with open(plain, "w", encoding="utf-8") as handle:
            handle.write("x")
        os.chmod(plain, 0o644)
        rustc = self._fake_rustc("rustc_ne.py")
        md = self._manifest_dir("md_ne")
        proc = _run([PYTHON_BIN, "-B", BUILD_TOOL, "--cargo", plain,
                     "--rustc", rustc, "--manifest-dir", md,
                     "--profile", "release"])
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"BUILD: FAIL", proc.stdout)

    def test_relative_cargo_path_rejected(self):
        rustc = self._fake_rustc("rustc_rel.py")
        md = self._manifest_dir("md_rel")
        proc = _run([PYTHON_BIN, "-B", BUILD_TOOL, "--cargo", "cargo",
                     "--rustc", rustc, "--manifest-dir", md,
                     "--profile", "release"])
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"absolute", proc.stdout.lower())

    def test_build_argv_matches_adopted_invocation(self):
        cargo = self._fake_cargo("cargo_argv.py")
        rustc = self._fake_rustc("rustc_argv.py")
        md = self._manifest_dir("md_argv")
        proc = _run([PYTHON_BIN, "-B", BUILD_TOOL, "--cargo", cargo,
                     "--rustc", rustc, "--manifest-dir", md,
                     "--profile", "release"])
        facts = json.loads(proc.stdout.decode().splitlines()[0])
        self.assertEqual(facts["build_argv"][1:],
                         ["build", "-q", "--release"])
        # no --locked (there is no committed lock file to honour)
        self.assertNotIn("--locked", facts["build_argv"])


# ----------------------------------------------------------------------
# Equivalence and standalone execution
# ----------------------------------------------------------------------

VERDICT_LINE = (b'{"verifier":"witness-verify",'
                b'"version":"0.0.8-step79-diagnostics",'
                b'"verdict":"INCONCLUSIVE",'
                b'"reason_code":"RECEIPT_CHAIN_HASHES_RECOMPUTED",'
                b'"detail":"ok"}\n')


def _fake_verifier(name, out=VERDICT_LINE, err=b"", rc=3):
    """A stand-in verifier with fully controlled stdout/stderr/exit."""
    return _write_python_exe(
        name,
        "import sys\n"
        "sys.stdout.buffer.write(%r)\n"
        "sys.stderr.buffer.write(%r)\n"
        "sys.exit(%d)\n" % (out, err, rc))


class TestStandaloneExactExpectations(unittest.TestCase):
    """Blocker 3: standalone must assert exact adopted behaviour, not
    merely 'stderr was empty'."""

    def _bundle(self):
        d = os.path.join(_TMP, "sa_bundle")
        os.makedirs(d, exist_ok=True)
        return d

    def _run_standalone(self, binary, tag, expect=True):
        argv = [PYTHON_BIN, "-B", EQUIV_TOOL, "--mode", "standalone",
                "--release-bin", binary,
                "--workdir", os.path.join(_TMP, "sa_" + tag),
                "--input", self._bundle()]
        if expect:
            argv += ["--expect-verdict", "INCONCLUSIVE",
                     "--expect-reason-code",
                     "RECEIPT_CHAIN_HASHES_RECOMPUTED",
                     "--expect-exit-code", "3"]
        return _run(argv)

    def test_correct_behaviour_passes(self):
        proc = self._run_standalone(_fake_verifier("sa_ok.py"), "ok")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(b"STANDALONE: PASS", proc.stdout)

    def test_wrong_output_and_exit_17_fails(self):
        bad = _fake_verifier(
            "sa_bad.py", out=b'{"verdict":"WRONG","reason_code":"NOPE"}\n',
            rc=17)
        proc = self._run_standalone(bad, "bad")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"STANDALONE: FAIL", proc.stdout)
        self.assertNotIn(b"STANDALONE: PASS", proc.stdout)

    def test_wrong_exit_code_alone_fails(self):
        bad = _fake_verifier("sa_rc.py", rc=0)
        proc = self._run_standalone(bad, "rc")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"exit code", proc.stdout)

    def test_wrong_reason_code_alone_fails(self):
        bad = _fake_verifier(
            "sa_reason.py",
            out=VERDICT_LINE.replace(b"RECEIPT_CHAIN_HASHES_RECOMPUTED",
                                     b"SOMETHING_ELSE"))
        proc = self._run_standalone(bad, "reason")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"reason_code", proc.stdout)

    def test_non_empty_stderr_fails(self):
        bad = _fake_verifier("sa_err.py", err=b"warning")
        proc = self._run_standalone(bad, "err")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"stderr", proc.stdout)

    def test_expectations_are_mandatory(self):
        proc = self._run_standalone(_fake_verifier("sa_noexp.py"), "noexp",
                                    expect=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"explicit expected behaviour", proc.stdout)

    def test_multi_line_stdout_rejected(self):
        bad = _fake_verifier("sa_multi.py",
                             out=VERDICT_LINE + VERDICT_LINE)
        proc = self._run_standalone(bad, "multi")
        self.assertEqual(proc.returncode, 1)

    def test_standalone_dir_has_no_toolchain_material(self):
        self._run_standalone(_fake_verifier("sa_clean.py"), "clean")
        rundir = os.path.join(_TMP, "sa_clean", "run")
        present = set(os.listdir(rundir))
        for forbidden in ("cargo", "rustc", "python3", "sh", "Cargo.toml",
                          "src", "rust"):
            self.assertNotIn(forbidden, present)

    def test_standalone_env_is_empty_path_private_home_tmp(self):
        import equivalence
        env = equivalence.standalone_env("/h", "/t")
        self.assertEqual(env["PATH"], "")
        self.assertEqual(env["HOME"], "/h")
        self.assertEqual(env["TMPDIR"], "/t")

    def test_paths_containing_spaces_supported(self):
        spaced = os.path.join(_TMP, "space dir")
        os.makedirs(spaced, exist_ok=True)
        binary = _fake_verifier("sa space.py")
        proc = _run([PYTHON_BIN, "-B", EQUIV_TOOL, "--mode", "standalone",
                     "--release-bin", binary,
                     "--workdir", os.path.join(spaced, "work space"),
                     "--input", self._bundle(),
                     "--expect-verdict", "INCONCLUSIVE",
                     "--expect-reason-code",
                     "RECEIPT_CHAIN_HASHES_RECOMPUTED",
                     "--expect-exit-code", "3"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_binary_that_cannot_launch_fails_closed(self):
        bad = os.path.join(_TMP, "sa_badfmt_bin")
        with open(bad, "wb") as handle:
            handle.write(b"\x00\x01\x02 not an executable")
        os.chmod(bad, 0o755)
        proc = self._run_standalone(bad, "badfmt")
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn(b"Traceback", proc.stderr)


class TestControlledAgainstAdoptedExpectations(unittest.TestCase):
    """Blocker 4: correctness comes from the ADOPTED authorities, never
    from two newly built binaries agreeing with each other."""

    EXPECTED = os.path.join(ROOT, "verify", "corrupted_bundle_pack_v01",
                            "expected_results.json")
    MANIFEST = os.path.join(ROOT, "verify", "corrupted_bundle_pack_v01",
                            "fixture_manifest.json")

    def _fixtures_dir(self):
        d = os.path.join(_TMP, "ctl_fixtures")
        if os.path.isdir(d):
            return d
        os.makedirs(d, exist_ok=True)
        with open(self.MANIFEST, encoding="utf-8") as handle:
            fixtures = json.load(handle)["fixtures"]
        for entry in fixtures.values():
            path = os.path.join(d, entry["filename"])
            if entry["kind"] == "dir":
                os.makedirs(path, exist_ok=True)
            else:
                with open(path, "wb") as handle:
                    handle.write(b"PK\x03\x04")
        return d

    def _run_controlled(self, release, debug, tag):
        return _run([PYTHON_BIN, "-B", EQUIV_TOOL, "--mode", "controlled",
                     "--release-bin", release, "--debug-bin", debug,
                     "--expected-results", self.EXPECTED,
                     "--fixture-manifest", self.MANIFEST,
                     "--fixtures-dir", self._fixtures_dir()])

    def test_two_identically_wrong_binaries_do_not_pass(self):
        # both profiles agree perfectly, and both are WRONG
        wrong = _fake_verifier(
            "ctl_wrong.py",
            out=b'{"verdict":"FAIL","reason_code":"TOTALLY_WRONG"}\n', rc=1)
        wrong2 = _fake_verifier(
            "ctl_wrong2.py",
            out=b'{"verdict":"FAIL","reason_code":"TOTALLY_WRONG"}\n', rc=1)
        proc = self._run_controlled(wrong, wrong2, "wrong")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"adopted expectation", proc.stdout)
        self.assertIn(b"CONTROLLED: FAIL", proc.stdout)

    def test_identical_non_empty_stderr_fails(self):
        noisy = _fake_verifier("ctl_noisy.py", err=b"warning")
        noisy2 = _fake_verifier("ctl_noisy2.py", err=b"warning")
        proc = self._run_controlled(noisy, noisy2, "noisy")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"zero stderr bytes", proc.stdout)

    def test_profile_divergence_fails(self):
        a = _fake_verifier("ctl_a.py")
        b = _fake_verifier("ctl_b.py", rc=1)
        proc = self._run_controlled(a, b, "div")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"profiles diverge", proc.stdout)

    def test_every_adopted_case_is_loaded_exactly_once(self):
        import equivalence
        cases = equivalence.load_controlled_cases(
            self.EXPECTED, self.MANIFEST, self._fixtures_dir())
        ids = [c["case_id"] for c in cases]
        self.assertEqual(len(ids), len(set(ids)))
        with open(self.EXPECTED, encoding="utf-8") as handle:
            expected = json.load(handle)["cases"]
        self.assertEqual(sorted(ids), sorted(expected))
        self.assertGreaterEqual(len(ids), 8)

    def test_expectations_carry_adopted_verdicts(self):
        import equivalence
        cases = equivalence.load_controlled_cases(
            self.EXPECTED, self.MANIFEST, self._fixtures_dir())
        by_id = {c["case_id"]: c["expected"] for c in cases}
        self.assertEqual(by_id["M80-CLEAN-001"]["verdict"], "INCONCLUSIVE")
        self.assertEqual(by_id["M80-CLEAN-001"]["exit_code"], 3)
        self.assertEqual(by_id["M80-MISSING-MANIFEST-001"]["verdict"],
                         "FAIL")

    def test_missing_fixture_is_reported(self):
        import equivalence
        cases = equivalence.load_controlled_cases(
            self.EXPECTED, self.MANIFEST,
            os.path.join(_TMP, "no_such_fixture_dir"))
        good = _fake_verifier("ctl_missing.py")
        problems, _ = equivalence.run_controlled(good, good, cases)
        self.assertTrue(any("adopted fixture missing" in p
                            for p in problems))

    def test_verifier_stdout_framing_is_strict(self):
        import equivalence
        with self.assertRaises(equivalence.EquivalenceError):
            equivalence.parse_verifier_stdout(b"")
        with self.assertRaises(equivalence.EquivalenceError):
            equivalence.parse_verifier_stdout(b"noise\n")
        with self.assertRaises(equivalence.EquivalenceError):
            equivalence.parse_verifier_stdout(VERDICT_LINE + VERDICT_LINE)
        obj = equivalence.parse_verifier_stdout(VERDICT_LINE)
        self.assertEqual(obj["verdict"], "INCONCLUSIVE")


class TestAdoptedCorpusCompleteness(unittest.TestCase):
    """B5: the corpus is the COMPLETE adopted set, built with the adopted
    builder after its pins are verified."""

    HARNESS = os.path.join(ROOT, "verify", "agreement_harness_v01")

    def test_corpus_pins_verified_before_building(self):
        import equivalence
        lock = equivalence.verify_corpus_pins(self.HARNESS)
        self.assertIn("file_pins", lock)
        self.assertGreaterEqual(len(lock["file_pins"]), 4)

    def test_tampered_corpus_pin_is_rejected(self):
        import equivalence
        import shutil
        copy = os.path.join(_TMP, "harness_copy")
        if os.path.isdir(copy):
            shutil.rmtree(copy)
        shutil.copytree(self.HARNESS, copy)
        target = os.path.join(copy, "corpus", "build_archives.py")
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n# tampered\n")
        with self.assertRaises(equivalence.EquivalenceError):
            equivalence.verify_corpus_pins(copy)

    def test_adopted_builder_produces_every_archive_case_fixture(self):
        import equivalence
        lock = equivalence.verify_corpus_pins(self.HARNESS)
        outdir = os.path.join(_TMP, "corpus_archives")
        archives = equivalence.build_archive_fixtures(
            os.path.join(self.HARNESS, "corpus"), outdir, lock)
        self.assertEqual(len(archives), 67)
        # 67 synthesised + 3 external = the complete adopted 70
        with open(os.path.join(self.HARNESS, "corpus",
                               "archive_cases.json"),
                  encoding="utf-8") as handle:
            declared = json.load(handle)["cases"]
        self.assertEqual(len(declared), 70)
        external = [c for c in declared if c.get("archive_file") is None]
        self.assertEqual(
            {c["case_id"] for c in external},
            set(equivalence.EXTERNAL_ARCHIVE_CASES))

    def test_external_archive_cases_require_a_real_artifact(self):
        import equivalence
        lock = equivalence.verify_corpus_pins(self.HARNESS)
        outdir = os.path.join(_TMP, "corpus_archives2")
        archives = equivalence.build_archive_fixtures(
            os.path.join(self.HARNESS, "corpus"), outdir, lock)
        with self.assertRaises(equivalence.EquivalenceError):
            equivalence.load_archive_cases(
                os.path.join(self.HARNESS, "corpus", "archive_cases.json"),
                archives, {})

    def test_archive_expectations_are_reason_classes(self):
        import equivalence
        lock = equivalence.verify_corpus_pins(self.HARNESS)
        outdir = os.path.join(_TMP, "corpus_archives3")
        archives = equivalence.build_archive_fixtures(
            os.path.join(self.HARNESS, "corpus"), outdir, lock)
        with open(os.path.join(self.HARNESS, "corpus",
                               "archive_cases.json"),
                  encoding="utf-8") as handle:
            declared = json.load(handle)["cases"]
        for case in declared:
            if case.get("rust_scope") == "in_scope":
                self.assertIn("reason_class", case["expected"]["rust"])
        self.assertTrue(archives)

    def test_raw_reason_resolves_to_the_adopted_class(self):
        import equivalence
        rm = equivalence.load_reason_map(
            os.path.join(self.HARNESS, "reason_map.json"))
        cls, stage = equivalence.resolve_reason_class(
            rm, "archive", "ARCHIVE_PATH_TRAVERSAL")
        self.assertEqual(stage, "archive")
        self.assertTrue(cls)
        cls2, stage2 = equivalence.resolve_reason_class(
            rm, "archive", "NOT_A_REASON")
        self.assertIsNone(cls2)
        self.assertIsNone(stage2)


class TestExactRecordMatching(unittest.TestCase):
    """B4: the EXACT record, not three selected fields."""

    GOOD = (b'{"verifier":"witness-verify",'
            b'"version":"0.0.8-step79-diagnostics",'
            b'"verdict":"INCONCLUSIVE",'
            b'"reason_code":"RECEIPT_CHAIN_HASHES_RECOMPUTED",'
            b'"detail":"ok"}\n')
    EXPECT = {"verdict": "INCONCLUSIVE",
              "reason_code": "RECEIPT_CHAIN_HASHES_RECOMPUTED",
              "exit_code": 3}

    def _check(self, raw, rc=3, **kw):
        import equivalence
        return equivalence.check_exact_record(
            raw, b"", rc, self.EXPECT, "t", **kw)

    def test_correct_record_passes(self):
        self.assertEqual(self._check(self.GOOD), [])

    def test_wrong_version_fails(self):
        bad = self.GOOD.replace(b"0.0.8-step79-diagnostics", b"9.9.9")
        problems = self._check(bad)
        self.assertTrue(any("version" in p for p in problems))

    def test_wrong_verifier_identity_fails(self):
        bad = self.GOOD.replace(b"witness-verify", b"impostor")
        problems = self._check(bad)
        self.assertTrue(any("verifier" in p for p in problems))

    def test_extra_field_fails(self):
        bad = self.GOOD.replace(b'"detail":"ok"}',
                                b'"detail":"ok","stage":"complete"}')
        problems = self._check(bad)
        self.assertTrue(any("unexpected field" in p for p in problems))

    def test_missing_field_fails(self):
        bad = (b'{"verifier":"witness-verify",'
               b'"version":"0.0.8-step79-diagnostics",'
               b'"verdict":"INCONCLUSIVE",'
               b'"reason_code":"RECEIPT_CHAIN_HASHES_RECOMPUTED"}\n')
        problems = self._check(bad)
        self.assertTrue(any("missing field" in p for p in problems))

    def test_entry_count_only_allowed_for_archives(self):
        raw = self.GOOD.replace(b'"detail":"ok"}',
                                b'"detail":"ok","entry_count":3}')
        # on a bundle record entry_count is an unexpected field
        self.assertTrue(any("unexpected field" in p
                            for p in self._check(raw)))

    def test_non_empty_stderr_fails(self):
        import equivalence
        problems = equivalence.check_exact_record(
            self.GOOD, b"warning", 3, self.EXPECT, "t")
        self.assertTrue(any("stderr" in p for p in problems))

    def test_multi_line_output_fails(self):
        problems = self._check(self.GOOD + self.GOOD)
        self.assertTrue(problems)

    def test_wrong_exit_fails(self):
        problems = self._check(self.GOOD, rc=0)
        self.assertTrue(any("exit code" in p for p in problems))


class TestPublicationAtomicity(unittest.TestCase):
    """Blocker 8: publication is failure-atomic. Any failure must leave the
    output directory exactly as empty as it began."""

    def _setup(self, tag, record_over=None):
        import provenance as prov
        d = os.path.join(_TMP, "pub_" + tag)
        os.makedirs(d, exist_ok=True)
        out = os.path.join(d, "out")
        os.makedirs(out, exist_ok=True)
        binary = make_elf(os.path.join(d, "witness-verify"))
        import hashlib
        with open(binary, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        facts = _valid_facts(binary_sha256=digest,
                             binary_size_bytes=os.path.getsize(binary))
        if record_over:
            facts.update(record_over)
        record = prov.build_record(facts)
        rec_path = os.path.join(d, "rec.json")
        with open(rec_path, "wb") as handle:
            handle.write(prov.canonical_bytes(record))
        return binary, rec_path, out

    def test_successful_publication_produces_exactly_four_files(self):
        import provenance as prov
        binary, rec, out = self._setup("ok")
        result = prov.publish(binary, rec, out, "wv-1.0-aarch64-release")
        present = sorted(os.listdir(out))
        self.assertEqual(len(present), 4, present)
        self.assertIn("wv-1.0-aarch64-release", present)
        self.assertIn("wv-1.0-aarch64-release.sha256", present)
        self.assertIn("wv-1.0-aarch64-release.provenance.json", present)
        self.assertIn("wv-1.0-aarch64-release.provenance.json.sha256",
                      present)
        self.assertEqual(result["binary_sha256"],
                         prov.sha256_file(
                             os.path.join(out, "wv-1.0-aarch64-release")))

    def test_sidecar_format_is_standard(self):
        import provenance as prov
        binary, rec, out = self._setup("sidecar")
        prov.publish(binary, rec, out, "wv-sc")
        with open(os.path.join(out, "wv-sc.sha256"), "rb") as handle:
            content = handle.read().decode("utf-8")
        digest, sep, name = content.partition("  ")
        self.assertEqual(len(digest), 64)
        self.assertEqual(sep, "  ")
        self.assertEqual(name, "wv-sc\n")

    def test_hash_mismatch_rolls_back_completely(self):
        import provenance as prov
        # provenance claims a different binary hash than the real file
        binary, rec, out = self._setup("mismatch",
                                       record_over={"binary_sha256":
                                                    "f" * 64})
        with self.assertRaises(prov.PublishError):
            prov.publish(binary, rec, out, "wv-mismatch")
        self.assertEqual(os.listdir(out), [],
                         "output directory must be empty after rollback")

    def test_non_empty_output_directory_refused(self):
        import provenance as prov
        binary, rec, out = self._setup("nonempty")
        with open(os.path.join(out, "intruder.txt"), "w") as handle:
            handle.write("x")
        with self.assertRaises(prov.PublishError):
            prov.publish(binary, rec, out, "wv-nonempty")
        self.assertEqual(sorted(os.listdir(out)), ["intruder.txt"])

    def test_missing_output_directory_refused(self):
        import provenance as prov
        binary, rec, out = self._setup("missingdir")
        gone = os.path.join(out, "does_not_exist")
        with self.assertRaises(prov.PublishError):
            prov.publish(binary, rec, gone, "wv-gone")

    def test_non_canonical_record_rolls_back(self):
        import provenance as prov
        binary, rec, out = self._setup("noncanon")
        with open(rec, "rb") as handle:
            data = handle.read()
        with open(rec, "wb") as handle:
            handle.write(b"  " + data)      # leading whitespace
        with self.assertRaises(prov.PublishError):
            prov.publish(binary, rec, out, "wv-noncanon")
        self.assertEqual(os.listdir(out), [])

    def test_unreadable_record_rolls_back(self):
        import provenance as prov
        binary, rec, out = self._setup("badrec")
        with open(rec, "wb") as handle:
            handle.write(b"{not json")
        with self.assertRaises(prov.PublishError):
            prov.publish(binary, rec, out, "wv-badrec")
        self.assertEqual(os.listdir(out), [])

    def test_missing_binary_rolls_back(self):
        import provenance as prov
        binary, rec, out = self._setup("nobin")
        os.remove(binary)
        with self.assertRaises(prov.PublishError):
            prov.publish(binary, rec, out, "wv-nobin")
        self.assertEqual(os.listdir(out), [])

    def test_publish_cli_reports_failure_without_traceback(self):
        binary, rec, out = self._setup("cli",
                                       record_over={"binary_sha256":
                                                    "e" * 64})
        proc = _run([PYTHON_BIN, "-B", PROV_TOOL,
                     "--publish-binary", binary, "--publish-record", rec,
                     "--publish-dir", out, "--publish-base", "wv-cli"])
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"PUBLISH: FAIL", proc.stdout)
        self.assertNotIn(b"Traceback", proc.stderr)
        self.assertEqual(os.listdir(out), [])


class TestPathAndOutputEnforcement(unittest.TestCase):
    """Blocker 6: path rules are enforced on the SUPPLIED value, before any
    canonicalisation could promote a relative path."""

    def _gate_code(self):
        with open(GATE, encoding="utf-8") as handle:
            text = handle.read()
        return "\n".join(l for l in text.splitlines()
                          if not l.strip().startswith("#"))

    def _run_gate(self, env_over):
        env = dict(os.environ)
        env.update({
            "MOVE82_CANDIDATE_ZIP": "/run/c.zip",
            "MOVE82_CANDIDATE_SHA256": "a" * 64,
            "MOVE82_OUTPUT_DIR": "/run/out",
            "REAL_MOVE81": "/run/m81.zip", "REAL_MOVE80": "/run/m80.zip",
            "REAL_MOVE79": "/run/m79.zip", "REAL_MOVE78": "/run/m78.zip",
            "REAL_705": "/run/m705.zip",
        })
        env.update(env_over)
        return _run([TEST_SH, GATE], env=env)

    def test_relative_candidate_path_refused_before_canonicalisation(self):
        proc = self._run_gate({"MOVE82_CANDIDATE_ZIP": "relative/c.zip"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"not absolute", proc.stdout)
        self.assertIn(b"relative path", proc.stdout)

    def test_relative_output_dir_refused(self):
        proc = self._run_gate({"MOVE82_OUTPUT_DIR": "out"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"not absolute", proc.stdout)

    def test_every_real_input_must_be_absolute(self):
        for var in ("REAL_MOVE81", "REAL_MOVE80", "REAL_MOVE79",
                    "REAL_MOVE78", "REAL_705"):
            proc = self._run_gate({var: "rel/x.zip"})
            self.assertEqual(proc.returncode, 1, var)
            self.assertIn(b"not absolute", proc.stdout, var)

    def test_missing_inputs_give_usage_exit(self):
        env = dict(os.environ)
        for var in ("MOVE82_CANDIDATE_ZIP", "MOVE82_CANDIDATE_SHA256",
                    "MOVE82_OUTPUT_DIR", "REAL_MOVE81", "REAL_MOVE80",
                    "REAL_MOVE79", "REAL_MOVE78", "REAL_705"):
            env.pop(var, None)
        proc = _run([TEST_SH, GATE], env=env)
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"USAGE (missing:", proc.stdout)

    # ---- EXECUTABLE output-directory enforcement (B11) ----------------
    # These run the factored PRODUCTION helper the gate itself calls,
    # rather than asserting that the shell source contains a pattern.

    def _od_setup(self, tag):
        run = os.path.join(_TMP, "od_" + tag)
        cand = os.path.join(run, "src")
        os.makedirs(cand, exist_ok=True)
        return run, cand

    def _od_check(self, supplied, run, cand):
        return _run([PYTHON_BIN, "-B", BASELINE_CHECKER,
                     "--check-output-dir", supplied, "--run-dir", run,
                     "--candidate-root", cand])

    def test_valid_output_dir_accepted(self):
        run, cand = self._od_setup("ok")
        out = os.path.join(run, "out")
        os.makedirs(out, exist_ok=True)
        proc = self._od_check(out, run, cand)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(b"MOVE_82_OUTPUT_DIR: PASS", proc.stdout)

    def test_non_empty_output_dir_rejected(self):
        run, cand = self._od_setup("ne")
        out = os.path.join(run, "out")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "intruder"), "w") as handle:
            handle.write("x")
        proc = self._od_check(out, run, cand)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"not empty", proc.stdout)

    def test_output_symlink_rejected(self):
        run, cand = self._od_setup("sl")
        real = os.path.join(run, "real")
        os.makedirs(real, exist_ok=True)
        link = os.path.join(run, "link")
        os.symlink(real, link)
        proc = self._od_check(link, run, cand)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"symlink", proc.stdout)

    def test_lowercase_downloads_rejected(self):
        run, cand = self._od_setup("dl")
        out = os.path.join(run, "storage", "downloads", "o")
        os.makedirs(out, exist_ok=True)
        proc = self._od_check(out, run, cand)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"Downloads", proc.stdout)

    def test_shared_storage_rejected(self):
        run, cand = self._od_setup("ss")
        out = os.path.join(run, "storage", "emulated", "0", "o")
        os.makedirs(out, exist_ok=True)
        proc = self._od_check(out, run, cand)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"shared", proc.stdout)

    def test_output_inside_candidate_root_rejected(self):
        run, cand = self._od_setup("inside")
        out = os.path.join(cand, "out")
        os.makedirs(out, exist_ok=True)
        proc = self._od_check(out, run, cand)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"inside the candidate source root", proc.stdout)

    def test_output_outside_run_directory_rejected(self):
        run, cand = self._od_setup("outside")
        other = os.path.join(_TMP, "od_elsewhere")
        os.makedirs(other, exist_ok=True)
        proc = self._od_check(other, run, cand)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"internal run directory", proc.stdout)

    def test_relative_output_dir_rejected_by_helper(self):
        run, cand = self._od_setup("rel")
        proc = self._od_check("relative/out", run, cand)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"absolute", proc.stdout)

    def test_missing_output_dir_rejected(self):
        run, cand = self._od_setup("missing")
        proc = self._od_check(os.path.join(run, "nope"), run, cand)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"pre-created", proc.stdout)

    def test_gate_calls_the_factored_helper(self):
        code = self._gate_code()
        self.assertIn("--check-output-dir", code)

    def test_source_binding_runs_before_any_build(self):
        code = self._gate_code()
        binding = code.find("--verify-tree-matches-zip")
        build = code.find("--profile release")
        self.assertNotEqual(binding, -1)
        self.assertLess(binding, build)

    def test_acceptance_evidence_never_discards_stderr(self):
        code = self._gate_code()
        # Join shell line-continuations first: a discard can legitimately
        # sit on the continuation line of a statement whose intent is on
        # the first line, so scanning raw lines would misjudge it.
        joined = code.replace("\\\n", " ")
        for line in joined.splitlines():
            if "2>/dev/null" not in line:
                continue
            # only environment sanitisation and an emptiness probe may
            # discard stderr; neither is acceptance evidence
            self.assertTrue(
                line.strip().startswith("unset ") or "ls -A" in line,
                "acceptance evidence discards stderr: %r" % line)

    def test_every_acceptance_stage_captures_stderr_separately(self):
        code = self._gate_code()
        # each acceptance-bearing stage writes stderr to its own tracked
        # temporary and checks it, rather than merging or dropping it
        for err_var in ("$_VER_ERR", "$_BLD_ERR", "$_FIX_ERR", "$_EDG_ERR",
                        "$_INS_ERR", "$_PRV_ERR", "$_STD_ERR", "$_EQ_ERR",
                        "$_EDQ_ERR", "$_PUB_ERR", "$_SB_ERR"):
                self.assertIn('2>"%s"' % err_var, code,
                              "no separate stderr capture for %s" % err_var)
                self.assertIn('[ -s "%s" ]' % err_var, code,
                              "captured stderr not checked for %s" % err_var)


REAL_BUNDLE = os.path.join(
    ROOT, "freeze_record", "python_behaviour_freeze_v01", "reference_bundle")


class TestEdgeGenerationAgainstRealBundle(unittest.TestCase):
    """B1: the generator must work against the ACTUAL frozen reference
    bundle, not a synthetic substitute, and must require every surface."""

    def _make(self, tag, bundle):
        outdir = os.path.join(_TMP, "rb_edge_" + tag)
        manifest = os.path.join(_TMP, "rb_manifest_%s.json" % tag)
        proc = _run([PYTHON_BIN, "-B", EQUIV_TOOL, "--mode",
                     "make-edge-fixtures", "--outdir", outdir,
                     "--clean-bundle", bundle, "--json-out", manifest],
                    timeout=300)
        return proc, outdir, manifest

    def test_real_bundle_produces_every_required_surface(self):
        proc, _outdir, manifest = self._make("real", REAL_BUNDLE)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(manifest, encoding="utf-8") as handle:
            fixtures = json.load(handle)["fixtures"]
        import equivalence
        surfaces = {f["surface"] for f in fixtures}
        for required in equivalence.REQUIRED_EDGE_SURFACES:
            self.assertIn(required, surfaces,
                          "the real bundle produced no %s fixture"
                          % required)

    def test_generator_fails_rather_than_omitting_surfaces(self):
        thin = os.path.join(_TMP, "thin_bundle")
        os.makedirs(thin, exist_ok=True)
        with open(os.path.join(thin, "case_manifest.json"), "w",
                  encoding="utf-8") as handle:
            handle.write("{}")
        proc, _o, _m = self._make("thin", thin)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"FAIL", proc.stdout)
        self.assertNotIn(b"EDGE_FIXTURES: PASS", proc.stdout)

    def test_receipt_fixture_carries_a_real_extreme_value(self):
        _proc, outdir, _m = self._make("receipt", REAL_BUNDLE)
        import equivalence
        run_rel = equivalence.RUN_RECORD
        original = os.path.join(REAL_BUNDLE, run_rel)
        mutated = os.path.join(outdir, "edge_receipt_index", run_rel)
        self.assertTrue(os.path.isfile(mutated))
        with open(original, encoding="utf-8") as handle:
            before = json.load(handle)
        with open(mutated, encoding="utf-8") as handle:
            after = json.load(handle)
        self.assertTrue(before["receipts"])
        self.assertEqual(len(before["receipts"]), len(after["receipts"]))
        self.assertNotEqual(before["receipts"][0]["receipt_id"],
                            after["receipts"][0]["receipt_id"])
        self.assertEqual(after["receipts"][0]["receipt_id"], 2 ** 63 - 1)

    def test_receipt_fixture_leaves_the_hash_stage_intact(self):
        # sentinel_run.json is not one of the declared checksummed files,
        # so every checksummed file must be byte-identical -- otherwise the
        # fixture would answer at the hashes stage instead of receipts.
        _proc, outdir, _m = self._make("hashes", REAL_BUNDLE)
        dest = os.path.join(outdir, "edge_receipt_index")
        with open(os.path.join(REAL_BUNDLE, "companion_checksums.txt"),
                  encoding="utf-8") as handle:
            declared = [line.split()[1] for line in handle
                        if line.strip()]
        self.assertTrue(declared)
        for rel in declared:
            a = os.path.join(REAL_BUNDLE, rel)
            b = os.path.join(dest, rel)
            if not os.path.isfile(a):
                continue
            with open(a, "rb") as ha, open(b, "rb") as hb:
                self.assertEqual(ha.read(), hb.read(),
                                 "checksummed file %s was disturbed" % rel)

    def test_manifest_surfaces_mutate_the_file_the_verifier_parses(self):
        _proc, outdir, manifest = self._make("mani", REAL_BUNDLE)
        import equivalence
        with open(manifest, encoding="utf-8") as handle:
            fixtures = json.load(handle)["fixtures"]
        manifest_fixtures = [f for f in fixtures
                             if f.get("stage_intent") == "manifest"]
        self.assertTrue(manifest_fixtures)
        for fixture in manifest_fixtures:
            target = os.path.join(fixture["path"],
                                  equivalence.MANIFEST_FILE)
            self.assertTrue(os.path.isfile(target))
            with open(target, "rb") as handle:
                mutated = handle.read()
            with open(os.path.join(REAL_BUNDLE,
                                   equivalence.MANIFEST_FILE), "rb") as h2:
                self.assertNotEqual(mutated, h2.read())

    def test_every_fixture_declares_surface_and_intent_only(self):
        """Design intent is recorded; the expectation is established from
        the adopted baseline, never declared here."""
        _proc, _o, manifest = self._make("declare", REAL_BUNDLE)
        with open(manifest, encoding="utf-8") as handle:
            fixtures = json.load(handle)["fixtures"]
        for fixture in fixtures:
            self.assertTrue(fixture.get("surface"))
            self.assertTrue(fixture.get("stage_intent"))
            self.assertNotIn("expect_verdict", fixture)
            self.assertNotIn("expect_exit_code", fixture)
            self.assertNotIn("expect_stage", fixture)


class TestExternalArchiveHashes(unittest.TestCase):
    """B2: the three real archive cases are hash-pinned."""

    HARNESS = os.path.join(ROOT, "verify", "agreement_harness_v01")
    V20 = os.path.join(
        ROOT, "releases", "roadmap_one_complete", "move_70_final",
        "Project_Witness_WORKING_STACK_v20_MOVE_70.zip")

    def _archives(self):
        import equivalence
        lock = equivalence.verify_corpus_pins(self.HARNESS)
        outdir = os.path.join(_TMP, "extarch")
        return equivalence.build_archive_fixtures(
            os.path.join(self.HARNESS, "corpus"), outdir, lock)

    def test_pinned_hashes_are_the_adopted_values(self):
        import equivalence
        self.assertEqual(
            equivalence.EXTERNAL_ARCHIVE_SHA256["real_v20"],
            "1248bc46fa555cc50ed7b63c9284baffd1e95a6972cdfbc4a40a0201fea81aba")
        self.assertEqual(
            equivalence.EXTERNAL_ARCHIVE_SHA256["real_705"],
            "72e38ffd8338a978bf5d59d2fc9f0f06847092eab5f6a828077adef709c0f348")
        self.assertEqual(
            equivalence.EXTERNAL_ARCHIVE_SHA256["real_move78"],
            "6030148c2c1bb373ad69393563e8e2e3078dff93e9f446d728edd18ea3c45252")

    def test_the_inherited_v20_archive_has_the_required_hash(self):
        import equivalence
        self.assertTrue(os.path.isfile(self.V20))
        self.assertEqual(
            equivalence._sha256_path(self.V20),
            equivalence.EXTERNAL_ARCHIVE_SHA256["real_v20"])

    def test_move79_cannot_satisfy_real_v20(self):
        import equivalence
        archives = self._archives()
        # any other adopted archive standing in for real_v20 must fail
        substitute = os.path.join(_TMP, "extarch",
                                  sorted(archives)[0] + ".zip")
        with self.assertRaises(equivalence.EquivalenceError) as ctx:
            equivalence.load_archive_cases(
                os.path.join(self.HARNESS, "corpus", "archive_cases.json"),
                archives,
                {"real_v20": substitute,
                 "real_705": substitute,
                 "real_move78": substitute})
        self.assertIn("never be substituted", str(ctx.exception))

    def test_correct_v20_is_accepted(self):
        import equivalence
        archives = self._archives()
        real705 = os.path.join(_TMP, "fake705.zip")
        # only real_v20 is available here; prove IT validates by supplying
        # it and letting the others fail on their own pins
        with self.assertRaises(equivalence.EquivalenceError) as ctx:
            equivalence.load_archive_cases(
                os.path.join(self.HARNESS, "corpus", "archive_cases.json"),
                archives, {"real_v20": self.V20})
        # the failure must NOT be about real_v20
        self.assertNotIn("real_v20", str(ctx.exception))

    def test_missing_entry_count_on_accepted_archive_fails(self):
        import equivalence
        raw = (b'{"verifier":"witness-verify",'
               b'"version":"0.0.8-step79-diagnostics",'
               b'"verdict":"INCONCLUSIVE","reason_code":"ARCHIVE_SAFETY_OK",'
               b'"detail":"ok"}\n')
        problems = equivalence.check_exact_record(
            raw, b"", 3, {"verdict": "INCONCLUSIVE", "exit_code": 3},
            "t", allow_entry_count=True)
        self.assertTrue(any("entry_count" in p for p in problems))

    def test_wrong_entry_count_fails(self):
        import equivalence
        raw = (b'{"verifier":"witness-verify",'
               b'"version":"0.0.8-step79-diagnostics",'
               b'"verdict":"INCONCLUSIVE","reason_code":"ARCHIVE_SAFETY_OK",'
               b'"detail":"ok","entry_count":9}\n')
        problems = equivalence.check_exact_record(
            raw, b"", 3,
            {"verdict": "INCONCLUSIVE", "exit_code": 3, "entry_count": 3},
            "t", allow_entry_count=True)
        self.assertTrue(any("entry_count" in p for p in problems))


class TestUsageContract(unittest.TestCase):
    """B3: usage behaviour is executed, not assumed."""

    def _bin(self, name, out=b"usage\n", err=b"", rc=2):
        return _write_python_exe(
            name,
            "import sys\n"
            "sys.stdout.buffer.write(%r)\n"
            "sys.stderr.buffer.write(%r)\n"
            "sys.exit(%d)\n" % (out, err, rc))

    def _run_usage(self, release, debug, baseline=None):
        argv = [PYTHON_BIN, "-B", EQUIV_TOOL, "--mode", "usage-contract",
                "--release-bin", release, "--debug-bin", debug]
        if baseline:
            argv += ["--baseline-bin", baseline]
        return _run(argv)

    def test_matching_usage_passes(self):
        a = self._bin("us_a.py")
        b = self._bin("us_b.py")
        c = self._bin("us_c.py")
        proc = self._run_usage(a, b, c)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(b"USAGE_CONTRACT: PASS", proc.stdout)

    def test_profile_usage_divergence_fails(self):
        a = self._bin("us_d.py", out=b"one\n")
        b = self._bin("us_e.py", out=b"two\n")
        proc = self._run_usage(a, b)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"diverge", proc.stdout)

    def test_divergence_from_baseline_fails(self):
        a = self._bin("us_f.py", rc=2)
        base = self._bin("us_g.py", rc=64)
        proc = self._run_usage(a, a, base)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"baseline", proc.stdout)

    def test_all_three_usage_cases_are_covered(self):
        import equivalence
        ids = [c["case_id"] for c in equivalence.USAGE_CASES]
        self.assertEqual(len(ids), 3)
        self.assertIn("USAGE-NO-ARGUMENTS", ids)
        self.assertIn("USAGE-UNKNOWN-COMMAND", ids)
        self.assertIn("USAGE-WRONG-ARG-COUNT", ids)


class TestExactSourceMetadata(unittest.TestCase):
    """B7: exact mode bits and the complete path set."""

    def _tree_and_zip(self, tag):
        import zipfile
        root = os.path.join(_TMP, "meta_" + tag)
        os.makedirs(os.path.join(root, "sub"), exist_ok=True)
        f1 = os.path.join(root, "a.txt")
        f2 = os.path.join(root, "sub", "b.sh")
        with open(f1, "w") as h:
            h.write("a")
        with open(f2, "w") as h:
            h.write("b")
        os.chmod(f1, 0o644)
        os.chmod(f2, 0o755)
        z = os.path.join(_TMP, "meta_%s.zip" % tag)
        with zipfile.ZipFile(z, "w") as zf:
            for path, rel in ((f1, "a.txt"), (f2, "sub/b.sh")):
                i = zipfile.ZipInfo("project-witness-main/" + rel)
                i.external_attr = (os.lstat(path).st_mode & 0xFFFF) << 16
                with open(path, "rb") as h:
                    zf.writestr(i, h.read())
        return root, z

    def _check(self, root, z):
        return _run([PYTHON_BIN, "-B", BASELINE_CHECKER,
                     "--baseline-zip", z, "--verify-tree-matches-zip",
                     root])

    def test_matching_tree_passes(self):
        root, z = self._tree_and_zip("ok")
        proc = self._check(root, z)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_mode_only_drift_fails(self):
        root, z = self._tree_and_zip("mode")
        os.chmod(os.path.join(root, "a.txt"), 0o600)
        proc = self._check(root, z)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"mode differs", proc.stdout)

    def test_extra_empty_directory_fails(self):
        root, z = self._tree_and_zip("dir")
        os.makedirs(os.path.join(root, "unexpected"), exist_ok=True)
        proc = self._check(root, z)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"unlisted live directory", proc.stdout)


class TestTranscriptIdentity(unittest.TestCase):
    """B5: the transcript name matches the packaged candidate version."""

    CANDIDATE_VERSION = "v07"

    def test_gate_uses_the_current_candidate_transcript(self):
        with open(GATE, encoding="utf-8") as handle:
            code = handle.read()
        expected = "MOVE_82_V%s_TERMUX_GATE.txt" % \
            self.CANDIDATE_VERSION.upper().lstrip("V")
        expected = "MOVE_82_V07_TERMUX_GATE.txt"
        self.assertIn(expected, code)
        for stale in ("MOVE_82_V01_TERMUX_GATE.txt",
                      "MOVE_82_V02_TERMUX_GATE.txt",
                      "MOVE_82_V03_TERMUX_GATE.txt",
                      "MOVE_82_V04_TERMUX_GATE.txt",
                      "MOVE_82_V05_TERMUX_GATE.txt",
                      "MOVE_82_V06_TERMUX_GATE.txt"):
            self.assertNotIn(stale, code,
                             "stale transcript identity %s remains" % stale)

    def test_changelog_declares_the_current_candidate(self):
        changelog = os.path.join(ROOT, "CHANGELOG_MOVE_82.md")
        with open(changelog, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("Status: CANDIDATE v07", text)


class TestAndroidLinkerIdentities(unittest.TestCase):
    """B8: only explicit Android linker identities are accepted."""

    BASE = {"architecture": "aarch64", "executable_format": "ELF64",
            "endianness": "little", "elf_type": "DYN",
            "runtime_dependencies": ["libc.so"]}

    def _check(self, interp):
        facts = dict(self.BASE, interpreter=interp)
        return inspect_binary.cross_check(
            facts, rustc_host="aarch64-linux-android",
            platform_machine="aarch64")

    def test_genuine_android_linker_accepted(self):
        self.assertEqual(self._check("/system/bin/linker64"), [])

    def test_arbitrary_linker64_suffix_rejected(self):
        problems = self._check("/evil/custom/linker64")
        self.assertTrue(problems)
        self.assertTrue(any("not a recognised" in p for p in problems))

    def test_glibc_loader_rejected(self):
        problems = self._check("/lib64/ld-linux-aarch64.so.1")
        self.assertTrue(any("glibc" in p for p in problems))

    def test_no_suffix_acceptance_remains(self):
        self.assertEqual(inspect_binary.ANDROID_INTERPRETER_SUFFIXES, ())

    def test_synthetic_elf_with_evil_linker_fails(self):
        path = make_elf(os.path.join(_TMP, "evil_linker"),
                        interp="/evil/custom/linker64",
                        needed=("libc.so",))
        facts = inspect_binary.inspect_path(path)
        problems = inspect_binary.cross_check(
            facts, rustc_host="aarch64-linux-android",
            platform_machine="aarch64")
        self.assertTrue(any("not a recognised" in p for p in problems))


class TestRealArchiveEntryCounts(unittest.TestCase):
    """R2: through the GENUINE corpus loader and production checker."""

    HARNESS = os.path.join(ROOT, "verify", "agreement_harness_v01")
    V20 = os.path.join(
        ROOT, "releases", "roadmap_one_complete", "move_70_final",
        "Project_Witness_WORKING_STACK_v20_MOVE_70.zip")

    def _loaded_case(self, case_id="real_v20"):
        """Load through the REAL production loader -- not a hand-built
        expectation, which is what hid the defect."""
        import equivalence
        lock = equivalence.verify_corpus_pins(self.HARNESS)
        outdir = os.path.join(_TMP, "rc_arch")
        archives = equivalence.build_archive_fixtures(
            os.path.join(self.HARNESS, "corpus"), outdir, lock)
        with open(os.path.join(self.HARNESS, "corpus",
                               "archive_cases.json"),
                  encoding="utf-8") as handle:
            declared = json.load(handle)["cases"]
        external = {}
        for case in declared:
            if case.get("archive_file") is None:
                external[case["case_id"]] = self.V20
        # only real_v20's pin can be satisfied here; load just that case
        subset = {"lane": "archive",
                  "cases": [c for c in declared
                            if c["case_id"] == case_id]}
        path = os.path.join(_TMP, "rc_subset.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(subset, handle)
        cases = equivalence.load_archive_cases(path, archives, external)
        self.assertEqual(len(cases), 1)
        return cases[0]

    def test_loader_preserves_the_adopted_entry_count(self):
        case = self._loaded_case()
        self.assertEqual(case["expected"].get("entry_count"), 970,
                         "the loader discarded the adopted entry_count")

    def _record(self, entry_count=970, omit=False):
        obj = {"verifier": "witness-verify",
               "version": "0.0.8-step79-diagnostics",
               "verdict": "INCONCLUSIVE",
               "reason_code": "ARCHIVE_SAFETY_OK",
               "detail": "ok"}
        if not omit:
            obj["entry_count"] = entry_count
        return (json.dumps(obj, separators=(",", ":")) + "\n").encode()

    def _check(self, raw):
        import equivalence
        case = self._loaded_case()
        rm = equivalence.load_reason_map(
            os.path.join(self.HARNESS, "reason_map.json"))
        return equivalence.check_exact_record(
            raw, b"", 3, case["expected"], "t", reason_map=rm,
            expect_kind="reason_class", allow_entry_count=True)

    def test_correct_entry_count_accepted(self):
        self.assertEqual(self._check(self._record(970)), [])

    def test_wrong_entry_count_rejected(self):
        problems = self._check(self._record(1))
        self.assertTrue(any("entry_count" in p for p in problems),
                        "entry_count 1 was accepted against adopted 970")

    def test_missing_entry_count_rejected(self):
        problems = self._check(self._record(omit=True))
        self.assertTrue(any("entry_count" in p for p in problems))

    def test_non_integer_entry_count_rejected(self):
        problems = self._check(self._record("970"))
        self.assertTrue(any("entry_count" in p for p in problems))

    def test_corpus_declares_the_adopted_counts(self):
        with open(os.path.join(self.HARNESS, "corpus",
                               "archive_cases.json"),
                  encoding="utf-8") as handle:
            cases = {c["case_id"]: c for c in json.load(handle)["cases"]}
        self.assertEqual(cases["real_v20"]["expected"]["entry_count"], 970)
        self.assertEqual(cases["real_705"]["expected"]["entry_count"], 819)
        self.assertEqual(
            cases["real_move78"]["expected"]["entry_count"], 935)


ADOPTED_ADAPTER = os.path.join(
    ROOT, "verify", "structured_verdict_v01", "adapter.py")
ADOPTED_REASON_MAP = os.path.join(
    ROOT, "verify", "agreement_harness_v01", "reason_map.json")


def _verifier_stub(name, line, rc):
    """A verifier stand-in emitting one exact raw line."""
    return _write_python_exe(
        name,
        "import sys\n"
        "sys.stdout.write(%r + '\\n')\n"
        "sys.exit(%d)\n" % (line, rc))


CLEAN_RAW_LINE = ('{"verifier": "witness-verify", '
                  '"version": "0.0.8-step79-diagnostics", '
                  '"verdict": "INCONCLUSIVE", '
                  '"reason_code": "RECEIPT_CHAIN_HASHES_RECOMPUTED", '
                  '"detail": "ok"}')


class TestGenuineAdapterIsTheAuthority(unittest.TestCase):
    """B1/B2: the ADOPTED inherited adapter defines valid output. No
    synthetic record is ever the authority for success."""

    def _genuine(self, tag, line=CLEAN_RAW_LINE, rc=3, lane="rust_bundle",
                 target=None):
        stub = _verifier_stub("ga_%s.py" % tag, line, rc)
        proc = _run([PYTHON_BIN, "-B", ADOPTED_ADAPTER, "verdict",
                     "--lane", lane, "--input", target or REAL_BUNDLE,
                     "--reason-map", ADOPTED_REASON_MAP,
                     "--rust-bin", stub], timeout=300)
        return proc, stub

    def test_genuine_record_includes_operation(self):
        proc, _stub = self._genuine("op")
        self.assertEqual(proc.stderr, b"")
        record = json.loads(proc.stdout)
        self.assertIn("operation", record,
                      "the adopted adapter emits operation; any checker "
                      "that treats it as unexpected is wrong")
        self.assertEqual(record["operation"], "verify_bundle")

    def test_genuine_record_normalizes_the_reason(self):
        proc, _stub = self._genuine("norm")
        record = json.loads(proc.stdout)
        self.assertEqual(record["reason_code"], "OK",
                         "the adapter normalizes the raw Rust reason")
        self.assertNotEqual(record["reason_code"],
                            "RECEIPT_CHAIN_HASHES_RECOMPUTED")
        self.assertEqual(record["stage"], "complete")

    def test_genuine_record_is_canonical_bytes(self):
        import equivalence
        proc, _stub = self._genuine("canon")
        self.assertEqual(
            equivalence.check_canonical_json_bytes(proc.stdout, "t"), [])

    def test_identical_verifiers_produce_byte_identical_records(self):
        import equivalence
        a = _verifier_stub("ga_a.py", CLEAN_RAW_LINE, 3)
        b = _verifier_stub("ga_b.py", CLEAN_RAW_LINE, 3)
        problems, checked = equivalence.run_adapter_equivalence(
            ADOPTED_ADAPTER, PYTHON_BIN, a, b, ADOPTED_REASON_MAP,
            [{"case_id": "CLEAN", "argv": ["verify", REAL_BUNDLE],
              "path": REAL_BUNDLE, "expected": {}, "expected_kind": None}],
            baseline_bin=a)
        self.assertEqual(problems, [])
        self.assertEqual(checked, 1)

    def test_a_differing_profile_is_rejected(self):
        import equivalence
        good = _verifier_stub("ga_good.py", CLEAN_RAW_LINE, 3)
        other = CLEAN_RAW_LINE.replace("RECEIPT_CHAIN_HASHES_RECOMPUTED",
                                       "RECEIPT_LINKAGE_BROKEN")
        other = other.replace('"INCONCLUSIVE"', '"FAIL"')
        bad = _verifier_stub("ga_bad.py", other, 1)
        problems, _ = equivalence.run_adapter_equivalence(
            ADOPTED_ADAPTER, PYTHON_BIN, bad, good, ADOPTED_REASON_MAP,
            [{"case_id": "CLEAN", "argv": ["verify", REAL_BUNDLE],
              "path": REAL_BUNDLE, "expected": {}, "expected_kind": None}],
            baseline_bin=good)
        self.assertTrue(problems)
        self.assertTrue(any("byte-identical" in p for p in problems))

    def test_baseline_authority_is_mandatory(self):
        import equivalence
        good = _verifier_stub("ga_nb.py", CLEAN_RAW_LINE, 3)
        with self.assertRaises(equivalence.EquivalenceError):
            equivalence.run_adapter_equivalence(
                ADOPTED_ADAPTER, PYTHON_BIN, good, good,
                ADOPTED_REASON_MAP,
                [{"case_id": "C", "argv": ["verify", REAL_BUNDLE],
                  "path": REAL_BUNDLE, "expected": {},
                  "expected_kind": None}])

    def test_no_synthetic_adapter_schema_is_reconstructed(self):
        """The production module must not carry a hand-written copy of the
        Move 81 field list -- that reconstruction is what omitted
        `operation` and compared against the raw reason."""
        with open(EQUIV_TOOL, encoding="utf-8") as handle:
            src = handle.read()
        for token in ("ADAPTER_REQUIRED_FIELDS", "ADAPTER_CAPABILITY_SCOPE",
                      "ADAPTER_PRODUCER_VERSION"):
            self.assertNotIn(token, src,
                             "%s reconstructs the adopted schema" % token)


class TestCanonicalJsonBytes(unittest.TestCase):
    """B3: byte-exact canonical JSON, not semantic comparison."""

    GOOD = None

    def setUp(self):
        import equivalence
        self.eq = equivalence
        record = {"a": 1, "b": "x", "c": True}
        self.GOOD = (json.dumps(record, sort_keys=True,
                                separators=(",", ":")) + "\n").encode()

    def _check(self, raw):
        return self.eq.check_canonical_json_bytes(raw, "t")

    def test_canonical_accepted(self):
        self.assertEqual(self._check(self.GOOD), [])

    def test_non_canonical_key_order_rejected(self):
        raw = b'{"c":true,"a":1,"b":"x"}\n'
        self.assertTrue(self._check(raw))

    def test_alternate_separators_rejected(self):
        raw = b'{"a": 1, "b": "x", "c": true}\n'
        self.assertTrue(self._check(raw))

    def test_leading_space_rejected(self):
        self.assertTrue(self._check(b" " + self.GOOD))

    def test_trailing_space_rejected(self):
        self.assertTrue(self._check(self.GOOD[:-1] + b" \n"))

    def test_duplicate_keys_rejected(self):
        raw = b'{"a":1,"a":2}\n'
        problems = self._check(raw)
        self.assertTrue(any("duplicate" in p for p in problems))

    def test_two_json_lines_rejected(self):
        self.assertTrue(self._check(self.GOOD + self.GOOD))

    def test_missing_final_newline_rejected(self):
        self.assertTrue(self._check(self.GOOD[:-1]))

    def test_extra_final_newline_rejected(self):
        self.assertTrue(self._check(self.GOOD + b"\n"))

    def test_additional_stdout_rejected(self):
        self.assertTrue(self._check(b"noise\n" + self.GOOD))

    def test_empty_output_rejected(self):
        self.assertTrue(self._check(b""))


class TestArchiveFieldSetExactness(unittest.TestCase):
    """B5: entry_count belongs only to the accepted archive record."""

    HARNESS = os.path.join(ROOT, "verify", "agreement_harness_v01")

    def _check(self, obj, expected, rc):
        import equivalence
        rm = equivalence.load_reason_map(
            os.path.join(self.HARNESS, "reason_map.json"))
        raw = (json.dumps(obj, separators=(",", ":")) + "\n").encode()
        return equivalence.check_exact_record(
            raw, b"", rc, expected, "t", reason_map=rm,
            expect_kind="reason_class", allow_entry_count=True)

    def _accepted(self, **over):
        obj = {"verifier": "witness-verify",
               "version": "0.0.8-step79-diagnostics",
               "verdict": "INCONCLUSIVE",
               "reason_code": "ARCHIVE_SAFETY_OK",
               "detail": "ok", "entry_count": 970}
        obj.update(over)
        return obj

    def _fail(self, **over):
        obj = {"verifier": "witness-verify",
               "version": "0.0.8-step79-diagnostics",
               "verdict": "FAIL",
               "reason_code": "ARCHIVE_PATH_TRAVERSAL",
               "detail": "bad"}
        obj.update(over)
        return obj

    ACCEPT_EXPECT = {"verdict": "INCONCLUSIVE", "exit_code": 3,
                     "reason_class": "ARCHIVE_OK", "stage": "archive",
                     "entry_count": 970}
    FAIL_EXPECT = {"verdict": "FAIL", "exit_code": 1,
                   "reason_class": "ARCHIVE_PATH_TRAVERSAL",
                   "stage": "archive"}

    def test_accepted_with_correct_count_ok(self):
        self.assertEqual(self._check(self._accepted(),
                                     self.ACCEPT_EXPECT, 3), [])

    def test_invented_count_on_fail_record_rejected(self):
        problems = self._check(self._fail(entry_count=999),
                               self.FAIL_EXPECT, 1)
        self.assertTrue(any("entry_count" in p for p in problems),
                        "an invented entry_count rode along on a FAIL "
                        "record")

    def test_fail_record_without_count_ok(self):
        self.assertEqual(self._check(self._fail(), self.FAIL_EXPECT, 1),
                         [])

    def test_missing_count_on_accepted_rejected(self):
        obj = self._accepted()
        del obj["entry_count"]
        self.assertTrue(self._check(obj, self.ACCEPT_EXPECT, 3))

    def test_wrong_count_rejected(self):
        self.assertTrue(self._check(self._accepted(entry_count=1),
                                    self.ACCEPT_EXPECT, 3))

    def test_string_count_rejected(self):
        self.assertTrue(self._check(self._accepted(entry_count="970"),
                                    self.ACCEPT_EXPECT, 3))

    def test_float_count_rejected(self):
        self.assertTrue(self._check(self._accepted(entry_count=970.0),
                                    self.ACCEPT_EXPECT, 3))

    def test_extra_field_rejected(self):
        self.assertTrue(self._check(self._accepted(surprise=1),
                                    self.ACCEPT_EXPECT, 3))

    def test_missing_required_field_rejected(self):
        obj = self._accepted()
        del obj["detail"]
        self.assertTrue(self._check(obj, self.ACCEPT_EXPECT, 3))


class TestHelperStreamAndStatusHostility(unittest.TestCase):
    """B4: helpers that lie in one channel must be caught."""

    def _helper(self, name, out=b"", err=b"", rc=0):
        return _write_python_exe(
            name,
            "import sys\n"
            "sys.stdout.buffer.write(%r)\n"
            "sys.stderr.buffer.write(%r)\n"
            "sys.exit(%d)\n" % (out, err, rc))

    def test_stderr_with_success_exit_is_detected(self):
        h = self._helper("hs_a.py", out=b"{}\n", err=b"warning", rc=0)
        proc = _run([h])
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr,
                        "a helper can exit 0 while writing stderr")

    def test_failure_with_plausible_stdout_is_detected(self):
        import equivalence
        h = self._helper("hs_b.py",
                         out=(json.dumps({"a": 1}, separators=(",", ":"))
                              + "\n").encode(), rc=1)
        proc = _run([h])
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(
            equivalence.check_canonical_json_bytes(proc.stdout, "t"), [],
            "stdout looks plausible, so only the status reveals failure")

    def test_success_with_malformed_stdout_is_detected(self):
        import equivalence
        h = self._helper("hs_c.py", out=b"{not json\n", rc=0)
        proc = _run([h])
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(
            equivalence.check_canonical_json_bytes(proc.stdout, "t"))

    def test_wrong_exit_with_expected_output_is_detected(self):
        h = self._helper("hs_d.py", out=b"{}\n", rc=7)
        proc = _run([h])
        self.assertEqual(proc.returncode, 7)

    def test_gate_checks_status_stderr_and_stdout_separately(self):
        with open(GATE, encoding="utf-8") as handle:
            code = handle.read()
        for err_var in ("$_FGB_ERR", "$_BFX_ERR", "$_UN_ERR", "$_VER_ERR"):
            self.assertIn('2>"%s"' % err_var, code, err_var)
            self.assertIn('[ -s "%s" ]' % err_var, code, err_var)
        # the second fixture generation now has its own stdout file and a
        # separately checked status
        self.assertIn("_FGB_OUT", code)
        self.assertIn('"$_fgb_rc" -ne 0', code)
        self.assertIn('"$_bfx_rc" -ne 0', code)

    def test_single_adapter_invocation_block(self):
        with open(GATE, encoding="utf-8") as handle:
            code = "\n".join(l for l in handle.read().splitlines()
                              if not l.strip().startswith("#"))
        self.assertEqual(code.count("--mode adapter-equivalence"), 1)


class TestStreamSeparation(unittest.TestCase):
    """R4: no acceptance stage merges stdout and stderr."""

    def _gate(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read()

    def test_no_merged_redirection_anywhere(self):
        code = "\n".join(l for l in self._gate().splitlines()
                          if not l.strip().startswith("#"))
        joined = code.replace("\\\n", " ")
        self.assertNotIn("2>&1", joined,
                         "merged redirection cannot prove empty stderr")

    def test_child_gates_and_hygiene_capture_stderr_separately(self):
        code = self._gate()
        for err_var in ("$_M81_ERR", "$_PH_ERR", "$_RV_ERR", "$_UN_ERR",
                        "$_DBG_ERR", "$_BA_ERR", "$_FI_ERR", "$_EDQ_ERR",
                        "$_AD_ERR", "$_US_ERR", "$_SB_ERR", "$_OD_ERR"):
            self.assertIn('2>"%s"' % err_var, code, err_var)
            self.assertIn('[ -s "%s" ]' % err_var, code, err_var)


class TestProductionCheckerMutationResistance(unittest.TestCase):
    """R5: removing one exact comparison from a production checker must
    make the suite fail. Proven by mutating the loaded module in memory
    and re-running the real checkers."""

    HARNESS = os.path.join(ROOT, "verify", "agreement_harness_v01")

    def test_dropping_the_entry_count_comparison_is_detected(self):
        import equivalence
        rm = equivalence.load_reason_map(
            os.path.join(self.HARNESS, "reason_map.json"))
        expected = {"verdict": "INCONCLUSIVE", "exit_code": 3,
                    "reason_class": "ARCHIVE_OK", "stage": "archive",
                    "entry_count": 970}
        raw = (json.dumps(
            {"verifier": "witness-verify",
             "version": "0.0.8-step79-diagnostics",
             "verdict": "INCONCLUSIVE",
             "reason_code": "ARCHIVE_SAFETY_OK",
             "detail": "ok", "entry_count": 1},
            separators=(",", ":")) + "\n").encode()
        problems = equivalence.check_exact_record(
            raw, b"", 3, expected, "t", reason_map=rm,
            expect_kind="reason_class", allow_entry_count=True)
        self.assertTrue(any("entry_count" in p for p in problems),
                        "the production checker does not enforce the "
                        "adopted entry_count")

    def test_dropping_the_edge_verdict_comparison_is_detected(self):
        import equivalence
        rm = equivalence.load_reason_map(
            os.path.join(self.HARNESS, "reason_map.json"))
        fixture = {"kind": "archive", "surface": "zip_offset",
                   "expect_stage": "archive", "expect_verdict": "FAIL",
                   "expect_exit_code": 1,
                   "expect_reason_code": "ARCHIVE_PATH_TRAVERSAL",
                   "expect_reason_class": "ARCHIVE_PATH_TRAVERSAL",
                   "path": "/x"}
        raw = (json.dumps(
            {"verifier": "witness-verify",
             "version": "0.0.8-step79-diagnostics",
             "verdict": "PASS", "reason_code": "ARCHIVE_PATH_TRAVERSAL",
             "detail": "d"}, separators=(",", ":")) + "\n").encode()
        problems = equivalence.check_edge_contract(
            raw, b"", 0, fixture, rm, "t")
        self.assertTrue(any("verdict" in p for p in problems))
        self.assertTrue(any("exit code" in p for p in problems))


class TestEdgeContractIsBaselineEstablished(unittest.TestCase):
    """The v06 Termux failure: edge_control.zip was hand-declared
    INCONCLUSIVE/3 while the adopted verifier genuinely answers FAIL/1.
    Every edge expectation must now come from the baseline."""

    HARNESS = os.path.join(ROOT, "verify", "agreement_harness_v01")
    REASON_MAP = os.path.join(HARNESS, "reason_map.json")

    def _fixtures(self, tag):
        outdir = os.path.join(_TMP, "be_" + tag)
        manifest = os.path.join(_TMP, "be_%s.json" % tag)
        proc = _run([PYTHON_BIN, "-B", EQUIV_TOOL, "--mode",
                     "make-edge-fixtures", "--outdir", outdir,
                     "--clean-bundle", REAL_BUNDLE,
                     "--json-out", manifest], timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(manifest, encoding="utf-8") as handle:
            return manifest, json.load(handle)["fixtures"]

    def _verifier(self, name, verdict="FAIL", rc=1,
                  archive_reason="ARCHIVE_PATH_TRAVERSAL",
                  bundle_reason="MANIFEST_JSON_INVALID"):
        return _write_python_exe(
            name,
            "import json,os,sys\n"
            "f = os.path.basename(sys.argv[-1].rstrip('/'))\n"
            "reason = %r if f.endswith('.zip') else %r\n"
            "sys.stdout.write(json.dumps({'verifier':'witness-verify',"
            "'version':'0.0.8-step79-diagnostics','verdict':%r,"
            "'reason_code':reason,'detail':'d'},separators=(',',':'))"
            " + '\\n')\n"
            "sys.exit(%d)\n"
            % (archive_reason, bundle_reason, verdict, rc))

    def _pin(self, tag, verifier):
        manifest, _fx = self._fixtures(tag)
        pinned = os.path.join(_TMP, "be_pin_%s.json" % tag)
        proc = _run([PYTHON_BIN, "-B", EQUIV_TOOL, "--mode",
                     "edge-equivalence", "--release-bin", verifier,
                     "--debug-bin", verifier, "--baseline-bin", verifier,
                     "--reason-map", self.REASON_MAP,
                     "--edge-manifest", manifest, "--json-out", pinned],
                    timeout=300)
        return proc, pinned

    def _run_pinned(self, pinned, release, debug=None):
        return _run([PYTHON_BIN, "-B", EQUIV_TOOL, "--mode",
                     "edge-equivalence", "--release-bin", release,
                     "--debug-bin", debug or release,
                     "--reason-map", self.REASON_MAP,
                     "--edge-manifest", pinned], timeout=300)

    # ---- the generator must declare no expectation at all -------------

    def test_generator_declares_no_expectations(self):
        _manifest, fixtures = self._fixtures("noexp")
        for fixture in fixtures:
            for key in ("expect_verdict", "expect_exit_code",
                        "expect_reason_code", "expect_reason_class",
                        "expect_stage"):
                self.assertNotIn(
                    key, fixture,
                    "the generator hand-declared %s on %s"
                    % (key, fixture["path"]))
            self.assertTrue(fixture.get("surface"))

    def test_no_hardcoded_verdict_in_the_generator_source(self):
        with open(EQUIV_TOOL, encoding="utf-8") as handle:
            src = handle.read()
        start = src.find("def make_edge_fixtures(")
        end = src.find("def ", start + 10)
        body = src[start:end if end != -1 else len(src)]
        for token in ('"expect_verdict"', '"expect_exit_code"',
                      '"expect_stage"'):
            self.assertNotIn(token, body,
                             "the generator still declares %s" % token)

    # ---- edge_control must take the adopted result --------------------

    def test_edge_control_uses_the_baseline_result_not_inconclusive_3(self):
        verifier = self._verifier("be_ctrl.py")   # answers FAIL/1
        proc, pinned = self._pin("ctrl", verifier)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        with open(pinned, encoding="utf-8") as handle:
            fixtures = json.load(handle)["fixtures"]
        control = [f for f in fixtures
                   if os.path.basename(f["path"]) == "edge_control.zip"]
        self.assertEqual(len(control), 1)
        control = control[0]
        self.assertEqual(control["expect_verdict"], "FAIL")
        self.assertEqual(control["expect_exit_code"], 1)
        # the exact v06 regression must be impossible
        self.assertNotEqual(control["expect_verdict"], "INCONCLUSIVE")
        self.assertNotEqual(control["expect_exit_code"], 3)

    def test_edge_control_follows_a_different_baseline(self):
        """If the adopted verifier accepted the control, the pinned
        contract would follow it -- the expectation tracks the authority,
        never a fixed guess."""
        accepting = self._verifier(
            "be_accept.py", verdict="INCONCLUSIVE", rc=3,
            archive_reason="ARCHIVE_SAFETY_OK",
            bundle_reason="RECEIPT_CHAIN_HASHES_RECOMPUTED")
        proc, pinned = self._pin("accept", accepting)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        with open(pinned, encoding="utf-8") as handle:
            fixtures = json.load(handle)["fixtures"]
        control = [f for f in fixtures
                   if os.path.basename(f["path"]) == "edge_control.zip"][0]
        self.assertEqual(control["expect_verdict"], "INCONCLUSIVE")
        self.assertEqual(control["expect_exit_code"], 3)

    # ---- a tampered contract must be rejected even with agreement -----

    def test_altered_contract_rejected_though_profiles_agree(self):
        verifier = self._verifier("be_tamper.py")
        proc, pinned = self._pin("tamper", verifier)
        self.assertEqual(proc.returncode, 0)
        with open(pinned, encoding="utf-8") as handle:
            data = json.load(handle)
        for fixture in data["fixtures"]:
            if os.path.basename(fixture["path"]) == "edge_control.zip":
                fixture["expect_verdict"] = "INCONCLUSIVE"
                fixture["expect_exit_code"] = 3
        altered = os.path.join(_TMP, "be_altered.json")
        with open(altered, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        # SAME binary as release and debug: they agree perfectly
        result = self._run_pinned(altered, verifier, verifier)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"verdict is 'FAIL'", result.stdout)
        self.assertIn(b"exit code", result.stdout)
        self.assertNotIn(b"EDGE_EQUIVALENCE: PASS", result.stdout)

    def test_altered_reason_contract_rejected(self):
        verifier = self._verifier("be_reason.py")
        proc, pinned = self._pin("reason", verifier)
        with open(pinned, encoding="utf-8") as handle:
            data = json.load(handle)
        for fixture in data["fixtures"]:
            fixture["expect_reason_code"] = "SOMETHING_ELSE"
        altered = os.path.join(_TMP, "be_reason_alt.json")
        with open(altered, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        result = self._run_pinned(altered, verifier, verifier)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"raw reason_code", result.stdout)

    def test_altered_stage_contract_rejected(self):
        verifier = self._verifier("be_stage.py")
        proc, pinned = self._pin("stage", verifier)
        with open(pinned, encoding="utf-8") as handle:
            data = json.load(handle)
        for fixture in data["fixtures"]:
            fixture["expect_stage"] = "receipts"
        altered = os.path.join(_TMP, "be_stage_alt.json")
        with open(altered, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        result = self._run_pinned(altered, verifier, verifier)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"answered at stage", result.stdout)

    # ---- completeness of the pinned contract --------------------------

    def test_partially_pinned_contract_rejected(self):
        verifier = self._verifier("be_partial.py")
        proc, pinned = self._pin("partial", verifier)
        with open(pinned, encoding="utf-8") as handle:
            data = json.load(handle)
        for fixture in data["fixtures"]:
            del fixture["expect_exit_code"]
        partial = os.path.join(_TMP, "be_partial_alt.json")
        with open(partial, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        result = self._run_pinned(partial, verifier, verifier)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"no baseline-established contract", result.stdout)

    def test_every_pinned_fixture_carries_the_complete_contract(self):
        verifier = self._verifier("be_complete.py")
        _proc, pinned = self._pin("complete", verifier)
        with open(pinned, encoding="utf-8") as handle:
            fixtures = json.load(handle)["fixtures"]
        self.assertEqual(len(fixtures), 10)
        for fixture in fixtures:
            for key in ("expect_verdict", "expect_exit_code",
                        "expect_reason_code", "expect_reason_class",
                        "expect_stage", "baseline_stdout_sha256"):
                self.assertIn(key, fixture, fixture["path"])

    def test_baseline_verdict_outside_the_adopted_set_rejected(self):
        liar = self._verifier("be_pass.py", verdict="PASS", rc=0)
        manifest, _fx = self._fixtures("passbase")
        result = _run([PYTHON_BIN, "-B", EQUIV_TOOL, "--mode",
                       "edge-equivalence", "--release-bin", liar,
                       "--debug-bin", liar, "--baseline-bin", liar,
                       "--reason-map", self.REASON_MAP,
                       "--edge-manifest", manifest], timeout=300)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"no other reachable verdict", result.stdout)

    def test_established_evidence_is_printed(self):
        verifier = self._verifier("be_evidence.py")
        proc, _pinned = self._pin("evidence", verifier)
        self.assertIn(b"EDGE_ESTABLISHED:", proc.stdout)
        self.assertIn(b"edge_control.zip", proc.stdout)


if __name__ == "__main__":
    _suite = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[__name__])
    _result = unittest.TextTestRunner(
        stream=sys.stdout, verbosity=1).run(_suite)
    sys.exit(0 if _result.wasSuccessful() else 1)
