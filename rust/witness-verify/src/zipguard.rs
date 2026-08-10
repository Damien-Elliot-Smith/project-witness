//! Move 78: ZipGuard — read-only archive safety inspection.
//!
//! Parses the ZIP central directory (End Of Central Directory record +
//! central directory file headers) AND every referenced local file
//! header, using the standard library, and requires the two header sets
//! to agree. It NEVER decompresses, extracts, executes, or writes
//! anything: it reads entry metadata (names, flags, methods, versions,
//! extra fields, external attributes) and analyses the names for
//! extraction-time hazards. Local-header inspection was added in v3
//! after hostile review showed a central-directory-only parse could be
//! fooled by a benign central name masking a traversal local name.
//!
//! Grounding (corrected in v6): both real project archives were
//! re-parsed byte-for-byte. They are clean on the name axes (no
//! symlinks, duplicates, traversal, non-ASCII, case/normalization
//! collisions, no zip64) BUT they are NOT free of extra fields: every
//! one of their 970 + 819 entries carries 0x5455 Extended Timestamp
//! (central len 5 = mtime only; local len 9 = mtime + atime) and
//! 0x7875 Info-ZIP Unix UID/GID (len 11, version 1, 4-byte uid/gid),
//! created by host system 3 (Unix). An earlier candidate wrongly
//! claimed zero extra fields and would have rejected every real
//! archive. ZipGuard therefore parses these two tags strictly and
//! rejects all others.
//!
//! FAIL-CLOSED boundaries (never a safe verdict on an unchecked
//! property): zip64, encryption, compression methods other than
//! store/deflate, multi-disk, the data-descriptor flag, and ANY
//! unsupported general-purpose flag bit all yield
//! ARCHIVE_UNSUPPORTED_FEATURE. Extra-field policy is a strict
//! ALLOWLIST: 0x5455 Extended Timestamp and 0x7875 Unix UID/GID are
//! parsed and validated (they appear on every entry of the real
//! project archives); 0x7075 Unicode Path, 0x0001 ZIP64, unknown
//! tags, duplicate tags and malformed records all fail closed.
//! Flag policy: the
//! UTF-8 name flag (bit 11) IS permitted on ASCII filenames; only
//! unsupported flag BITS fail closed. Name policy: ALL non-ASCII
//! filenames fail closed with ARCHIVE_UNICODE_NAME_UNSAFE (no Unicode
//! normalization or case folding is implemented), whether or not the
//! UTF-8 flag is set.
//!
//! REASON-CODE TAXONOMY (v9, settled after the Termux gate):
//!  - ARCHIVE_LOCAL_HEADER_OFFSET_INVALID: an entry's declared local
//!    header offset is itself invalid - out of range, duplicated, or
//!    not pointing at a local header.
//!  - ARCHIVE_LOCAL_LAYOUT_INVALID: individually valid entry ranges
//!    that conflict with each other (overlap).
//!  - ARCHIVE_UNREFERENCED_DATA: archive-body bytes no central entry
//!    accounts for (prefix/SFX stub, interior gap, trailing junk,
//!    orphan local header).
//!  - ARCHIVE_UNSUPPORTED_FEATURE: a ZIP feature we do not interpret -
//!    including an unknown or disallowed extra-field tag in EITHER
//!    header. An unknown tag is an unsupported feature, not a
//!    central/local mismatch.
//!  - ARCHIVE_LOCAL_HEADER_MISMATCH: SUPPORTED fields whose parsed
//!    values disagree between central and local (name, flags, method,
//!    version, CRC, sizes, UT flags/mtime, uid/gid).
//!  - ARCHIVE_LOCAL_HEADER_MALFORMED: a local header or its extra
//!    records are structurally broken.
//!  - Path-name precedence: the MOST SPECIFIC rule wins - UNC before
//!    absolute; "."/".." components before Windows-hostile names.
//!
//! Verdict: a clean archive is INCONCLUSIVE / ARCHIVE_SAFETY_OK (this
//! stage proves nothing about bundle CONTENTS). PASS is unreachable.

use std::fs;
use std::path::Path;

pub type Failure = (String, String);

fn fail(code: &str, detail: String) -> Failure {
    (code.to_string(), detail)
}

// ---- minimal central-directory parse (read-only) ----

const EOCD_SIG: u32 = 0x0605_4b50;
const EOCD64_LOCATOR_SIG: u32 = 0x0706_4b50;
const CDH_SIG: u32 = 0x0201_4b50;

struct Entry {
    name_raw: Vec<u8>,
    raw_flags: u16,
    method: u16,
    external_attr: u32,
    version_needed: u16,
    local_offset: u32,
    central_extra: ExtraInfo,
    disk_start: u16,
    version_made_by: u16,
    crc32: u32,
    comp_size: u32,
    uncomp_size: u32,
}

/// General-purpose flag bits we support. Bit 11 (0x0800) = UTF-8 name;
/// bit 0 (0x0001) = encryption (rejected, but a known bit). Every other
/// bit is unsupported and fails closed - including bit 3 (0x0008) data
/// descriptor, which changes where sizes/CRC live.
const SUPPORTED_FLAG_MASK: u16 = 0x0800 | 0x0001;

fn utf8_flag(f: u16) -> bool { f & 0x0800 != 0 }
fn encrypted_flag(f: u16) -> bool { f & 0x0001 != 0 }

fn u16le(b: &[u8], o: usize) -> u16 {
    u16::from_le_bytes([b[o], b[o + 1]])
}
fn u32le(b: &[u8], o: usize) -> u32 {
    u32::from_le_bytes([b[o], b[o + 1], b[o + 2], b[o + 3]])
}

fn find_eocd(data: &[u8]) -> Result<usize, Failure> {
    if data.len() < 22 {
        return Err(fail("ARCHIVE_MALFORMED", "file smaller than EOCD".into()));
    }
    let max_back = data.len().saturating_sub(22).min(0xffff + 22);
    let start = data.len() - 22;
    let mut i = start;
    loop {
        if u32le(data, i) == EOCD_SIG {
            return Ok(i);
        }
        if i == 0 || start - i >= max_back {
            break;
        }
        i -= 1;
    }
    Err(fail("ARCHIVE_MALFORMED", "no End Of Central Directory record".into()))
}

fn parse_central_directory(data: &[u8]) -> Result<Vec<Entry>, Failure> {
    let eocd = find_eocd(data)?;
    // zip64 detection: EOCD locator precedes EOCD if present
    if eocd >= 20 && u32le(data, eocd - 20) == EOCD64_LOCATOR_SIG {
        return Err(fail(
            "ARCHIVE_UNSUPPORTED_FEATURE",
            "zip64 archives are not supported; cannot verify safely".into(),
        ));
    }
    let disk_no = u16le(data, eocd + 4);
    let cd_start_disk = u16le(data, eocd + 6);
    let this_disk_entries = u16le(data, eocd + 8) as usize;
    let total = u16le(data, eocd + 10) as usize;
    let cd_size = u32le(data, eocd + 12) as usize;
    let cd_offset = u32le(data, eocd + 16) as usize;
    let comment_len = u16le(data, eocd + 20) as usize;
    if disk_no != 0 || cd_start_disk != 0 {
        return Err(fail(
            "ARCHIVE_UNSUPPORTED_FEATURE",
            "multi-disk archive (nonzero disk numbers)".into(),
        ));
    }
    if this_disk_entries != total {
        return Err(fail(
            "ARCHIVE_UNSUPPORTED_FEATURE",
            "multi-disk archives are not supported".into(),
        ));
    }
    // EOCD comment must consume exactly to end of file
    if eocd + 22 + comment_len != data.len() {
        return Err(fail(
            "ARCHIVE_MALFORMED",
            "EOCD comment length does not match end of file".into(),
        ));
    }
    if cd_offset == 0xffff_ffff || cd_size == 0xffff_ffff
        || total == 0xffff
    {
        return Err(fail(
            "ARCHIVE_UNSUPPORTED_FEATURE",
            "zip64 sentinel values present; not supported".into(),
        ));
    }
    if cd_offset + cd_size > data.len() {
        return Err(fail(
            "ARCHIVE_MALFORMED",
            "central directory extends past end of file".into(),
        ));
    }

    let mut entries = Vec::new();
    let mut p = cd_offset;
    let end = cd_offset + cd_size;
    if end > eocd {
        return Err(fail(
            "ARCHIVE_MALFORMED",
            "central directory overlaps EOCD".into(),
        ));
    }
    for _ in 0..total {
        if p + 46 > end {
            return Err(fail(
                "ARCHIVE_MALFORMED",
                "central directory header truncated".into(),
            ));
        }
        if u32le(data, p) != CDH_SIG {
            return Err(fail(
                "ARCHIVE_MALFORMED",
                "bad central directory header signature".into(),
            ));
        }
        let version_made_by = u16le(data, p + 4);
        let version_needed = u16le(data, p + 6);
        let flags = u16le(data, p + 8);
        let method = u16le(data, p + 10);
        let crc32 = u32le(data, p + 16);
        let comp_size = u32le(data, p + 20);
        let uncomp_size = u32le(data, p + 24);
        let name_len = u16le(data, p + 28) as usize;
        let extra_len = u16le(data, p + 30) as usize;
        let comment_len = u16le(data, p + 32) as usize;
        let disk_start = u16le(data, p + 34);
        let external_attr = u32le(data, p + 38);
        let local_offset = u32le(data, p + 42);
        let name_start = p + 46;
        let name_end = name_start + name_len;
        if name_end > end {
            return Err(fail(
                "ARCHIVE_MALFORMED",
                "central directory filename truncated".into(),
            ));
        }
        let name_raw = data[name_start..name_end].to_vec();
        // Extra-field policy (v6): strict ALLOWLIST. The real project
        // archives carry 0x5455 (Extended Timestamp) and 0x7875 (Unix
        // UID/GID) on every entry, so a reject-all policy would have
        // rejected them. Both tags are parsed strictly; everything else
        // fails closed.
        let extra_end = name_end + extra_len;
        if extra_end > end {
            return Err(fail(
                "ARCHIVE_MALFORMED",
                "central extra field extends past central directory".into(),
            ));
        }
        let central_extra = parse_extra_fields(
            &data[name_end..extra_end],
            false,
            "ARCHIVE_MALFORMED",
        )?;
        entries.push(Entry {
            name_raw,
            raw_flags: flags,
            method,
            external_attr,
            version_needed,
            local_offset,
            central_extra,
            disk_start,
            version_made_by,
            crc32,
            comp_size,
            uncomp_size,
        });
        p = extra_end + comment_len;
    }
    // the parser must land exactly on the declared central-directory end
    if p != end {
        return Err(fail(
            "ARCHIVE_MALFORMED",
            format!(
                "central directory entries consumed {} bytes, declared {}",
                p - cd_offset,
                cd_size
            ),
        ));
    }
    // and the central directory must end exactly at the EOCD: any
    // intervening record is unparsed and therefore unsupported
    if end != eocd {
        return Err(fail(
            "ARCHIVE_UNSUPPORTED_FEATURE",
            "unparsed data between central directory and EOCD".into(),
        ));
    }
    Ok(entries)
}


const LFH_SIG: u32 = 0x0403_4b50;

/// Validate the local file header at `offset` and confirm its filename,
/// flags, method and version-needed match the central-directory entry.
/// Returns Ok(()) or a precise Failure. Read-only.
fn validate_local_header(
    data: &[u8],
    e: &Entry,
    cd_offset: usize,
) -> Result<(usize, usize), Failure> {
    let off = e.local_offset as usize;
    // local header must sit before the central directory
    if off + 30 > cd_offset {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_OFFSET_INVALID",
            format!("local header offset {} outside archive body", off),
        ));
    }
    if u32le(data, off) != LFH_SIG {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MALFORMED",
            format!("bad local header signature at offset {}", off),
        ));
    }
    let l_version = u16le(data, off + 4);
    let l_flags = u16le(data, off + 6);
    let l_method = u16le(data, off + 8);
    let l_crc = u32le(data, off + 14);
    let l_comp = u32le(data, off + 18);
    let l_uncomp = u32le(data, off + 22);
    let l_namelen = u16le(data, off + 26) as usize;
    let l_extralen = u16le(data, off + 28) as usize;
    if l_version != e.version_needed {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MISMATCH",
            format!(
                "local version-needed {} != central {}",
                l_version, e.version_needed
            ),
        ));
    }
    let name_start = off + 30;
    let name_end = name_start + l_namelen;
    if name_end > cd_offset || name_end + l_extralen > cd_offset {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MALFORMED",
            "local header name/extra extends into central directory".into(),
        ));
    }
    let l_name = &data[name_start..name_end];
    if l_name != e.name_raw.as_slice() {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MISMATCH",
            format!(
                "local filename {:?} != central {:?}",
                String::from_utf8_lossy(l_name),
                String::from_utf8_lossy(&e.name_raw)
            ),
        ));
    }
    if l_flags != e.raw_flags {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MISMATCH",
            format!("local flags {:#06x} != central {:#06x}",
                    l_flags, e.raw_flags),
        ));
    }
    if l_method != e.method {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MISMATCH",
            "local/central compression method disagree".into(),
        ));
    }
    if l_version > 45 {
        return Err(fail(
            "ARCHIVE_UNSUPPORTED_FEATURE",
            format!("local version-needed {} exceeds supported", l_version),
        ));
    }

    // Data descriptor (flag bit 3) moves crc/sizes to a trailer; we do
    // not parse trailers, so fail closed rather than compare zeros.
    if l_flags & 0x0008 != 0 {
        return Err(fail(
            "ARCHIVE_UNSUPPORTED_FEATURE",
            "data-descriptor flag (bit 3) is not supported".into(),
        ));
    }
    if l_crc != e.crc32 {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MISMATCH",
            "local/central CRC-32 disagree".into(),
        ));
    }
    if l_comp != e.comp_size {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MISMATCH",
            "local/central compressed size disagree".into(),
        ));
    }
    if l_uncomp != e.uncomp_size {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MISMATCH",
            "local/central uncompressed size disagree".into(),
        ));
    }

    // Local extra fields: parsed with the LOCAL form (the standard
    // defines different central/local Extended Timestamp shapes, so raw
    // bytes and lengths legitimately differ and must NOT be compared
    // byte-for-byte). Shared VALUES must agree.
    let extra_start = name_end;
    let extra_end = extra_start + l_extralen;
    if extra_end > cd_offset {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MALFORMED",
            "local extra field extends past archive body".into(),
        ));
    }
    let local_extra = parse_extra_fields(
        &data[extra_start..extra_end],
        true,
        "ARCHIVE_LOCAL_HEADER_MALFORMED",
    )?;
    if local_extra.ut_flags != e.central_extra.ut_flags {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MISMATCH",
            format!(
                "central/local Extended Timestamp flags disagree \
                 ({:?} vs {:?})",
                e.central_extra.ut_flags, local_extra.ut_flags
            ),
        ));
    }
    if local_extra.ut_mtime != e.central_extra.ut_mtime {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MISMATCH",
            "central/local Extended Timestamp mtime disagree".into(),
        ));
    }
    if local_extra.ux_uid != e.central_extra.ux_uid
        || local_extra.ux_gid != e.central_extra.ux_gid
    {
        return Err(fail(
            "ARCHIVE_LOCAL_HEADER_MISMATCH",
            "central/local Unix UID/GID disagree".into(),
        ));
    }

    // full local entry range: header + name + extra + compressed data.
    // (comp_size already equals central and is validated above.)
    let data_start = extra_end;
    let range_end = data_start + e.comp_size as usize;
    if range_end > cd_offset {
        return Err(fail(
            "ARCHIVE_MALFORMED",
            format!("entry data ends at {} past central directory {}",
                    range_end, cd_offset),
        ));
    }
    Ok((off, range_end))
}



/// Windows-hostile filename component analysis. Windows silently strips
/// trailing dots/spaces, reserves DOS device names, and treats ':' as an
/// alternate-data-stream separator. Extraction on Windows could then
/// overwrite or redirect. We fail closed on all of these.
fn analyse_windows_name(name: &str) -> Option<Failure> {
    const RESERVED: [&str; 5] = ["CON", "PRN", "AUX", "NUL", "CLOCK$"];
    for comp in name.trim_end_matches('/').split('/') {
        // ADS / stream syntax (drive prefix already handled earlier)
        if comp.contains(':') {
            return Some(fail(
                "ARCHIVE_ALTERNATE_DATA_STREAM",
                format!("colon / NTFS stream syntax in component {:?}", comp),
            ));
        }
        // trailing dot or space (Windows strips them -> overwrite risk)
        if comp.ends_with('.') || comp.ends_with(' ') {
            return Some(fail(
                "ARCHIVE_WINDOWS_NAME_UNSAFE",
                format!("component has trailing dot/space: {:?}", comp),
            ));
        }
        // reserved device name, with or without an extension
        let stem = comp.split('.').next().unwrap_or(comp);
        let upper = stem.to_ascii_uppercase();
        if RESERVED.contains(&upper.as_str()) {
            return Some(fail(
                "ARCHIVE_WINDOWS_NAME_UNSAFE",
                format!("reserved DOS device name: {:?}", comp),
            ));
        }
        if (upper.starts_with("COM") || upper.starts_with("LPT"))
            && upper.len() == 4
        {
            let d = upper.as_bytes()[3];
            if (b'1'..=b'9').contains(&d) {
                return Some(fail(
                    "ARCHIVE_WINDOWS_NAME_UNSAFE",
                    format!("reserved DOS device name: {:?}", comp),
                ));
            }
        }
    }
    None
}


// ---- extra-field allowlist (strictly parsed, grounded in real bytes) ----

const TAG_UT: u16 = 0x5455;   // Extended Timestamp
const TAG_UX: u16 = 0x7875;   // Info-ZIP Unix UID/GID
const TAG_UNICODE_PATH: u16 = 0x7075;
const TAG_ZIP64: u16 = 0x0001;

/// Parsed, validated contents of an entry's extra fields.
#[derive(Default, PartialEq, Debug)]
struct ExtraInfo {
    ut_flags: Option<u8>,
    ut_mtime: Option<i32>,
    ux_uid: Option<u64>,
    ux_gid: Option<u64>,
}

/// Strictly parse one extra-field blob. `is_local` selects the local or
/// central form of the Extended Timestamp (central: mtime only; local:
/// mtime plus optionally atime/ctime, per the flag bits). Unknown tags,
/// duplicate tags, and malformed records all fail closed.
fn parse_extra_fields(
    blob: &[u8],
    is_local: bool,
    malformed_code: &str,
) -> Result<ExtraInfo, Failure> {
    let mut info = ExtraInfo::default();
    let mut seen: Vec<u16> = Vec::new();
    let mut p: usize = 0;
    while p < blob.len() {
        if p + 4 > blob.len() {
            return Err(fail(
                malformed_code,
                "truncated extra-field header".into(),
            ));
        }
        let tag = u16::from_le_bytes([blob[p], blob[p + 1]]);
        let sz = u16::from_le_bytes([blob[p + 2], blob[p + 3]]) as usize;
        if p + 4 + sz > blob.len() {
            return Err(fail(
                malformed_code,
                format!("extra record {:#06x} overruns blob", tag),
            ));
        }
        if seen.contains(&tag) {
            return Err(fail(
                malformed_code,
                format!("duplicate extra tag {:#06x}", tag),
            ));
        }
        seen.push(tag);
        let payload = &blob[p + 4..p + 4 + sz];

        match tag {
            TAG_ZIP64 => {
                return Err(fail(
                    "ARCHIVE_UNSUPPORTED_FEATURE",
                    "zip64 extended information is not supported".into(),
                ));
            }
            TAG_UNICODE_PATH => {
                return Err(fail(
                    "ARCHIVE_UNSUPPORTED_FEATURE",
                    "Unicode Path extra field can change filename \
                     interpretation; not supported".into(),
                ));
            }
            TAG_UT => {
                if payload.is_empty() {
                    return Err(fail(malformed_code,
                                    "empty Extended Timestamp".into()));
                }
                let flags = payload[0];
                // only mtime/atime/ctime bits may be set
                if flags & !0x07 != 0 {
                    return Err(fail(
                        "ARCHIVE_UNSUPPORTED_FEATURE",
                        format!("unsupported UT flag bits {:#04x}", flags),
                    ));
                }
                if flags & 0x01 == 0 {
                    return Err(fail(
                        "ARCHIVE_UNSUPPORTED_FEATURE",
                        "Extended Timestamp without mtime is not supported"
                            .into(),
                    ));
                }
                // central form: exactly flags + mtime (5 bytes).
                // local form: flags + mtime, plus one 4-byte value per
                // additional advertised bit.
                let extra_times = if is_local {
                    ((flags >> 1) & 0x01) as usize
                        + ((flags >> 2) & 0x01) as usize
                } else {
                    0
                };
                let want = 1 + 4 + 4 * extra_times;
                if sz != want {
                    return Err(fail(
                        malformed_code,
                        format!(
                            "Extended Timestamp length {} != expected {} \
                             (flags {:#04x}, {})",
                            sz, want, flags,
                            if is_local { "local" } else { "central" }
                        ),
                    ));
                }
                let mtime = i32::from_le_bytes([
                    payload[1], payload[2], payload[3], payload[4],
                ]);
                info.ut_flags = Some(flags);
                info.ut_mtime = Some(mtime);
            }
            TAG_UX => {
                // version(1) uidsize(1) uid(n) gidsize(1) gid(m)
                if payload.len() < 3 {
                    return Err(fail(malformed_code,
                                    "Unix UID/GID field too short".into()));
                }
                if payload[0] != 1 {
                    return Err(fail(
                        "ARCHIVE_UNSUPPORTED_FEATURE",
                        format!("Unix UID/GID version {} unsupported",
                                payload[0]),
                    ));
                }
                let uidsz = payload[1] as usize;
                if uidsz == 0 || uidsz > 8 || payload.len() < 2 + uidsz + 1 {
                    return Err(fail(malformed_code,
                                    "malformed Unix UID length".into()));
                }
                let mut uid: u64 = 0;
                for (i, b) in payload[2..2 + uidsz].iter().enumerate() {
                    uid |= (*b as u64) << (8 * i);
                }
                let gidsz = payload[2 + uidsz] as usize;
                if gidsz == 0
                    || gidsz > 8
                    || payload.len() != 3 + uidsz + gidsz
                {
                    return Err(fail(malformed_code,
                                    "malformed Unix GID length".into()));
                }
                let mut gid: u64 = 0;
                for (i, b) in
                    payload[3 + uidsz..3 + uidsz + gidsz].iter().enumerate()
                {
                    gid |= (*b as u64) << (8 * i);
                }
                info.ux_uid = Some(uid);
                info.ux_gid = Some(gid);
            }
            other => {
                return Err(fail(
                    "ARCHIVE_UNSUPPORTED_FEATURE",
                    format!("unknown extra-field tag {:#06x}", other),
                ));
            }
        }
        p += 4 + sz;
    }
    Ok(info)
}

// ---- name safety analysis ----

fn is_bidi_control(c: char) -> bool {
    matches!(c as u32,
        0x202A..=0x202E | 0x2066..=0x2069 | 0x200E | 0x200F | 0x061C)
}

/// Non-ASCII policy (Move 78 v3, after hostile review).
///
/// We implement neither Unicode normalization (NFC/NFD) nor Unicode case
/// folding. Without both, we cannot honestly prove that two non-ASCII
/// names will not collide at extraction time on a normalizing or
/// case-insensitive filesystem. The earlier heuristic (reject only
/// combining marks) was UNSOUND: precomposed forms such as "É" carry no
/// combining mark, so they were accepted and then case-compared with
/// ASCII-only lowercase - which does not fold É to é. That is exactly
/// the "safe verdict on an unchecked property" this project forbids.
///
/// Therefore EVERY non-ASCII filename fails closed with
/// ARCHIVE_UNICODE_NAME_UNSAFE, UTF-8 flag or not. Both real project
/// archives are pure ASCII (computed during grounding), so this costs
/// nothing today. Lifting it requires a real normalization + case-fold
/// implementation, reviewed and approved.
fn is_non_ascii(s: &str) -> bool {
    !s.is_ascii()
}

fn analyse_name(name: &str) -> Option<Failure> {
    // control characters
    if let Some(c) = name.chars().find(|c| (*c as u32) < 0x20 || *c as u32 == 0x7f) {
        return Some(fail(
            "ARCHIVE_CONTROL_CHARACTER",
            format!("control character U+{:04X} in name {:?}", c as u32, name),
        ));
    }
    // bidi / directionality controls
    if let Some(c) = name.chars().find(|c| is_bidi_control(*c)) {
        return Some(fail(
            "ARCHIVE_BIDI_CHARACTER",
            format!("bidi control U+{:04X} in name {:?}", c as u32, name),
        ));
    }
    // PRECEDENCE (v9 repair): the MORE SPECIFIC rule must fire first, or
    // a correct rejection reports a misleading reason. Two bugs found by
    // the Termux gate: UNC (//server) was masked by the generic
    // absolute-path rule, and "." components were masked by the Windows
    // trailing-dot rule. Order is now:
    //   UNC -> absolute -> backslash -> drive -> traversal ("." and "..")
    //   -> Windows-hostile -> non-ASCII

    // UNC (\\server or //server) BEFORE generic absolute: "//server"
    // also starts with '/', so absolute would otherwise win.
    if name.starts_with("\\\\") || name.starts_with("//") {
        return Some(fail(
            "ARCHIVE_UNC_PATH",
            format!("UNC-style path: {:?}", name),
        ));
    }
    // absolute unix
    if name.starts_with('/') {
        return Some(fail(
            "ARCHIVE_ABSOLUTE_PATH",
            format!("absolute path: {:?}", name),
        ));
    }
    if name.contains('\\') {
        return Some(fail(
            "ARCHIVE_BACKSLASH_PATH",
            format!("backslash separator in name: {:?}", name),
        ));
    }
    // windows drive  X:  at start
    let bytes = name.as_bytes();
    if bytes.len() >= 2
        && bytes[1] == b':'
        && bytes[0].is_ascii_alphabetic()
    {
        return Some(fail(
            "ARCHIVE_WINDOWS_DRIVE_PATH",
            format!("windows drive path: {:?}", name),
        ));
    }
    // traversal: any component equal to ".." or "." — BEFORE the Windows
    // name rules, so "a/./b" reports PATH_TRAVERSAL rather than being
    // caught by the Windows trailing-dot rule. (A trailing-dot NAME like
    // "file." is not a "." component and still reaches the Windows rule.)
    for comp in name.trim_end_matches('/').split('/') {
        if comp == ".." || comp == "." {
            return Some(fail(
                "ARCHIVE_PATH_TRAVERSAL",
                format!("{:?} path component in {:?}", comp, name),
            ));
        }
    }
    // Windows-hostile components
    if let Some(f) = analyse_windows_name(name) {
        return Some(f);
    }
    if is_non_ascii(name) {
        return Some(fail(
            "ARCHIVE_UNICODE_NAME_UNSAFE",
            format!(
                "non-ASCII filename: Unicode normalization and case folding \
                 are not implemented, so collision safety cannot be proven; \
                 failing closed on {:?}",
                name
            ),
        ));
    }
    None
}

/// Structural path validation run before collision keying. Rejects
/// dot components, empty interior components (repeated separators),
/// empty filenames, and trailing-dot tricks. Returns a Failure or the
/// cleaned component vector (without any trailing-slash marker).
fn validate_path_components(name: &str) -> Result<Vec<String>, Failure> {
    let is_dir = name.ends_with('/');
    let core = if is_dir { &name[..name.len() - 1] } else { name };
    if core.is_empty() {
        return Err(fail(
            "ARCHIVE_MALFORMED",
            format!("empty filename: {:?}", name),
        ));
    }
    let mut comps = Vec::new();
    for comp in core.split('/') {
        if comp.is_empty() {
            return Err(fail(
                "ARCHIVE_PATH_TRAVERSAL",
                format!("empty path component (repeated separator) in {:?}",
                        name),
            ));
        }
        if comp == "." {
            return Err(fail(
                "ARCHIVE_PATH_TRAVERSAL",
                format!("'.' path component in {:?}", name),
            ));
        }
        comps.push(comp.to_string());
    }
    Ok(comps)
}


pub fn inspect_archive(path: &Path) -> Result<usize, Failure> {
    let data = match fs::read(path) {
        Ok(d) => d,
        Err(e) => {
            return Err(fail(
                "ARCHIVE_IO_ERROR",
                format!("could not read archive: {}", e),
            ));
        }
    };
    let entries = parse_central_directory(&data)?;
    if entries.is_empty() {
        return Err(fail("ARCHIVE_MALFORMED", "no entries".into()));
    }
    // recover cd_offset for local-header bounds checking
    let eocd = find_eocd(&data)?;
    let cd_offset = u32le(&data, eocd + 16) as usize;
    let mut seen_local_offsets = std::collections::BTreeSet::new();
    let mut ranges: Vec<(usize, usize)> = Vec::new();

    let mut exact_seen = std::collections::BTreeSet::new();
    let mut ci_seen: std::collections::BTreeMap<String, String> =
        std::collections::BTreeMap::new();
    let mut dir_prefixes = std::collections::BTreeSet::new();
    let mut file_prefixes = std::collections::BTreeSet::new();

    for e in &entries {
        // unsupported features fail closed BEFORE any safe conclusion
        if encrypted_flag(e.raw_flags) {
            return Err(fail(
                "ARCHIVE_UNSUPPORTED_FEATURE",
                "encrypted entry cannot be verified".into(),
            ));
        }
        if e.method != 0 && e.method != 8 {
            return Err(fail(
                "ARCHIVE_UNSUPPORTED_FEATURE",
                format!("unsupported compression method {}", e.method),
            ));
        }
        if e.version_needed > 45 {
            return Err(fail(
                "ARCHIVE_UNSUPPORTED_FEATURE",
                format!("version-needed {} exceeds supported", e.version_needed),
            ));
        }
        if e.disk_start != 0 {
            return Err(fail(
                "ARCHIVE_UNSUPPORTED_FEATURE",
                format!("entry disk-start {} is not zero (multi-disk)",
                        e.disk_start),
            ));
        }
        // duplicate/unsafe local-header offsets
        if !seen_local_offsets.insert(e.local_offset) {
            return Err(fail(
                "ARCHIVE_LOCAL_HEADER_OFFSET_INVALID",
                format!("duplicate local-header offset {}", e.local_offset),
            ));
        }
        // validate the local header matches the central entry and
        // collect its byte range for overlap / embedding detection
        // Flag policy ORDER matters (v5 repair, same class as the v3
        // collision-order bug): validate_local_header compares the RAW
        // flags words first, so a central/local disagreement reports
        // ARCHIVE_LOCAL_HEADER_MISMATCH. Only once both headers AGREE do
        // we judge whether the agreed bits are supported.
        let (r_start, r_end) = validate_local_header(&data, e, cd_offset)?;
        ranges.push((r_start, r_end));
        if e.raw_flags & !SUPPORTED_FLAG_MASK != 0 {
            return Err(fail(
                "ARCHIVE_UNSUPPORTED_FEATURE",
                format!("unsupported general-purpose flag bits {:#06x}",
                        e.raw_flags & !SUPPORTED_FLAG_MASK),
            ));
        }
        // filename encoding: only trust UTF-8 when flagged, or pure ASCII
        let is_ascii = e.name_raw.iter().all(|b| *b < 0x80);
        let name = if is_ascii {
            String::from_utf8(e.name_raw.clone()).unwrap()
        } else if utf8_flag(e.raw_flags) {
            match std::str::from_utf8(&e.name_raw) {
                Ok(s) => s.to_string(),
                Err(_) => {
                    return Err(fail(
                        "ARCHIVE_UNICODE_NAME_UNSAFE",
                        "UTF-8 flag set but bytes are not valid UTF-8".into(),
                    ));
                }
            }
        } else {
            return Err(fail(
                "ARCHIVE_UNICODE_NAME_UNSAFE",
                "non-ASCII name without UTF-8 flag; encoding ambiguous".into(),
            ));
        };

        if let Some(f) = analyse_name(&name) {
            return Err(f);
        }
        let comps = validate_path_components(&name)?;

        // Creator host (v6): the high byte of version-made-by. The real
        // project archives are all host 3 (Unix), so external_attr's high
        // bits are Unix mode bits. Any other creator system uses
        // different attribute semantics we do not interpret -> fail
        // closed rather than guess.
        let creator_host = (e.version_made_by >> 8) as u8;
        if creator_host != 3 {
            return Err(fail(
                "ARCHIVE_UNSUPPORTED_FEATURE",
                format!(
                    "creator host system {} is not supported (only 3 = Unix)",
                    creator_host
                ),
            ));
        }

        // Unix file type in the high 16 bits of external_attr. Only
        // regular files (0x8000) and directories (0x4000) are allowed;
        // symlinks, FIFOs, sockets, and devices fail closed. A ZERO file
        // type is ambiguous on a Unix-created archive -> rejected rather
        // than guessed.
        let unix_mode = (e.external_attr >> 16) as u16;
        let ftype = unix_mode & 0xF000;
        let name_is_dir = name.ends_with('/');
        if ftype == 0 {
            return Err(fail(
                "ARCHIVE_SPECIAL_FILE_TYPE",
                format!("ambiguous zero Unix file type in {:?}", name),
            ));
        }
        {
            match ftype {
                0xA000 => {
                    return Err(fail(
                        "ARCHIVE_SYMLINK_ENTRY",
                        format!("symlink entry: {:?}", name),
                    ));
                }
                0x8000 => {
                    // regular file: name must not claim to be a directory
                    if name_is_dir {
                        return Err(fail(
                            "ARCHIVE_FILE_DIRECTORY_COLLISION",
                            format!(
                                "trailing-slash name with regular-file \
                                 mode: {:?}",
                                name
                            ),
                        ));
                    }
                }
                0x4000 => {
                    // directory: name must carry the trailing slash and
                    // the entry must carry no data
                    if !name_is_dir {
                        return Err(fail(
                            "ARCHIVE_FILE_DIRECTORY_COLLISION",
                            format!(
                                "directory mode without trailing slash: {:?}",
                                name
                            ),
                        ));
                    }
                    if e.comp_size != 0
                        || e.uncomp_size != 0
                        || e.crc32 != 0
                    {
                        return Err(fail(
                            "ARCHIVE_MALFORMED",
                            format!("directory entry carries data: {:?}",
                                    name),
                        ));
                    }
                }
                other => {
                    return Err(fail(
                        "ARCHIVE_SPECIAL_FILE_TYPE",
                        format!(
                            "non-regular, non-directory Unix file type \
                             {:#06x} in {:?}",
                            other, name
                        ),
                    ));
                }
            }
        }

        // exact duplicate
        if !exact_seen.insert(name.clone()) {
            return Err(fail(
                "ARCHIVE_DUPLICATE_NAME",
                format!("duplicate entry name: {:?}", name),
            ));
        }

        // Collision detection (Move 78 v4). All comparisons are done on
        // the ASCII-case-folded component path (non-ASCII already failed
        // closed), so case-insensitive collisions are covered uniformly.
        let is_dir = name.ends_with('/');
        let comps_lc: Vec<String> =
            comps.iter().map(|c| c.to_ascii_lowercase()).collect();
        let base_lc = comps_lc.join("/");

        // (a) every ancestor prefix of this entry must be a directory,
        //     and must not already be a file. This catches "a" (file)
        //     then "a/b", and the case-folded variant "A" then "a/b".
        for depth in 1..comps_lc.len() {
            let prefix = comps_lc[..depth].join("/");
            if file_prefixes.contains(&prefix) {
                return Err(fail(
                    "ARCHIVE_FILE_DIRECTORY_COLLISION",
                    format!("{:?} is a file but is used as a directory                              prefix", prefix),
                ));
            }
            dir_prefixes.insert(prefix);
        }

        // (b) this entry's own path
        if is_dir {
            if file_prefixes.contains(&base_lc) {
                return Err(fail(
                    "ARCHIVE_FILE_DIRECTORY_COLLISION",
                    format!("path is both file and directory: {:?}", base_lc),
                ));
            }
            dir_prefixes.insert(base_lc.clone());
        } else {
            // a file path may not already be required as a directory
            if dir_prefixes.contains(&base_lc) {
                return Err(fail(
                    "ARCHIVE_FILE_DIRECTORY_COLLISION",
                    format!("path is both file and directory: {:?}", base_lc),
                ));
            }
            file_prefixes.insert(base_lc.clone());
        }

        // (c) exact duplicate / case / normalized collision
        let key = base_lc.clone();
        if let Some(prev) = ci_seen.get(&key) {
            if prev != &name {
                return Err(fail(
                    "ARCHIVE_CASE_COLLISION",
                    format!(
                        "case-insensitive collision: {:?} vs {:?}",
                        prev, name
                    ),
                ));
            }
            return Err(fail(
                "ARCHIVE_NORMALIZED_NAME_COLLISION",
                format!("normalized-name collision: {:?}", name),
            ));
        }
        ci_seen.insert(key, name.clone());
    }

    // Archive-body layout (v6, BLOCKER 2): the validated local-entry
    // ranges must tile the region [0, cd_offset) exactly. Any prefix
    // bytes (e.g. an SFX stub), interior gap, overlap, or trailing
    // unreferenced bytes means the archive body contains data no central
    // entry accounts for - including an orphan local header with a
    // traversal name. Fail closed.
    ranges.sort();
    let mut cursor: usize = 0;
    for (start, end) in &ranges {
        if *start < cursor {
            return Err(fail(
                "ARCHIVE_LOCAL_LAYOUT_INVALID",
                format!("local entry range [{},{}) overlaps previous data \
                         ending at {}", start, end, cursor),
            ));
        }
        if *start > cursor {
            return Err(fail(
                "ARCHIVE_UNREFERENCED_DATA",
                format!("{} unreferenced byte(s) at offset {} before the \
                         next local entry", start - cursor, cursor),
            ));
        }
        cursor = *end;
    }
    if cursor != cd_offset {
        return Err(fail(
            "ARCHIVE_UNREFERENCED_DATA",
            format!("{} unreferenced byte(s) between the last local entry \
                     and the central directory", cd_offset - cursor),
        ));
    }

    Ok(entries.len())
}
