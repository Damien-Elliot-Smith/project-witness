"""Deterministic synthetic adversarial archive generator (Move 79).

Builds one small ZIP per named attack class, each exercising a specific
neighbouring reason-code distinction from the adopted Move 78 v10 contract.
Deterministic: same inputs -> byte-identical archives every run.

Each generated case name maps to an independently declared expected result
in corpus/archive_cases.json. The generator does NOT decide expectations;
it only produces bytes. This keeps expectation provenance separate from the
implementations under test.
"""

import os
import struct

MTIME = 1783018176
ATIME = 1783018930
F_MODE = 0o100644
D_MODE = 0o040755


def _ut_central():
    return struct.pack("<HHB", 0x5455, 5, 0x03) + struct.pack("<i", MTIME)


def _ut_local():
    return (struct.pack("<HHB", 0x5455, 9, 0x03)
            + struct.pack("<ii", MTIME, ATIME))


def _ux():
    return (struct.pack("<HH", 0x7875, 11) + bytes([1, 4])
            + struct.pack("<I", 0) + bytes([4]) + struct.pack("<I", 0))


def _real_central_extra():
    return _ut_central() + _ux()


def _real_local_extra():
    return _ut_local() + _ux()


class Builder:
    """Assembles a ZIP from explicit entry specs. Each spec is a dict with
    keys: cname, lname, mode, method, flags, made_by, cextra, lextra,
    crc, csize, usize. Missing keys take safe real-archive defaults."""

    def __init__(self):
        self.buf = bytearray()
        self.central = []

    def add(self, **spec):
        cname = spec["cname"]
        lname = spec.get("lname", cname)
        flags = spec.get("flags", 0)
        method = spec.get("method", 0)
        made_by = spec.get("made_by", 0x031E)
        cextra = spec.get("cextra", _real_central_extra())
        lextra = spec.get("lextra", _real_local_extra())
        mode = spec.get("mode", F_MODE)
        crc = spec.get("crc", 0)
        csize = spec.get("csize", 0)
        usize = spec.get("usize", 0)

        lho = len(self.buf)
        self.buf += struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, flags,
                                method, 0, 0, crc, csize, usize,
                                len(lname), len(lextra))
        self.buf += lname
        self.buf += lextra
        self.central.append((cname, lname, flags, method, made_by, cextra,
                             mode, crc, csize, usize, lho))

    def build(self):
        cd_start = len(self.buf)
        for (cname, _l, flags, method, made_by, cextra, mode,
             crc, csize, usize, lho) in self.central:
            self.buf += struct.pack(
                "<IHHHHHHIIIHHHHHII", 0x02014B50, made_by, 20, flags,
                method, 0, 0, crc, csize, usize, len(cname), len(cextra),
                0, 0, 0, (mode & 0xFFFF) << 16, lho)
            self.buf += cname
            self.buf += cextra
        cd_size = len(self.buf) - cd_start
        n = len(self.central)
        self.buf += struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, n, n,
                                cd_size, cd_start, 0)
        return bytes(self.buf)


def _clean():
    b = Builder()
    b.add(cname=b"a.txt")
    b.add(cname=b"dir/", mode=D_MODE)
    b.add(cname=b"dir/b.txt")
    return b.build()


def _one(cname, **kw):
    b = Builder()
    b.add(cname=cname, **kw)
    return b.build()


def _patch(bytes_in, offset, value_bytes):
    b = bytearray(bytes_in)
    b[offset:offset + len(value_bytes)] = value_bytes
    return bytes(b)


def _find_cd(data):
    return data.find(b"PK\x01\x02")


def _find_eocd(data):
    return data.rfind(b"PK\x05\x06")


# Each builder returns raw ZIP bytes. Names match archive_cases.json.

def _layout_overlapping_ranges():
    """Two entries whose local ranges overlap because entry 0 declares a
    compressed size that runs into entry 1's local header. Central and
    local sizes agree (so the header check passes); the OVERLAP is caught
    by the layout tiling rule -> ARCHIVE_LOCAL_LAYOUT_INVALID."""
    b = Builder()
    b.add(cname=b"a.txt", csize=60, usize=60)
    b.add(cname=b"b.txt")
    return b.build()


def _layout_interior_gap():
    """A structurally valid archive with an unreferenced gap between two
    entries: entry 1's local header is pushed forward, leaving bytes no
    central entry accounts for -> ARCHIVE_UNREFERENCED_DATA."""
    b = Builder()
    b.add(cname=b"a.txt")
    b.add(cname=b"b.txt")
    data = bytearray(b.build())
    # find entry 1's local header, insert 8 filler bytes before it, and
    # bump entry 1's central local-offset and the CD/EOCD offsets by 8.
    import struct as _s
    lfh2 = data.find(b"PK\x03\x04", 4)
    cd = data.find(b"PK\x01\x02")
    eocd = data.rfind(b"PK\x05\x06")
    # entry 1 is the second central header
    cd2 = data.find(b"PK\x01\x02", cd + 4)
    gap = b"\x00" * 8
    new = bytearray(data[:lfh2]) + gap + bytearray(data[lfh2:])
    # shift cd offset in EOCD (+8) and central dir moved (+8) and entry-1
    # local offset (+8)
    neocd = new.rfind(b"PK\x05\x06")
    cd_off = _s.unpack_from("<I", new, neocd + 16)[0] + 8
    _s.pack_into("<I", new, neocd + 16, cd_off)
    ncd2 = new.find(b"PK\x01\x02", new.find(b"PK\x01\x02") + 4)
    lho2 = _s.unpack_from("<I", new, ncd2 + 42)[0] + 8
    _s.pack_into("<I", new, ncd2 + 42, lho2)
    return bytes(new)


def _layout_orphan_local_header():
    """A valid archive plus an extra, unreferenced local header (with a
    benign name) before the central directory. No central entry points at
    it, so its bytes are unreferenced -> ARCHIVE_UNREFERENCED_DATA."""
    import struct as _s
    b = Builder()
    b.add(cname=b"a.txt")
    data = bytearray(b.build())
    cd = data.find(b"PK\x01\x02")
    orphan = _s.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0, 0, 0, 0, 0, 0, 0,
                     5, 0) + b"c.txt"
    new = bytearray(data[:cd]) + orphan + bytearray(data[cd:])
    neocd = new.rfind(b"PK\x05\x06")
    cd_off = _s.unpack_from("<I", new, neocd + 16)[0] + len(orphan)
    _s.pack_into("<I", new, neocd + 16, cd_off)
    return bytes(new)


def _layout_data_into_cd():
    """Entry declares a compressed size so large its data range runs past
    the central directory -> ARCHIVE_MALFORMED (entry data past CD)."""
    b = Builder()
    b.add(cname=b"a.txt", csize=0xF000, usize=0xF000)
    return b.build()




def _layout_valid_sfx_prefix():
    """SFX prefix with ALL offsets repaired: prepend bytes, then bump every
    central local-header offset and the EOCD cd_offset by the prefix length.
    The archive stays structurally parseable, so the prefix bytes are simply
    UNREFERENCED -> ARCHIVE_UNREFERENCED_DATA (not MALFORMED)."""
    import struct as _s
    b = Builder()
    b.add(cname=b"a.txt")
    data = bytearray(b.build())
    prefix = b"MZ" + b"\x00" * 30          # 32-byte plausible stub
    n = len(prefix)
    new = bytearray(prefix) + data
    eocd = new.rfind(b"PK\x05\x06")
    cd_off = _s.unpack_from("<I", new, eocd + 16)[0] + n
    _s.pack_into("<I", new, eocd + 16, cd_off)
    # bump each central entry's local-header offset
    p = cd_off
    total = _s.unpack_from("<H", new, eocd + 10)[0]
    for _ in range(total):
        lho = _s.unpack_from("<I", new, p + 42)[0] + n
        _s.pack_into("<I", new, p + 42, lho)
        nlen = _s.unpack_from("<H", new, p + 28)[0]
        elen = _s.unpack_from("<H", new, p + 30)[0]
        clen = _s.unpack_from("<H", new, p + 32)[0]
        p += 46 + nlen + elen + clen
    return bytes(new)


def _layout_cd_eocd_gap():
    """Insert bytes between the end of the central directory and the EOCD,
    leaving cd_offset/cd_size intact. The CD no longer ends exactly at the
    EOCD -> the adopted rule rejects the unparsed region."""
    b = Builder()
    b.add(cname=b"a.txt")
    data = bytearray(b.build())
    eocd = data.rfind(b"PK\x05\x06")
    new = bytearray(data[:eocd]) + b"\x00" * 8 + bytearray(data[eocd:])
    return bytes(new)


def _compete_version_vs_local():
    """COMPETING: central version-needed unsupported (99) AND the local
    version differs (20). The adopted order checks entry-level UNSUPPORTED
    FEATURES (including version-needed > 45) BEFORE validating the local
    header, so ARCHIVE_UNSUPPORTED_FEATURE wins over the local mismatch.
    (My initial prediction was the opposite; the observed contract order
    corrected it.)"""
    import struct as _s
    b = Builder()
    b.add(cname=b"a.txt")
    d = bytearray(b.build())
    cd = d.find(b"PK\x01\x02")
    _s.pack_into("<H", d, cd + 6, 99)     # central version-needed 99
    return bytes(d)                        # local stays 20 -> mismatch


def _data_descriptor_both_set():
    """Central AND local both set flag bit 3. Flags AGREE, so this is not a
    mismatch: it is an unsupported feature -> ARCHIVE_UNSUPPORTED_FEATURE."""
    b = Builder()
    b.add(cname=b"a.txt", flags=0x0008)
    return b.build()


def build_all():
    out = {}
    out["clean"] = _clean()
    out["traversal"] = _one(b"../evil")
    out["nested_traversal"] = _one(b"a/b/../../../evil")
    out["dot_component"] = _one(b"a/./b")
    out["trailing_dot_windows"] = _one(b"file.")
    out["absolute_unix"] = _one(b"/etc/passwd")
    out["unc_path"] = _one(b"//server/share")
    out["windows_drive"] = _one(b"C:data")
    out["backslash"] = _one(b"a\\b")
    out["reserved_con"] = _one(b"CON")
    out["reserved_com1"] = _one(b"COM1.log")
    out["ads_colon"] = _one(b"file.txt:stream")
    out["control_char"] = _one(b"a\x01b")
    out["non_ascii"] = _one("\u00e9.txt".encode("utf-8"), flags=0x0800)

    # exact duplicate
    b = Builder(); b.add(cname=b"same.txt"); b.add(cname=b"same.txt")
    out["duplicate_name"] = b.build()
    # case collision
    b = Builder(); b.add(cname=b"File.txt"); b.add(cname=b"file.txt")
    out["case_collision"] = b.build()
    # file then dir prefix
    b = Builder(); b.add(cname=b"a"); b.add(cname=b"a/b")
    out["prefix_collision"] = b.build()
    # ancestor: a/b then file a
    b = Builder(); b.add(cname=b"a/b"); b.add(cname=b"a")
    out["ancestor_prefix_collision"] = b.build()

    out["symlink"] = _one(b"link", mode=0o120777)
    out["fifo"] = _one(b"pipe", mode=0o010644)
    out["chardev"] = _one(b"dev", mode=0o020644)
    out["zero_ftype"] = _one(b"a.txt", mode=0)
    out["dir_no_slash"] = _one(b"x", mode=D_MODE)
    out["slash_file_mode"] = _one(b"x/", mode=F_MODE)

    # CRC mismatch: patch local CRC (offset 14 of first LFH)
    out["crc_mismatch"] = _patch(_one(b"a.txt"), 14, b"\xAA")
    # compressed size mismatch (offset 18)
    out["csize_mismatch"] = _patch(_one(b"a.txt"), 18, b"\x05")
    # local name mismatch
    out["local_name_mismatch"] = _one(b"safe.txt", lname=b"../x.txt")
    # local flags mismatch (central 0, local 0x0008 data descriptor bit)
    out["local_flags_mismatch"] = _one(b"a.txt", flags=0)  # patched below
    dd = _one(b"a.txt")
    dd = _patch(dd, 6, struct.pack("<H", 0x0008))  # local flags bit 3
    out["local_flags_mismatch"] = dd

    # unsupported: encrypted
    out["encrypted"] = _one(b"a.txt", flags=0x0001)
    # unsupported compression
    out["bad_method"] = _one(b"a.txt", method=99)
    # non-Unix creator
    out["dos_creator"] = _patch(_one(b"a.txt"), _find_cd(_one(b"a.txt")) + 5,
                                b"\x00")
    # unknown extra tag (central)
    unk = struct.pack("<HH", 0x1234, 2) + b"\x00\x00"
    out["unknown_extra"] = _one(b"a.txt", cextra=_ut_central() + _ux() + unk,
                                lextra=_real_local_extra())
    # malformed extra length
    badx = struct.pack("<HH", 0x5455, 200)
    out["malformed_extra"] = _one(b"a.txt", cextra=badx,
                                  lextra=_real_local_extra())
    # UT mtime disagreement
    ce = struct.pack("<HHB", 0x5455, 5, 0x03) + struct.pack("<i", 111) + _ux()
    le = struct.pack("<HHB", 0x5455, 9, 0x03) + struct.pack("<ii", 222, 333) \
        + _ux()
    out["ut_mtime_disagree"] = _one(b"a.txt", cextra=ce, lextra=le)

    # malformed EOCD comment length
    base = _one(b"a.txt")
    out["eocd_comment_mismatch"] = _patch(base, _find_eocd(base) + 20,
                                          b"\x05")
    # nonzero disk-start
    out["nonzero_disk_start"] = _patch(_one(b"a.txt"),
                                       _find_cd(_one(b"a.txt")) + 34, b"\x01")
    # not a zip
    out["not_a_zip"] = b"this is not a zip file at all"

    # invalid local offset (point central lho past CD)
    base = _one(b"a.txt")
    out["bad_local_offset"] = _patch(base, _find_cd(base) + 42,
                                     b"\xF0\xFF\x00\x00")

    # prepended SFX stub (breaks the offsets)
    base = _one(b"a.txt")
    out["sfx_stub"] = b"MZ\x90\x00" + base


    # ---- Move 79 v2: additional adopted-contract + precedence cases ----
    out["repeated_separator"] = _one(b"a//b")
    out["bidi_control"] = _one("a\u202Eb.txt".encode("utf-8"), flags=0x0800)

    # duplicate extra tag (UT twice)
    dup = _ut_central() + _ut_central() + _ux()
    out["duplicate_extra_tag"] = _one(b"a.txt", cextra=dup,
                                      lextra=_real_local_extra())
    # Unicode Path extra
    up = struct.pack("<HH", 0x7075, 5) + bytes([1, 0, 0, 0, 0])
    out["unicode_path_extra"] = _one(b"a.txt",
                                     cextra=_ut_central() + _ux() + up,
                                     lextra=_real_local_extra())
    # ZIP64 extra tag
    z64 = struct.pack("<HH", 0x0001, 0)
    out["zip64_extra"] = _one(b"a.txt", cextra=_ut_central() + _ux() + z64,
                              lextra=_real_local_extra())
    # unknown LOCAL extra
    unk = struct.pack("<HH", 0x4242, 2) + b"\x00\x00"
    out["unknown_local_extra"] = _one(
        b"a.txt", lextra=_real_local_extra() + unk)
    # malformed LOCAL extra
    badl = struct.pack("<HH", 0x5455, 250)
    out["malformed_local_extra"] = _one(b"a.txt", lextra=badl)
    # UT flags disagreement (same mtime, different flags)
    ce = struct.pack("<HHB", 0x5455, 5, 0x01) + struct.pack("<i", MTIME) + _ux()
    out["ut_flags_disagree"] = _one(b"a.txt", cextra=ce,
                                    lextra=_real_local_extra())
    # malformed UID/GID (uid size 9 > 8)
    badux = struct.pack("<HH", 0x7875, 3) + bytes([1, 9, 0])
    out["malformed_uid_gid"] = _one(b"a.txt",
                                    cextra=_ut_central() + badux,
                                    lextra=_real_local_extra())
    # uncompressed-size mismatch (local usize at offset 22)
    out["usize_mismatch"] = _patch(_one(b"a.txt"), 22, b"\x07")
    # local version mismatch (local version-needed at offset 4)
    out["local_version_mismatch"] = _patch(_one(b"a.txt"), 4, b"\x2d")
    # directory carrying data
    d = _one(b"dir/", mode=D_MODE)
    d = _patch(d, 18, b"\x05")                       # local csize
    d = _patch(d, _find_cd(d) + 20, b"\x05")         # central csize
    out["directory_with_data"] = d

    # ---- COMPETING-DEFECT cases: two rules could fire; precedence decides
    # 1. "../CON" : traversal AND a reserved Windows name. The adopted
    #    precedence puts '..'/'.' components BEFORE Windows-hostile names,
    #    so PATH_TRAVERSAL must win.
    out["compete_traversal_vs_windows"] = _one(b"../CON")
    # 2. "//server/../x" : UNC AND traversal. UNC is checked first.
    out["compete_unc_vs_traversal"] = _one(b"//server/../x")
    # 3. "/etc/./passwd" : absolute AND a '.' component. Absolute is
    #    checked before component scanning, so ABSOLUTE_PATH wins.
    out["compete_absolute_vs_dot"] = _one(b"/etc/./passwd")
    # 4. non-ASCII AND a trailing dot: the Windows rule runs BEFORE the
    #    non-ASCII rule in the adopted order, so WINDOWS_NAME_UNSAFE wins.
    out["compete_windows_vs_nonascii"] = _one("\u00e9.".encode("utf-8"),
                                              flags=0x0800)
    # 5. symlink whose NAME also traverses: name checks run before the
    #    file-type check, so PATH_TRAVERSAL wins over SYMLINK_ENTRY.
    out["compete_traversal_vs_symlink"] = _one(b"../link", mode=0o120777)

    # ---- Move 79 v3: central-unsupported vs local-mismatch precedence ----
    import struct as _s
    def _central_flag_local_clear(cflag):
        b = Builder(); b.add(cname=b"a.txt", flags=cflag)
        d = bytearray(b.build()); _s.pack_into("<H", d, 6, 0)  # local flags 0
        return bytes(d)
    out["compete_enc_vs_local"] = _central_flag_local_clear(0x0001)
    # central bad method, local method 0
    b = Builder(); b.add(cname=b"a.txt", method=99)
    d = bytearray(b.build()); _s.pack_into("<H", d, 8, 0)  # local method 0
    out["compete_method_vs_local"] = bytes(d)
    # central disk-start nonzero, local name differs
    b = Builder(); b.add(cname=b"safe.txt", lname=b"safe.txt")
    d = bytearray(b.build()); cd = d.find(b"PK\x01\x02")
    _s.pack_into("<H", d, cd + 34, 1)  # central disk-start = 1
    _s.pack_into("<H", d, 6, 0x0008)   # local flags differ too
    out["compete_disk_vs_local"] = bytes(d)

    # ---- Move 79 v3: byte-accurate layout fixtures ----
    out["overlapping_ranges"] = _layout_overlapping_ranges()
    out["interior_gap"] = _layout_interior_gap()
    out["orphan_local_header"] = _layout_orphan_local_header()
    out["data_into_cd"] = _layout_data_into_cd()
    out["valid_sfx_prefix"] = _layout_valid_sfx_prefix()
    out["cd_eocd_gap"] = _layout_cd_eocd_gap()
    out["compete_version_vs_local"] = _compete_version_vs_local()
    out["data_descriptor_both_set"] = _data_descriptor_both_set()

    return out


def write_corpus(dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    names = []
    for name, data in sorted(build_all().items()):
        with open(os.path.join(dest_dir, name + ".zip"), "wb") as handle:
            handle.write(data)
        names.append(name)
    return names


if __name__ == "__main__":
    import sys
    built = write_corpus(sys.argv[1] if len(sys.argv) > 1 else "archives")
    for n in built:
        print("built:", n)
