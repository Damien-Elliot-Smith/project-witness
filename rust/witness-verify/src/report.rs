//! Move 83 — structured verification report (`witness-report/1`).
//!
//! STRICTLY ADDITIVE. This module is reachable only from the two new
//! `report-bundle` / `report-archive` invocations. It adds NO check, NO
//! verification capability, NO reason code and NO verdict. It changes no
//! existing behaviour: `verify` and `inspect-archive` still run exactly
//! the code they ran before, still emit exactly one legacy line, and
//! still exit with exactly the same codes.
//!
//! EXECUTION HONESTY. The adopted evaluation short-circuits: it returns
//! on the first failing check, so later checks genuinely never run. This
//! module preserves that behaviour exactly — it calls the same check
//! functions in the same adopted order and stops at the same point — and
//! records every check that did not execute as `NOT_RUN` with the reason
//! it was skipped. No PASS, FAIL or INCONCLUSIVE result is ever inferred,
//! invented or synthesised for a check that never ran. The report is
//! evidence of what was executed, never a prediction of what would have
//! happened.
//!
//! The report is canonical JSON: sorted keys, compact separators, exactly
//! one object, exactly one trailing newline, no timestamps and no
//! host-dependent values.

use std::fs;
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::FileTypeExt;
use std::os::unix::fs::MetadataExt;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

use crate::hashes;
use crate::json_escape;
use crate::manifest;
use crate::receipts;
use crate::sha256;
use crate::zipguard;
use crate::{EXIT_FAIL, EXIT_INCONCLUSIVE, VERDICT_FAIL, VERDICT_INCONCLUSIVE, VERSION};

pub const REPORT_SCHEMA_VERSION: &str = "witness-report/1";
// The Rust verifier reports what it EXECUTED. Reason class and stage are
// defined by the adopted reason_map.json authority, which the verifier
// does not and must not read, so the record it emits is the CORE record;
// a completion step looks the classification up from the adopted bytes
// and emits record_type "verification_report".
pub const REPORT_RECORD_TYPE: &str = "verification_report_core";
pub const REPORT_PRODUCER: &str = "witness-verify-report";
pub const REPORT_PRODUCER_VERSION: &str = "0.0.1-step83-report";
pub const VERIFIER_NAME: &str = "witness-verify";

pub const STATUS_PASSED: &str = "PASSED";
pub const STATUS_FAILED: &str = "FAILED";
pub const STATUS_NOT_RUN: &str = "NOT_RUN";

pub const DIGEST_MEASURED: &str = "MEASURED";
pub const DIGEST_UNMEASURABLE: &str = "UNMEASURABLE";

/// Domain separation and version prefix for the bundle digest.
const DIGEST_DOMAIN: &[u8] = b"witness-bundle-digest/3\n";
/// The mode bits bound into the digest.
const DIGEST_MODE_MASK: u32 = 0o7777;

const DIGEST_SCOPE_BUNDLE: &str =
    "sha256 over an injective serialization of EVERY entry in the bundle \
     tree. The serialization is domain-separated. It begins with the \
     domain-separation prefix bytes 'witness-bundle-digest/3' followed by \
     a newline and then an 8-byte little-endian count of entries. Every \
     entry is covered and every Unix entry type carries its OWN tag; none \
     is collapsed into a generic class. Entries are ordered by their RAW \
     relative-path bytes and then by kind. Each entry appends a 4-byte \
     little-endian kind tag; an 8-byte little-endian length of the raw \
     relative-path bytes; those raw bytes verbatim (the exact raw Unix \
     path bytes and never a lossy string conversion); a 4-byte \
     little-endian encoding of the entry's ACTUAL Unix mode bits masked \
     with 0o7777; an 8-byte little-endian payload length; and the payload \
     itself. The kind tags are 1 for a regular file; 2 for a directory \
     including an empty one; 3 for a symbolic link; 4 for a FIFO; 5 for a \
     socket; 6 for a block device; 7 for a character device; and 8 for an \
     entry the kernel reports as none of these. The payload is the 64 \
     lowercase-hex bytes of a regular file's content sha256; the RAW \
     target bytes of a symbolic link; the 8-byte little-endian rdev of a \
     block or character device so two device nodes differing only in \
     device identity are distinguished; and empty for every other kind. \
     Because the kind tag is explicit and every variable-length element \
     is length-prefixed; distinct trees can never collapse to the same \
     digest. Adding or removing or renaming an empty directory changes \
     the digest; a regular file cannot masquerade as a directory or a \
     symbolic link or a FIFO or a socket or a device; and two symbolic \
     links with different targets are distinguished even when their \
     counts match. Symbolic links are NEVER followed -- only their target \
     bytes are bound as identity -- so nothing outside the bundle can be \
     drawn in. The digest therefore binds the complete tree structure \
     together with exact relative paths and entry types and relevant mode \
     bits and content and device identity. This definition is Unix-only. \
     It reads the ACTUAL Unix mode and type and device identity via the \
     Unix filesystem interfaces and the raw Unix path bytes via the Unix \
     byte interface; no cross-platform definition is claimed. The \
     file_count field counts regular files only and \
     non_regular_entry_count counts symbolic links and FIFOs and sockets \
     and devices and unrecognised entries; directories are bound into the \
     digest but are not counted by either field.";

const DIGEST_SCOPE_ARCHIVE: &str =
    "sha256 over the complete bytes of the archive file as supplied.";

/// One executed-or-skipped check.
struct CheckRecord {
    name: &'static str,
    status: &'static str,
    reason_code: Option<String>,
    not_run_reason: Option<String>,
    observed: Option<(&'static str, usize)>,
}

impl CheckRecord {
    fn passed(name: &'static str, observed: Option<(&'static str, usize)>) -> Self {
        CheckRecord {
            name,
            status: STATUS_PASSED,
            reason_code: None,
            not_run_reason: None,
            observed,
        }
    }

    fn failed(name: &'static str, code: &str) -> Self {
        CheckRecord {
            name,
            status: STATUS_FAILED,
            reason_code: Some(code.to_string()),
            not_run_reason: None,
            observed: None,
        }
    }

    fn not_run(name: &'static str, why: String) -> Self {
        CheckRecord {
            name,
            status: STATUS_NOT_RUN,
            reason_code: None,
            not_run_reason: Some(why),
            observed: None,
        }
    }

    /// Canonical JSON object for this check. Keys sorted:
    /// name, not_run_reason, observed, reason_code, status.
    fn to_json(&self) -> String {
        let mut out = String::from("{");
        out.push_str(&format!("\"name\":\"{}\"", json_escape(self.name)));
        out.push_str(",\"not_run_reason\":");
        match &self.not_run_reason {
            Some(v) => out.push_str(&format!("\"{}\"", json_escape(v))),
            None => out.push_str("null"),
        }
        out.push_str(",\"observed\":");
        match self.observed {
            Some((key, value)) => {
                out.push_str(&format!("{{\"{}\":{}}}", json_escape(key), value));
            }
            None => out.push_str("null"),
        }
        out.push_str(",\"reason_code\":");
        match &self.reason_code {
            Some(v) => out.push_str(&format!("\"{}\"", json_escape(v))),
            None => out.push_str("null"),
        }
        out.push_str(&format!(",\"status\":\"{}\"", json_escape(self.status)));
        out.push('}');
        out
    }
}

/// The adopted bundle check sequence, in adopted order.
const BUNDLE_CHECKS: [&str; 5] = [
    "bundle_path_exists",
    "bundle_path_is_directory",
    "manifest_structure",
    "declared_top_level_hashes",
    "receipt_chain",
];

// The adopted `evaluate_archive` performs EXACTLY ONE check:
// zipguard::inspect_archive. A missing or unreadable archive is reported
// by zipguard with its own adopted reason code. v01 invented an
// `archive_path_readable` check, recorded it FAILED, and then still ran
// and recorded the safety check -- reporting an executed result after
// evaluation had already stopped, and inventing a reason code that is not
// in the adopted vocabulary. Both are gone.
const ARCHIVE_CHECKS: [&str; 1] = ["archive_safety"];

fn skipped_because(previous: &str, code: &str) -> String {
    format!(
        "not executed. Evaluation stopped at the earlier check '{}' with \
         reason code {}. The adopted verifier does not continue past a \
         failing check; no result for this check exists",
        previous, code
    )
}


/// Entry kinds bound explicitly into the digest so that a directory, a
/// regular file, a symlink and any other entry can never masquerade as
/// one another.
const ENTRY_KIND_FILE: u32 = 1;
const ENTRY_KIND_DIRECTORY: u32 = 2;
const ENTRY_KIND_SYMLINK: u32 = 3;
const ENTRY_KIND_FIFO: u32 = 4;
const ENTRY_KIND_SOCKET: u32 = 5;
const ENTRY_KIND_BLOCK_DEVICE: u32 = 6;
const ENTRY_KIND_CHAR_DEVICE: u32 = 7;
/// Reached only if the kernel reports a type none of the Unix predicates
/// above recognise. It is a distinct tag, never a bucket the known types
/// fall into.
const ENTRY_KIND_UNRECOGNISED: u32 = 8;

/// One filesystem entry, typed and identity-bound.
struct TreeEntry {
    relpath: Vec<u8>,
    kind: u32,
    mode: u32,
    /// For a regular file the lowercase-hex sha256 of its content. For a
    /// symlink the RAW bytes of its target. Empty for other kinds.
    payload: Vec<u8>,
}

/// Raw bytes of a path component or path.
///
/// `OsStrExt::as_bytes` is the explicit Unix byte interface and returns
/// the kernel's bytes verbatim, so two distinct filesystem paths can never
/// collapse to the same value. A lossy string conversion would map every
/// invalid UTF-8 byte to the same replacement character and make distinct
/// names collide.
fn path_bytes(path: &Path) -> Vec<u8> {
    path.as_os_str().as_bytes().to_vec()
}

/// The ACTUAL Unix mode bits of an entry, masked with 0o7777.
///
/// An earlier version approximated this from `Permissions::readonly()`,
/// which collapses every writable mode to 0o644 and every read-only mode
/// to 0o444. That discarded the executable bits, the group/other
/// distinctions and the special bits. The real mode is read from the
/// filesystem metadata.
///
/// This uses the Unix permission interface deliberately. The digest
/// definition is therefore Unix-only, which matches the only target this
/// project has established.
fn mode_bits(meta: &fs::Metadata) -> u32 {
    meta.permissions().mode() & DIGEST_MODE_MASK
}

/// Collect EVERY entry under `root`, typed and identity-bound.
///
/// Directories are collected in their own right, including empty ones,
/// because a tree containing an empty directory is not the same tree as
/// one without it. Symlinks are never followed; their target bytes are
/// bound as identity so two different links cannot collapse together.
/// Returns the entries plus the regular-file and non-regular counts.
fn collect_entries(root: &Path)
    -> std::io::Result<(Vec<TreeEntry>, usize, usize)>
{
    let mut entries: Vec<TreeEntry> = Vec::new();
    let mut file_count: usize = 0;
    let mut non_regular: usize = 0;
    let mut stack: Vec<PathBuf> = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let mut children: Vec<PathBuf> = Vec::new();
        for child in fs::read_dir(&dir)? {
            children.push(child?.path());
        }
        children.sort();
        for path in children {
            // symlink_metadata: links are never followed, so a link can
            // not smuggle content in from outside the bundle.
            let meta = fs::symlink_metadata(&path)?;
            let file_type = meta.file_type();
            let rel = path.strip_prefix(root).unwrap_or_else(|_| path.as_path());
            let relpath = path_bytes(rel);
            let mode = mode_bits(&meta);
            if file_type.is_dir() {
                entries.push(TreeEntry {
                    relpath,
                    kind: ENTRY_KIND_DIRECTORY,
                    mode,
                    payload: Vec::new(),
                });
                stack.push(path);
            } else if file_type.is_file() {
                let digest = sha256::digest_file(&path)?;
                entries.push(TreeEntry {
                    relpath,
                    kind: ENTRY_KIND_FILE,
                    mode,
                    payload: digest.as_bytes().to_vec(),
                });
                file_count += 1;
            } else if file_type.is_symlink() {
                // read_link, never canonicalize: the link is identified by
                // its target bytes and is never followed.
                let target = match fs::read_link(&path) {
                    Ok(t) => path_bytes(t.as_path()),
                    Err(_) => Vec::new(),
                };
                entries.push(TreeEntry {
                    relpath,
                    kind: ENTRY_KIND_SYMLINK,
                    mode,
                    payload: target,
                });
                non_regular += 1;
            } else {
                // Each remaining Unix type gets its OWN tag. Collapsing
                // them into one bucket would let a FIFO and a socket at
                // the same path with the same mode produce the same
                // digest, which would contradict the complete-tree claim.
                // Device entries additionally bind their device identity:
                // two device nodes differing only in rdev are distinct
                // objects and must not share a digest.
                let (kind, payload) = if file_type.is_fifo() {
                    (ENTRY_KIND_FIFO, Vec::new())
                } else if file_type.is_socket() {
                    (ENTRY_KIND_SOCKET, Vec::new())
                } else if file_type.is_block_device() {
                    (ENTRY_KIND_BLOCK_DEVICE,
                     meta.rdev().to_le_bytes().to_vec())
                } else if file_type.is_char_device() {
                    (ENTRY_KIND_CHAR_DEVICE,
                     meta.rdev().to_le_bytes().to_vec())
                } else {
                    (ENTRY_KIND_UNRECOGNISED, Vec::new())
                };
                entries.push(TreeEntry {
                    relpath,
                    kind,
                    mode,
                    payload,
                });
                non_regular += 1;
            }
        }
    }
    // deterministic order over RAW relative-path bytes then kind,
    // independent of directory enumeration order
    entries.sort_by(|a, b| {
        a.relpath.cmp(&b.relpath).then(a.kind.cmp(&b.kind))
    });
    Ok((entries, file_count, non_regular))
}

/// Deterministic, INJECTIVE digest over the COMPLETE bundle tree.
///
/// Every entry is serialized with an explicit kind tag, its raw relative
/// path bytes, its actual mode bits and a kind-specific payload, and every
/// variable-length element is length-prefixed. Distinct trees therefore
/// cannot collapse to the same digest -- adding, removing or renaming an
/// empty directory changes it, and a file cannot masquerade as a
/// directory or a symlink.
fn digest_bundle(root: &Path) -> std::io::Result<(String, usize, usize)> {
    let (entries, file_count, non_regular) = collect_entries(root)?;
    let mut listing: Vec<u8> = Vec::new();
    listing.extend_from_slice(DIGEST_DOMAIN);
    listing.extend_from_slice(&(entries.len() as u64).to_le_bytes());
    for entry in &entries {
        listing.extend_from_slice(&entry.kind.to_le_bytes());
        listing.extend_from_slice(&(entry.relpath.len() as u64).to_le_bytes());
        listing.extend_from_slice(&entry.relpath);
        listing.extend_from_slice(&entry.mode.to_le_bytes());
        listing.extend_from_slice(&(entry.payload.len() as u64).to_le_bytes());
        listing.extend_from_slice(&entry.payload);
    }
    Ok((sha256::digest_hex(&listing), file_count, non_regular))
}

fn limitations_json(operation: &str) -> String {
    let mut items: Vec<String> = vec![
        "this report describes only checks that genuinely executed. A \
         check recorded as NOT_RUN has no result and none is inferred"
            .to_string(),
        "the Rust verifier emits no pass verdict. An accepted bundle is \
         reported as INCONCLUSIVE by design and not as an error"
            .to_string(),
        "this report adds no check and no verification capability. It \
         describes the adopted evaluation and changes none of it"
            .to_string(),
    ];
    if operation == "verify_bundle" {
        items.push(
            "the input digest covers the bundle tree as described in the \
             scope field of input_digest. It is not the manifest's own \
             declared hash set and it does not certify the bundle"
                .to_string(),
        );
    } else {
        items.push(
            "the input digest covers the archive file bytes as described \
             in the scope field of input_digest"
                .to_string(),
        );
    }
    let parts: Vec<String> = items
        .iter()
        .map(|s| format!("\"{}\"", json_escape(s)))
        .collect();
    format!("[{}]", parts.join(","))
}


fn build_report(
    operation: &str,
    input_type: &str,
    digest_value: Option<&str>,
    digest_state: &str,
    digest_scope: &str,
    file_count: Option<usize>,
    non_regular_count: Option<usize>,
    checks: &[CheckRecord],
    verdict: &str,
    reason_code: &str,
    exit_code: i32,
) -> String {
    let check_parts: Vec<String> = checks.iter().map(|c| c.to_json()).collect();
    // Keys are emitted in sorted order: checks, exit_code,
    // final_reason_code, final_verdict, input_digest, input_type,
    // limitations, operation, producer, producer_version, record_type,
    // schema_version, verifier, verifier_version.
    let mut out = String::from("{");
    out.push_str(&format!("\"checks\":[{}]", check_parts.join(",")));
    out.push_str(&format!(",\"exit_code\":{}", exit_code));
    out.push_str(&format!(
        ",\"final_reason_code\":\"{}\"",
        json_escape(reason_code)
    ));
    out.push_str(&format!(",\"final_verdict\":\"{}\"", json_escape(verdict)));

    // input_digest keys sorted: algorithm, file_count,
    // non_regular_entry_count, scope, state, value.
    out.push_str(",\"input_digest\":{\"algorithm\":\"sha256\"");
    out.push_str(",\"file_count\":");
    match file_count {
        Some(n) => out.push_str(&n.to_string()),
        None => out.push_str("null"),
    }
    out.push_str(",\"non_regular_entry_count\":");
    match non_regular_count {
        Some(n) => out.push_str(&n.to_string()),
        None => out.push_str("null"),
    }
    out.push_str(&format!(",\"scope\":\"{}\"", json_escape(digest_scope)));
    out.push_str(&format!(",\"state\":\"{}\"", json_escape(digest_state)));
    out.push_str(",\"value\":");
    match digest_value {
        Some(v) => out.push_str(&format!("\"{}\"", json_escape(v))),
        None => out.push_str("null"),
    }
    out.push('}');

    out.push_str(&format!(",\"input_type\":\"{}\"", json_escape(input_type)));
    out.push_str(&format!(",\"limitations\":{}", limitations_json(operation)));
    out.push_str(&format!(",\"operation\":\"{}\"", json_escape(operation)));
    out.push_str(&format!(",\"producer\":\"{}\"", json_escape(REPORT_PRODUCER)));
    out.push_str(&format!(
        ",\"producer_version\":\"{}\"",
        json_escape(REPORT_PRODUCER_VERSION)
    ));
    out.push_str(&format!(
        ",\"record_type\":\"{}\"",
        json_escape(REPORT_RECORD_TYPE)
    ));
    out.push_str(&format!(
        ",\"schema_version\":\"{}\"",
        json_escape(REPORT_SCHEMA_VERSION)
    ));
    out.push_str(&format!(",\"verifier\":\"{}\"", json_escape(VERIFIER_NAME)));
    out.push_str(&format!(
        ",\"verifier_version\":\"{}\"",
        json_escape(VERSION)
    ));
    out.push('}');
    out
}

/// Report for `verify`-equivalent evaluation of a bundle directory.
///
/// Runs the adopted checks in the adopted order and stops where the
/// adopted verifier stops. Returns (report, exit code); the exit code is
/// the same code the adopted evaluation produces for the same input.
pub fn report_bundle(path: &Path) -> (String, i32) {
    let mut checks: Vec<CheckRecord> = Vec::new();

    // The digest is measured first so it is present even when evaluation
    // stops early. It is a measurement of the input, never a check.
    let (digest_value, digest_state, file_count, non_regular) =
        match digest_bundle(path) {
            Ok((value, count, non_regular)) => {
                (Some(value), DIGEST_MEASURED, Some(count), Some(non_regular))
            }
            Err(_) => (None, DIGEST_UNMEASURABLE, None, None),
        };

    if !path.exists() {
        checks.push(CheckRecord::failed(BUNDLE_CHECKS[0], "BUNDLE_PATH_MISSING"));
        for name in BUNDLE_CHECKS.iter().skip(1) {
            checks.push(CheckRecord::not_run(
                *name,
                skipped_because(BUNDLE_CHECKS[0], "BUNDLE_PATH_MISSING"),
            ));
        }
        return (
            build_report(
                "verify_bundle",
                "bundle_dir",
                digest_value.as_deref(),
                digest_state,
                DIGEST_SCOPE_BUNDLE,
                file_count,
                non_regular,
                &checks,
                VERDICT_FAIL,
                "BUNDLE_PATH_MISSING",
                EXIT_FAIL,
            ),
            EXIT_FAIL,
        );
    }
    checks.push(CheckRecord::passed(BUNDLE_CHECKS[0], None));

    if !path.is_dir() {
        checks.push(CheckRecord::failed(
            BUNDLE_CHECKS[1],
            "BUNDLE_PATH_NOT_A_DIRECTORY",
        ));
        for name in BUNDLE_CHECKS.iter().skip(2) {
            checks.push(CheckRecord::not_run(
                *name,
                skipped_because(BUNDLE_CHECKS[1], "BUNDLE_PATH_NOT_A_DIRECTORY"),
            ));
        }
        return (
            build_report(
                "verify_bundle",
                "bundle_dir",
                digest_value.as_deref(),
                digest_state,
                DIGEST_SCOPE_BUNDLE,
                file_count,
                non_regular,
                &checks,
                VERDICT_FAIL,
                "BUNDLE_PATH_NOT_A_DIRECTORY",
                EXIT_FAIL,
            ),
            EXIT_FAIL,
        );
    }
    checks.push(CheckRecord::passed(BUNDLE_CHECKS[1], None));

    if let Err((code, _detail)) = manifest::validate(path) {
        checks.push(CheckRecord::failed(BUNDLE_CHECKS[2], &code));
        for name in BUNDLE_CHECKS.iter().skip(3) {
            checks.push(CheckRecord::not_run(
                *name,
                skipped_because(BUNDLE_CHECKS[2], &code),
            ));
        }
        return (
            build_report(
                "verify_bundle",
                "bundle_dir",
                digest_value.as_deref(),
                digest_state,
                DIGEST_SCOPE_BUNDLE,
                file_count,
                non_regular,
                &checks,
                VERDICT_FAIL,
                &code,
                EXIT_FAIL,
            ),
            EXIT_FAIL,
        );
    }
    checks.push(CheckRecord::passed(BUNDLE_CHECKS[2], None));

    let hash_count = match hashes::verify_declared_hashes(path) {
        Ok(count) => count,
        Err((code, _detail)) => {
            checks.push(CheckRecord::failed(BUNDLE_CHECKS[3], &code));
            checks.push(CheckRecord::not_run(
                BUNDLE_CHECKS[4],
                skipped_because(BUNDLE_CHECKS[3], &code),
            ));
            return (
                build_report(
                    "verify_bundle",
                    "bundle_dir",
                    digest_value.as_deref(),
                    digest_state,
                    DIGEST_SCOPE_BUNDLE,
                    file_count,
                    non_regular,
                    &checks,
                    VERDICT_FAIL,
                    &code,
                    EXIT_FAIL,
                ),
                EXIT_FAIL,
            );
        }
    };
    checks.push(CheckRecord::passed(
        BUNDLE_CHECKS[3],
        Some(("declared_hashes_verified", hash_count)),
    ));

    match receipts::verify_receipt_chain(path) {
        Ok(receipt_count) => {
            checks.push(CheckRecord::passed(
                BUNDLE_CHECKS[4],
                Some(("receipts_verified", receipt_count)),
            ));
            (
                build_report(
                    "verify_bundle",
                    "bundle_dir",
                    digest_value.as_deref(),
                    digest_state,
                    DIGEST_SCOPE_BUNDLE,
                    file_count,
                    non_regular,
                    &checks,
                    VERDICT_INCONCLUSIVE,
                    "RECEIPT_CHAIN_HASHES_RECOMPUTED",
                    EXIT_INCONCLUSIVE,
                ),
                EXIT_INCONCLUSIVE,
            )
        }
        Err((code, _detail)) => {
            checks.push(CheckRecord::failed(BUNDLE_CHECKS[4], &code));
            (
                build_report(
                    "verify_bundle",
                    "bundle_dir",
                    digest_value.as_deref(),
                    digest_state,
                    DIGEST_SCOPE_BUNDLE,
                    file_count,
                    non_regular,
                    &checks,
                    VERDICT_FAIL,
                    &code,
                    EXIT_FAIL,
                ),
                EXIT_FAIL,
            )
        }
    }
}

/// Report for `inspect-archive`-equivalent evaluation of an archive.
pub fn report_archive(path: &Path) -> (String, i32) {
    let mut checks: Vec<CheckRecord> = Vec::new();

    // The digest is a MEASUREMENT of the input, never a check. When the
    // input cannot be read the measurement is unavailable, which is
    // recorded as a digest STATE -- it never becomes a verifier reason
    // code and it never fabricates a check result.
    let (digest_value, digest_state) = match fs::read(path) {
        Ok(bytes) => (Some(sha256::digest_hex(&bytes)), DIGEST_MEASURED),
        Err(_) => (None, DIGEST_UNMEASURABLE),
    };

    match zipguard::inspect_archive(path) {
        Ok(entry_count) => {
            checks.push(CheckRecord::passed(
                ARCHIVE_CHECKS[0],
                Some(("entries_inspected", entry_count)),
            ));
            (
                build_report(
                    "inspect_archive",
                    "archive_zip",
                    digest_value.as_deref(),
                    digest_state,
                    DIGEST_SCOPE_ARCHIVE,
                    None,
                    None,
                    &checks,
                    VERDICT_INCONCLUSIVE,
                    "ARCHIVE_SAFETY_OK",
                    EXIT_INCONCLUSIVE,
                ),
                EXIT_INCONCLUSIVE,
            )
        }
        Err((code, _detail)) => {
            checks.push(CheckRecord::failed(ARCHIVE_CHECKS[0], &code));
            (
                build_report(
                    "inspect_archive",
                    "archive_zip",
                    digest_value.as_deref(),
                    digest_state,
                    DIGEST_SCOPE_ARCHIVE,
                    None,
                    None,
                    &checks,
                    VERDICT_FAIL,
                    &code,
                    EXIT_FAIL,
                ),
                EXIT_FAIL,
            )
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_bundle_marks_every_later_check_not_run() {
        let (line, code) = report_bundle(Path::new("/nonexistent-bundle-xyz"));
        assert_eq!(code, EXIT_FAIL);
        assert!(line.contains("\"status\":\"FAILED\""));
        assert!(line.contains("\"status\":\"NOT_RUN\""));
        assert!(line.contains("BUNDLE_PATH_MISSING"));
        // no result is invented for checks that never ran
        assert!(!line.contains("\"status\":\"PASSED\""));
    }

    #[test]
    fn report_is_a_single_canonical_object() {
        let (line, _code) = report_bundle(Path::new("/nonexistent-bundle-xyz"));
        assert!(line.starts_with('{'));
        assert!(line.ends_with('}'));
        assert!(!line.contains('\n'));
        assert!(!line.contains(", "));
        assert!(!line.contains(": "));
    }

    #[test]
    fn report_carries_the_adopted_identities() {
        let (line, _code) = report_bundle(Path::new("/nonexistent-bundle-xyz"));
        assert!(line.contains("\"schema_version\":\"witness-report/1\""));
        assert!(line.contains("\"verifier\":\"witness-verify\""));
        assert!(line.contains(VERSION));
    }

    #[test]
    fn raw_report_emits_the_core_record_type() {
        // report_bundle emits the CORE record. Only the completion layer,
        // which looks class and stage up in the adopted reason map, turns
        // it into "verification_report".
        let (line, _code) = report_bundle(Path::new("/nonexistent-bundle-xyz"));
        assert_eq!(REPORT_RECORD_TYPE, "verification_report_core");
        assert!(line.contains("\"record_type\":\"verification_report_core\""));
        assert!(!line.contains("\"record_type\":\"verification_report\","));
    }

    #[test]
    fn raw_report_carries_no_classification() {
        // class and stage are defined by the adopted reason_map.json,
        // which this binary does not and must not read.
        let (line, _code) = report_bundle(Path::new("/nonexistent-bundle-xyz"));
        assert!(!line.contains("final_reason_class"));
        assert!(!line.contains("final_stage"));
    }

    #[test]
    fn archive_report_records_exactly_one_check() {
        let (line, _code) = report_archive(Path::new("/nonexistent-archive.zip"));
        assert_eq!(ARCHIVE_CHECKS.len(), 1);
        assert!(line.contains("\"name\":\"archive_safety\""));
        assert!(!line.contains("archive_path_readable"));
    }

    #[test]
    fn unmeasurable_digest_carries_no_value() {
        let (line, _code) = report_bundle(Path::new("/nonexistent-bundle-xyz"));
        assert!(line.contains("\"state\":\"UNMEASURABLE\""));
        assert!(line.contains("\"value\":null"));
    }

    #[test]
    fn limitations_are_never_empty() {
        let (line, _code) = report_bundle(Path::new("/nonexistent-bundle-xyz"));
        assert!(line.contains("\"limitations\":[\""));
    }

    #[test]
    fn no_pass_verdict_is_ever_reported() {
        let (line, _code) = report_bundle(Path::new("/nonexistent-bundle-xyz"));
        assert!(!line.contains("\"final_verdict\":\"PASS\""));
    }
}
