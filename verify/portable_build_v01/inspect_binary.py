#!/usr/bin/env python3
"""Move 82 binary inspector.

Parses the produced executable ITSELF and reports what it actually is.
Nothing here shells out: there is no dependence on PATH-resolved `file`,
`readelf`, `objdump` or `ldd`. Android/Termux compatibility is never
inferred from a filename or from the Cargo command that produced the
file -- only from bytes in the binary's own headers.

For ELF the inspector reports: class, endianness, e_type, e_machine
architecture, PT_INTERP (when present) and DT_NEEDED entries (when
present, deterministically sorted).

Every structural problem fails closed with a deterministic message; no
traceback and no raw exception escapes.
"""

import argparse
import json
import os
import struct
import sys


ELF_MAGIC = b"\x7fELF"

ELF_CLASS = {1: "ELF32", 2: "ELF64"}
ELF_DATA = {1: "little", 2: "big"}
ELF_TYPE = {1: "REL", 2: "EXEC", 3: "DYN", 4: "CORE"}
# Only the machines this project can honestly speak about are named; any
# other value is reported numerically rather than guessed at.
ELF_MACHINE = {
    0x03: "x86",
    0x28: "arm",
    0x3E: "x86_64",
    0xB7: "aarch64",
}

PT_DYNAMIC = 2
PT_INTERP = 3
PT_LOAD = 1

# The ONLY target candidate v02 is authorised for.
AUTHORISED_ARCHITECTURE = "aarch64"
AUTHORISED_FORMAT = "ELF64"
AUTHORISED_ENDIANNESS = "little"
AUTHORISED_TRIPLE = "aarch64-linux-android"
# Platform machine strings that genuinely denote AArch64.
# armv8l denotes a 32-bit ARM userland on an ARMv8 core, NOT AArch64, so
# it is deliberately NOT accepted.
AUTHORISED_PLATFORM_MACHINES = ("aarch64", "arm64")
# Genuine Android/Bionic dynamic linker identities. A glibc loader such as
# /lib64/ld-linux-aarch64.so.1 is proof the binary is NOT an Android
# target, however AArch64 its header looks.
ANDROID_INTERPRETERS = (
    "/system/bin/linker64",
    "/data/data/com.termux/files/usr/lib/ld-android.so",
)
# No suffix acceptance: an arbitrary path such as /evil/custom/linker64
# must never be treated as a genuine Android linker.
ANDROID_INTERPRETER_SUFFIXES = ()
# Bionic system dependencies a Termux-built binary may legitimately carry.
ANDROID_ALLOWED_NEEDED = ("libc.so", "libdl.so", "libm.so", "liblog.so",
                          "libandroid.so", "libc++_shared.so")
# glibc markers: their presence disproves an Android claim.
GLIBC_MARKERS = ("libc.so.6", "libm.so.6", "libdl.so.2", "libpthread.so.0",
                 "ld-linux", "libgcc_s.so.1")
# The Termux/Android Rust toolchain produces position-independent
# executables, so DYN is the type the native build genuinely establishes.
# EXEC is accepted only when explicitly permitted, and REL/CORE/unknown are
# rejected outright rather than described numerically and accepted.
ACCEPTED_ELF_TYPES = ("DYN",)
ACCEPTED_ELF_TYPES_RELAXED = ("DYN", "EXEC")

DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10


class InspectError(Exception):
    """Deterministic, message-only inspection failure."""


def _u(data, offset, size, endian):
    """Unsigned integer of `size` bytes at `offset`."""
    if offset < 0 or offset + size > len(data):
        raise InspectError("truncated: read beyond end of file")
    fmt = {1: "B", 2: "H", 4: "I", 8: "Q"}[size]
    prefix = "<" if endian == "little" else ">"
    return struct.unpack_from(prefix + fmt, data, offset)[0]


def _cstr(data, offset):
    if offset < 0 or offset >= len(data):
        raise InspectError("truncated: string offset beyond end of file")
    end = data.find(b"\x00", offset)
    if end == -1:
        raise InspectError("unterminated string in binary")
    try:
        return data[offset:end].decode("utf-8")
    except UnicodeDecodeError:
        raise InspectError("non-UTF-8 string in binary")


def inspect_elf(data):
    """Parse an ELF image. Returns a dict of established facts."""
    if len(data) < 64:
        raise InspectError("file is too small to be an ELF image")
    if data[:4] != ELF_MAGIC:
        raise InspectError("not an ELF image (bad magic)")

    ei_class = data[4]
    ei_data = data[5]
    if ei_class not in ELF_CLASS:
        raise InspectError("unsupported ELF class: %d" % ei_class)
    if ei_data not in ELF_DATA:
        raise InspectError("unsupported ELF endianness: %d" % ei_data)
    elf_class = ELF_CLASS[ei_class]
    endian = ELF_DATA[ei_data]
    if elf_class != "ELF64":
        raise InspectError(
            "unsupported ELF class for this project: %s" % elf_class)

    e_type = _u(data, 16, 2, endian)
    e_machine = _u(data, 18, 2, endian)
    e_phoff = _u(data, 32, 8, endian)
    e_phentsize = _u(data, 54, 2, endian)
    e_phnum = _u(data, 56, 2, endian)

    if e_phentsize != 56:
        raise InspectError(
            "unexpected ELF64 program-header size: %d" % e_phentsize)

    interp = None
    dynamic_off = None
    dynamic_size = None
    loads = []
    for index in range(e_phnum):
        base = e_phoff + index * e_phentsize
        p_type = _u(data, base, 4, endian)
        p_offset = _u(data, base + 8, 8, endian)
        p_vaddr = _u(data, base + 16, 8, endian)
        p_filesz = _u(data, base + 32, 8, endian)
        if p_type == PT_INTERP:
            if p_filesz == 0:
                raise InspectError("malformed PT_INTERP: zero length")
            if p_offset + p_filesz > len(data):
                raise InspectError("malformed PT_INTERP: extends beyond file")
            raw = data[p_offset:p_offset + p_filesz]
            if b"\x00" not in raw:
                raise InspectError("malformed PT_INTERP: unterminated")
            try:
                interp = raw.split(b"\x00", 1)[0].decode("utf-8")
            except UnicodeDecodeError:
                raise InspectError("malformed PT_INTERP: non-UTF-8")
            if interp == "":
                raise InspectError("malformed PT_INTERP: empty interpreter")
        elif p_type == PT_DYNAMIC:
            dynamic_off = p_offset
            dynamic_size = p_filesz
        elif p_type == PT_LOAD:
            loads.append((p_vaddr, p_offset, p_filesz))

    elf_type = ELF_TYPE.get(e_type, "UNKNOWN(%d)" % e_type)
    if elf_type not in ACCEPTED_ELF_TYPES_RELAXED:
        raise InspectError(
            "unsupported ELF type for an executable: %s" % elf_type)

    needed = _read_needed(data, endian, dynamic_off, dynamic_size, loads)

    return {
        "executable_format": elf_class,
        "endianness": endian,
        "elf_type": elf_type,
        "architecture": ELF_MACHINE.get(e_machine,
                                        "UNKNOWN(0x%02x)" % e_machine),
        "interpreter": interp,
        "runtime_dependencies": needed,
    }


def _vaddr_to_offset(vaddr, loads):
    for seg_vaddr, seg_offset, seg_filesz in loads:
        if seg_vaddr <= vaddr < seg_vaddr + seg_filesz:
            return seg_offset + (vaddr - seg_vaddr)
    return None


def _read_needed(data, endian, dynamic_off, dynamic_size, loads):
    """DT_NEEDED entries, deterministically sorted. Empty list when the
    image has no dynamic section (a fully static binary).

    Every name is read strictly INSIDE the declared dynamic string table.
    Without that bound a malformed DT_NEEDED offset would walk off the end
    of the string table and return unrelated file bytes as a dependency
    name, which is exactly the kind of confident-but-wrong evidence this
    inspector exists to prevent."""
    if dynamic_off is None or not dynamic_size:
        return []
    strtab_vaddr = None
    strtab_size = None
    needed_offsets = []
    entry = 0
    saw_null = False
    while True:
        base = dynamic_off + entry * 16
        if base + 16 > dynamic_off + dynamic_size:
            break
        if base + 16 > len(data):
            raise InspectError("malformed dynamic section: truncated")
        d_tag = _u(data, base, 8, endian)
        d_val = _u(data, base + 8, 8, endian)
        if d_tag == DT_NULL:
            saw_null = True
            break
        if d_tag == DT_NEEDED:
            needed_offsets.append(d_val)
        elif d_tag == DT_STRTAB:
            strtab_vaddr = d_val
        elif d_tag == DT_STRSZ:
            strtab_size = d_val
        entry += 1
    if not saw_null:
        raise InspectError(
            "malformed dynamic section: no DT_NULL terminator")
    if not needed_offsets:
        return []
    if strtab_vaddr is None:
        raise InspectError("malformed dynamic section: DT_NEEDED without "
                           "DT_STRTAB")
    strtab_off = _vaddr_to_offset(strtab_vaddr, loads)
    if strtab_off is None:
        raise InspectError("malformed dynamic section: DT_STRTAB address "
                           "is not inside any loadable segment")
    # Determine the string table's real extent. DT_STRSZ is authoritative
    # when present; otherwise fall back to the end of the containing
    # loadable segment, never the end of the file.
    if strtab_size is not None:
        if strtab_size == 0:
            raise InspectError("malformed dynamic section: DT_STRSZ is 0")
        strtab_end = strtab_off + strtab_size
    else:
        strtab_end = _segment_end_for_offset(strtab_off, loads)
        if strtab_end is None:
            raise InspectError(
                "malformed dynamic section: string table extent unknown")
    if strtab_end > len(data):
        raise InspectError(
            "malformed dynamic section: string table extends beyond file")
    names = []
    for rel in needed_offsets:
        start = strtab_off + rel
        if start < strtab_off or start >= strtab_end:
            raise InspectError(
                "malformed DT_NEEDED: name offset outside the string table")
        end = data.find(b"\x00", start, strtab_end)
        if end == -1:
            raise InspectError(
                "malformed DT_NEEDED: unterminated name in string table")
        try:
            name = data[start:end].decode("utf-8")
        except UnicodeDecodeError:
            raise InspectError("malformed DT_NEEDED: non-UTF-8 name")
        if name == "":
            raise InspectError("malformed DT_NEEDED: empty name")
        names.append(name)
    return sorted(set(names))


def _segment_end_for_offset(offset, loads):
    for _seg_vaddr, seg_offset, seg_filesz in loads:
        if seg_offset <= offset < seg_offset + seg_filesz:
            return seg_offset + seg_filesz
    return None


def inspect_path(path):
    if not os.path.isabs(path):
        raise InspectError("binary path must be absolute")
    if not os.path.isfile(path):
        raise InspectError("binary path is not a regular file")
    with open(path, "rb") as handle:
        data = handle.read()
    facts = inspect_elf(data)
    facts["binary_size_bytes"] = len(data)
    return facts


def cross_check(facts, rustc_host=None, platform_machine=None,
                require_authorised_target=True):
    """Cross-check the binary's own header against the toolchain host
    triple and the actual platform architecture. Returns a list of
    disagreements; empty means consistent.

    With require_authorised_target the ONLY accepted combination is the
    target candidate v02 is authorised for: aarch64 / ELF64 / little-endian
    / aarch64-linux-android. An x86 Android build must never be accepted
    and then reported under an AArch64 adoption marker."""
    problems = []
    arch = facts.get("architecture")
    fmt = facts.get("executable_format")
    endian = facts.get("endianness")

    if require_authorised_target:
        if arch != AUTHORISED_ARCHITECTURE:
            problems.append(
                "binary architecture %s is not the authorised %s"
                % (arch, AUTHORISED_ARCHITECTURE))
        if fmt != AUTHORISED_FORMAT:
            problems.append(
                "executable format %s is not the authorised %s"
                % (fmt, AUTHORISED_FORMAT))
        if endian != AUTHORISED_ENDIANNESS:
            problems.append(
                "endianness %s is not the authorised %s"
                % (endian, AUTHORISED_ENDIANNESS))
        if rustc_host is not None and rustc_host != AUTHORISED_TRIPLE:
            problems.append(
                "rustc host triple %s is not the authorised %s"
                % (rustc_host, AUTHORISED_TRIPLE))
        if platform_machine is not None \
                and platform_machine not in AUTHORISED_PLATFORM_MACHINES:
            problems.append(
                "platform machine %s is not an accepted AArch64 value"
                % platform_machine)

    if require_authorised_target:
        if facts.get("elf_type") not in ACCEPTED_ELF_TYPES:
            problems.append(
                "ELF type %s is not the type the native Termux release "
                "build establishes (%s)"
                % (facts.get("elf_type"), "/".join(ACCEPTED_ELF_TYPES)))
        interp = facts.get("interpreter")
        if interp is not None:
            if any(marker in interp for marker in GLIBC_MARKERS):
                problems.append(
                    "interpreter %s is a glibc loader; this is not an "
                    "Android/Termux binary" % interp)
            elif interp not in ANDROID_INTERPRETERS:
                problems.append(
                    "interpreter %s is not a recognised Android/Termux "
                    "linker" % interp)
        for dep in facts.get("runtime_dependencies") or []:
            if any(marker in dep for marker in GLIBC_MARKERS):
                problems.append(
                    "runtime dependency %s is a glibc library; this is not "
                    "an Android/Bionic binary" % dep)
            elif dep not in ANDROID_ALLOWED_NEEDED:
                problems.append(
                    "unexpected runtime dependency for an Android/Bionic "
                    "binary: %s" % dep)

    if rustc_host:
        host_arch = rustc_host.split("-", 1)[0]
        if host_arch != arch:
            problems.append(
                "binary architecture %s does not match rustc host %s"
                % (arch, rustc_host))
    if platform_machine:
        normalised = ("aarch64"
                      if platform_machine in AUTHORISED_PLATFORM_MACHINES
                      else platform_machine)
        if normalised != arch:
            problems.append(
                "binary architecture %s does not match platform machine %s"
                % (arch, platform_machine))
    if str(arch).startswith("UNKNOWN"):
        problems.append("unrecognised machine architecture: %s" % arch)
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Move 82 binary inspector")
    parser.add_argument("--binary", required=True)
    parser.add_argument("--json-out", required=True,
                        help="absolute path receiving ONLY the canonical "
                             "JSON object; the human marker stays on stdout")
    parser.add_argument("--rustc-host", default=None)
    parser.add_argument("--platform-machine", default=None)
    parser.add_argument("--allow-any-target", action="store_true",
                        help="test-only: relax the authorised-target rule. "
                             "The gate never passes this.")
    args = parser.parse_args(argv)

    if not os.path.isabs(args.json_out):
        print("usage error: --json-out must be an absolute path")
        return 2

    try:
        facts = inspect_path(args.binary)
    except InspectError as exc:
        print("BINARY_INSPECT: FAIL (%s)" % exc)
        return 1

    problems = cross_check(
        facts,
        rustc_host=args.rustc_host,
        platform_machine=args.platform_machine,
        require_authorised_target=not args.allow_any_target)
    if problems:
        for problem in sorted(problems):
            print("BINARY_INSPECT_MISMATCH: %s" % problem)
        print("BINARY_INSPECT: FAIL (%d disagreement(s))" % len(problems))
        return 1

    # The JSON file contains EXACTLY one canonical object and exactly one
    # trailing newline, so the gate can json.load() it without ambiguity.
    # The human-readable marker never shares that stream.
    raw = (json.dumps(facts, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False) + "\n").encode("utf-8")
    with open(args.json_out, "wb") as handle:
        handle.write(raw)
    print("BINARY_INSPECT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
