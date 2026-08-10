"""Python ZipGuard TEST ORACLE — Move 79 agreement harness.

*** THIS IS A TEST ORACLE, NOT A SECOND TRUSTED VERIFIER. ***

Purpose: provide an INDEPENDENT implementation of the adopted Move 78 v10
archive-safety contract so that the Rust ZipGuard can be cross-checked
behaviourally. It exists only to disagree with Rust when one of them is
wrong. It is never imported by Companion or any production path; deleting
this file changes no runtime behaviour.

Independence discipline (per the Move 79 boundaries):
  - written from the Move 78 CONTRACT (zipguard.rs module docstring /
    README taxonomy), not by mechanically translating Rust functions
  - deliberately different internal structure: a single ordered pass over
    parsed entry records, rather than the Rust layering, so that a shared
    structural bug is less likely to be replicated
  - read-only: never extracts, executes, writes, or modifies an archive

Agreement between this oracle and Rust is NOT proof of correctness — both
could share an error. Every corpus case therefore also carries an
independently declared expected result, and the harness compares all three.
"""

import re
import struct

# ---- contract constants (from the adopted Move 78 v10 contract) ----

SUPPORTED_FLAG_MASK = 0x0800 | 0x0001   # UTF-8 name bit, encryption bit
TAG_ZIP64 = 0x0001
TAG_UNICODE_PATH = 0x7075
TAG_UT = 0x5455                          # Extended Timestamp
TAG_UX = 0x7875                          # Info-ZIP Unix UID/GID
CREATOR_UNIX = 3
DOS_RESERVED = {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)) | {
    0x200E, 0x200F, 0x061C}


class Reject(Exception):
    def __init__(self, code, detail=""):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def _u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def _parse_extra(blob, is_local, malformed_code):
    """Strict allowlist parse. Returns dict with ut_flags/ut_mtime/uid/gid."""
    info = {"ut_flags": None, "ut_mtime": None, "uid": None, "gid": None}
    seen = []
    p = 0
    while p < len(blob):
        if p + 4 > len(blob):
            raise Reject(malformed_code, "truncated extra-field header")
        tag = _u16(blob, p)
        size = _u16(blob, p + 2)
        if p + 4 + size > len(blob):
            raise Reject(malformed_code,
                         "extra record %#06x overruns blob" % tag)
        if tag in seen:
            raise Reject(malformed_code, "duplicate extra tag %#06x" % tag)
        seen.append(tag)
        payload = blob[p + 4:p + 4 + size]

        if tag == TAG_ZIP64:
            raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                         "zip64 extended information")
        if tag == TAG_UNICODE_PATH:
            raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                         "Unicode Path extra field")
        if tag == TAG_UT:
            if not payload:
                raise Reject(malformed_code, "empty Extended Timestamp")
            flags = payload[0]
            if flags & ~0x07:
                raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                             "unsupported UT flag bits %#04x" % flags)
            if not flags & 0x01:
                raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                             "Extended Timestamp without mtime")
            extra_times = 0
            if is_local:
                extra_times = ((flags >> 1) & 1) + ((flags >> 2) & 1)
            want = 1 + 4 + 4 * extra_times
            if size != want:
                raise Reject(malformed_code,
                             "Extended Timestamp length %d != %d"
                             % (size, want))
            info["ut_flags"] = flags
            info["ut_mtime"] = struct.unpack_from("<i", payload, 1)[0]
        elif tag == TAG_UX:
            if len(payload) < 3:
                raise Reject(malformed_code, "Unix UID/GID too short")
            if payload[0] != 1:
                raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                             "Unix UID/GID version %d" % payload[0])
            uidsz = payload[1]
            if uidsz == 0 or uidsz > 8 or len(payload) < 2 + uidsz + 1:
                raise Reject(malformed_code, "malformed Unix UID length")
            uid = int.from_bytes(payload[2:2 + uidsz], "little")
            gidsz = payload[2 + uidsz]
            if gidsz == 0 or gidsz > 8 or len(payload) != 3 + uidsz + gidsz:
                raise Reject(malformed_code, "malformed Unix GID length")
            gid = int.from_bytes(payload[3 + uidsz:3 + uidsz + gidsz],
                                 "little")
            info["uid"] = uid
            info["gid"] = gid
        else:
            raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                         "unknown extra-field tag %#06x" % tag)
        p += 4 + size
    return info


def _check_name(name):
    """Name-safety rules in the adopted PRECEDENCE order (most specific
    first): UNC -> absolute -> backslash -> drive -> '.'/'..' components
    -> Windows-hostile -> non-ASCII."""
    for ch in name:
        o = ord(ch)
        if o < 0x20 or o == 0x7F:
            raise Reject("ARCHIVE_CONTROL_CHARACTER",
                         "control char U+%04X" % o)
    for ch in name:
        if ord(ch) in BIDI:
            raise Reject("ARCHIVE_BIDI_CHARACTER",
                         "bidi control U+%04X" % ord(ch))
    if name.startswith("\\\\") or name.startswith("//"):
        raise Reject("ARCHIVE_UNC_PATH", name)
    if name.startswith("/"):
        raise Reject("ARCHIVE_ABSOLUTE_PATH", name)
    if "\\" in name:
        raise Reject("ARCHIVE_BACKSLASH_PATH", name)
    if len(name) >= 2 and name[1] == ":" and name[0].isascii() \
            and name[0].isalpha():
        raise Reject("ARCHIVE_WINDOWS_DRIVE_PATH", name)
    for comp in name.rstrip("/").split("/"):
        if comp in ("..", "."):
            raise Reject("ARCHIVE_PATH_TRAVERSAL",
                         "%r component in %r" % (comp, name))
    for comp in name.rstrip("/").split("/"):
        if ":" in comp:
            raise Reject("ARCHIVE_ALTERNATE_DATA_STREAM", comp)
        if comp.endswith(".") or comp.endswith(" "):
            raise Reject("ARCHIVE_WINDOWS_NAME_UNSAFE",
                         "trailing dot/space: %r" % comp)
        stem = comp.split(".")[0].upper()
        if stem in DOS_RESERVED:
            raise Reject("ARCHIVE_WINDOWS_NAME_UNSAFE",
                         "reserved device name: %r" % comp)
        if len(stem) == 4 and stem[:3] in ("COM", "LPT") \
                and stem[3] in "123456789":
            raise Reject("ARCHIVE_WINDOWS_NAME_UNSAFE",
                         "reserved device name: %r" % comp)
    if not name.isascii():
        raise Reject("ARCHIVE_UNICODE_NAME_UNSAFE",
                     "non-ASCII filename %r" % name)


def _components(name):
    """Structural path validation: no empty components, no '.'/'..'."""
    is_dir = name.endswith("/")
    core = name[:-1] if is_dir else name
    if core == "":
        raise Reject("ARCHIVE_MALFORMED", "empty filename")
    comps = core.split("/")
    for c in comps:
        if c == "":
            raise Reject("ARCHIVE_PATH_TRAVERSAL",
                         "empty path component in %r" % name)
    return comps, is_dir


def inspect_archive(path):
    """Read-only. Returns dict(verdict, reason_code, entries, cd_offset,
    cd_size, local_entries, extra_tags). Never extracts or writes."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError as err:
        return _fail("ARCHIVE_IO_ERROR", str(err))

    try:
        return _inspect(data)
    except Reject as rej:
        return {"verdict": "FAIL", "reason_code": rej.code,
                "detail": rej.detail, "entries": None, "cd_offset": None,
                "cd_size": None, "local_entries": None, "extra_tags": None}


def _fail(code, detail):
    return {"verdict": "FAIL", "reason_code": code, "detail": detail,
            "entries": None, "cd_offset": None, "cd_size": None,
            "local_entries": None, "extra_tags": None}


def _find_eocd(data):
    if len(data) < 22:
        raise Reject("ARCHIVE_MALFORMED", "file smaller than EOCD")
    start = len(data) - 22
    limit = max(0, len(data) - 22 - 0xFFFF)
    i = start
    while i >= limit:
        if data[i:i + 4] == b"PK\x05\x06":
            return i
        i -= 1
    raise Reject("ARCHIVE_MALFORMED", "no EOCD record")


def _inspect(data):
    eocd = _find_eocd(data)
    if eocd >= 20 and data[eocd - 20:eocd - 16] == b"PK\x06\x07":
        raise Reject("ARCHIVE_UNSUPPORTED_FEATURE", "zip64 EOCD locator")

    disk_no = _u16(data, eocd + 4)
    cd_disk = _u16(data, eocd + 6)
    this_entries = _u16(data, eocd + 8)
    total = _u16(data, eocd + 10)
    cd_size = _u32(data, eocd + 12)
    cd_offset = _u32(data, eocd + 16)
    comment_len = _u16(data, eocd + 20)

    if disk_no != 0 or cd_disk != 0:
        raise Reject("ARCHIVE_UNSUPPORTED_FEATURE", "multi-disk archive")
    if this_entries != total:
        raise Reject("ARCHIVE_UNSUPPORTED_FEATURE", "multi-disk archive")
    if cd_offset == 0xFFFFFFFF or cd_size == 0xFFFFFFFF or total == 0xFFFF:
        raise Reject("ARCHIVE_UNSUPPORTED_FEATURE", "zip64 sentinel values")
    if eocd + 22 + comment_len != len(data):
        raise Reject("ARCHIVE_MALFORMED",
                     "EOCD comment length does not reach end of file")
    if cd_offset + cd_size > len(data):
        raise Reject("ARCHIVE_MALFORMED", "central directory past EOF")
    if cd_offset + cd_size > eocd:
        raise Reject("ARCHIVE_MALFORMED",
                     "central directory overlaps EOCD")

    entries = []
    p = cd_offset
    end = cd_offset + cd_size
    for _ in range(total):
        if p + 46 > end:
            raise Reject("ARCHIVE_MALFORMED",
                         "central header truncated")
        if data[p:p + 4] != b"PK\x01\x02":
            raise Reject("ARCHIVE_MALFORMED",
                         "bad central header signature")
        rec = {
            "version_made_by": _u16(data, p + 4),
            "version_needed": _u16(data, p + 6),
            "flags": _u16(data, p + 8),
            "method": _u16(data, p + 10),
            "crc": _u32(data, p + 16),
            "csize": _u32(data, p + 20),
            "usize": _u32(data, p + 24),
            "disk_start": _u16(data, p + 34),
            "ext_attr": _u32(data, p + 38),
            "lho": _u32(data, p + 42),
        }
        nlen = _u16(data, p + 28)
        elen = _u16(data, p + 30)
        clen = _u16(data, p + 32)
        name_end = p + 46 + nlen
        extra_end = name_end + elen
        if name_end > end or extra_end > end:
            raise Reject("ARCHIVE_MALFORMED",
                         "central name/extra past directory")
        rec["name_raw"] = data[p + 46:name_end]
        rec["extra"] = _parse_extra(data[name_end:extra_end], False,
                                    "ARCHIVE_MALFORMED")
        entries.append(rec)
        p = extra_end + clen

    if p != end:
        raise Reject("ARCHIVE_MALFORMED",
                     "central entries consumed %d bytes, declared %d"
                     % (p - cd_offset, cd_size))
    if end != eocd:
        raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                     "unparsed data between central directory and EOCD")
    if not entries:
        raise Reject("ARCHIVE_MALFORMED", "no entries")

    ranges = []
    seen_lho = set()
    exact = set()
    ci_seen = {}
    file_pfx = set()
    dir_pfx = set()
    tags = set()

    for rec in entries:
        if rec["lho"] in seen_lho:
            raise Reject("ARCHIVE_LOCAL_HEADER_OFFSET_INVALID",
                         "duplicate local-header offset %d" % rec["lho"])
        seen_lho.add(rec["lho"])

        # CHECK ORDER (corrected in Move 79 v3 after the harness exposed a
        # divergence): the adopted Move 78 contract checks entry-level
        # UNSUPPORTED FEATURES first — encryption, compression method,
        # version-needed, disk-start — and only then validates the local
        # header. The oracle previously validated the local header first,
        # so an archive with central-encrypted / local-clear flags reported
        # LOCAL_HEADER_MISMATCH instead of UNSUPPORTED_FEATURE. The oracle
        # was wrong about the contract; corrected here.
        if rec["disk_start"] != 0:
            raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                         "entry disk-start not zero")
        if rec["flags"] & 0x0001:
            raise Reject("ARCHIVE_UNSUPPORTED_FEATURE", "encrypted entry")
        if rec["method"] not in (0, 8):
            raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                         "compression method %d" % rec["method"])
        if rec["version_needed"] > 45:
            raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                         "version-needed %d" % rec["version_needed"])

        r_start, r_end = _check_local(data, rec, cd_offset)
        ranges.append((r_start, r_end))

        if rec["flags"] & ~SUPPORTED_FLAG_MASK:
            raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                         "unsupported flag bits %#06x"
                         % (rec["flags"] & ~SUPPORTED_FLAG_MASK))

        raw = rec["name_raw"]
        if all(b < 0x80 for b in raw):
            name = raw.decode("ascii")
        elif rec["flags"] & 0x0800:
            try:
                name = raw.decode("utf-8")
            except UnicodeDecodeError:
                raise Reject("ARCHIVE_UNICODE_NAME_UNSAFE",
                             "UTF-8 flag set but bytes invalid")
        else:
            raise Reject("ARCHIVE_UNICODE_NAME_UNSAFE",
                         "non-ASCII name without UTF-8 flag")

        _check_name(name)
        comps, is_dir = _components(name)

        host = rec["version_made_by"] >> 8
        if host != CREATOR_UNIX:
            raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                         "creator host system %d" % host)
        mode = (rec["ext_attr"] >> 16) & 0xF000
        if mode == 0:
            raise Reject("ARCHIVE_SPECIAL_FILE_TYPE",
                         "ambiguous zero Unix file type")
        if mode == 0xA000:
            raise Reject("ARCHIVE_SYMLINK_ENTRY", name)
        if mode == 0x8000:
            if is_dir:
                raise Reject("ARCHIVE_FILE_DIRECTORY_COLLISION",
                             "trailing-slash name with regular-file mode")
        elif mode == 0x4000:
            if not is_dir:
                raise Reject("ARCHIVE_FILE_DIRECTORY_COLLISION",
                             "directory mode without trailing slash")
            if rec["csize"] or rec["usize"] or rec["crc"]:
                raise Reject("ARCHIVE_MALFORMED",
                             "directory entry carries data")
        else:
            raise Reject("ARCHIVE_SPECIAL_FILE_TYPE",
                         "unix file type %#06x" % mode)

        if name in exact:
            raise Reject("ARCHIVE_DUPLICATE_NAME", name)
        exact.add(name)

        lc = [c.lower() for c in comps]
        base_lc = "/".join(lc)
        for depth in range(1, len(lc)):
            pfx = "/".join(lc[:depth])
            if pfx in file_pfx:
                raise Reject("ARCHIVE_FILE_DIRECTORY_COLLISION",
                             "%r is a file used as a directory prefix" % pfx)
            dir_pfx.add(pfx)
        if is_dir:
            if base_lc in file_pfx:
                raise Reject("ARCHIVE_FILE_DIRECTORY_COLLISION", base_lc)
            dir_pfx.add(base_lc)
        else:
            if base_lc in dir_pfx:
                raise Reject("ARCHIVE_FILE_DIRECTORY_COLLISION", base_lc)
            file_pfx.add(base_lc)

        if base_lc in ci_seen:
            if ci_seen[base_lc] != name:
                raise Reject("ARCHIVE_CASE_COLLISION",
                             "%r vs %r" % (ci_seen[base_lc], name))
            raise Reject("ARCHIVE_NORMALIZED_NAME_COLLISION", name)
        ci_seen[base_lc] = name

        if rec["extra"]["ut_flags"] is not None:
            tags.add(TAG_UT)
        if rec["extra"]["uid"] is not None:
            tags.add(TAG_UX)

    ranges.sort()
    cursor = 0
    for start, stop in ranges:
        if start < cursor:
            raise Reject("ARCHIVE_LOCAL_LAYOUT_INVALID",
                         "range [%d,%d) overlaps data ending at %d"
                         % (start, stop, cursor))
        if start > cursor:
            raise Reject("ARCHIVE_UNREFERENCED_DATA",
                         "%d unreferenced byte(s) at offset %d"
                         % (start - cursor, cursor))
        cursor = stop
    if cursor != cd_offset:
        raise Reject("ARCHIVE_UNREFERENCED_DATA",
                     "%d unreferenced byte(s) before central directory"
                     % (cd_offset - cursor))

    return {
        "verdict": "INCONCLUSIVE",
        "reason_code": "ARCHIVE_SAFETY_OK",
        "detail": "archive passed Move 78 safety checks",
        "entries": len(entries),
        "cd_offset": cd_offset,
        "cd_size": cd_size,
        "local_entries": len(ranges),
        "extra_tags": sorted(tags),
    }


def _check_local(data, rec, cd_offset):
    off = rec["lho"]
    if off + 30 > cd_offset:
        raise Reject("ARCHIVE_LOCAL_HEADER_OFFSET_INVALID",
                     "local header offset %d outside archive body" % off)
    if data[off:off + 4] != b"PK\x03\x04":
        raise Reject("ARCHIVE_LOCAL_HEADER_MALFORMED",
                     "bad local header signature at %d" % off)
    l_version = _u16(data, off + 4)
    l_flags = _u16(data, off + 6)
    l_method = _u16(data, off + 8)
    l_crc = _u32(data, off + 14)
    l_csize = _u32(data, off + 18)
    l_usize = _u32(data, off + 22)
    l_nlen = _u16(data, off + 26)
    l_elen = _u16(data, off + 28)

    name_start = off + 30
    name_end = name_start + l_nlen
    extra_end = name_end + l_elen
    if name_end > cd_offset or extra_end > cd_offset:
        raise Reject("ARCHIVE_LOCAL_HEADER_MALFORMED",
                     "local name/extra runs into central directory")
    if data[name_start:name_end] != rec["name_raw"]:
        raise Reject("ARCHIVE_LOCAL_HEADER_MISMATCH",
                     "local filename differs from central")
    if l_flags != rec["flags"]:
        raise Reject("ARCHIVE_LOCAL_HEADER_MISMATCH",
                     "local flags %#06x != central %#06x"
                     % (l_flags, rec["flags"]))
    if l_method != rec["method"]:
        raise Reject("ARCHIVE_LOCAL_HEADER_MISMATCH",
                     "local/central method disagree")
    if l_version != rec["version_needed"]:
        raise Reject("ARCHIVE_LOCAL_HEADER_MISMATCH",
                     "local version-needed %d != central %d"
                     % (l_version, rec["version_needed"]))
    if l_version > 45:
        raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                     "local version-needed %d" % l_version)
    if l_flags & 0x0008:
        raise Reject("ARCHIVE_UNSUPPORTED_FEATURE",
                     "data-descriptor flag (bit 3)")
    if l_crc != rec["crc"]:
        raise Reject("ARCHIVE_LOCAL_HEADER_MISMATCH", "CRC-32 disagree")
    if l_csize != rec["csize"]:
        raise Reject("ARCHIVE_LOCAL_HEADER_MISMATCH",
                     "compressed size disagree")
    if l_usize != rec["usize"]:
        raise Reject("ARCHIVE_LOCAL_HEADER_MISMATCH",
                     "uncompressed size disagree")

    local_extra = _parse_extra(data[name_end:extra_end], True,
                               "ARCHIVE_LOCAL_HEADER_MALFORMED")
    if local_extra["ut_flags"] != rec["extra"]["ut_flags"]:
        raise Reject("ARCHIVE_LOCAL_HEADER_MISMATCH",
                     "Extended Timestamp flags disagree")
    if local_extra["ut_mtime"] != rec["extra"]["ut_mtime"]:
        raise Reject("ARCHIVE_LOCAL_HEADER_MISMATCH",
                     "Extended Timestamp mtime disagree")
    if local_extra["uid"] != rec["extra"]["uid"] \
            or local_extra["gid"] != rec["extra"]["gid"]:
        raise Reject("ARCHIVE_LOCAL_HEADER_MISMATCH",
                     "Unix UID/GID disagree")

    range_end = extra_end + rec["csize"]
    if range_end > cd_offset:
        raise Reject("ARCHIVE_MALFORMED",
                     "entry data ends at %d past central directory %d"
                     % (range_end, cd_offset))
    return off, range_end
