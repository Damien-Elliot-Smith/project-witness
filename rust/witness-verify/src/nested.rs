//! Nested evidence integrity (Rust port of the Python RT-004 deep layer).
//!
//! Mirrors src/12_companion_cli_v031/companion_lib/deep_checksums.py:
//!
//! 1. Nested checksum files: every file whose name ends in
//!    `checksums.txt` anywhere under the bundle (except the top-level
//!    companion_checksums.txt, already verified by hashes.rs) is parsed and
//!    every entry it lists is re-hashed. Two line formats are accepted:
//!        <sha256-hex>  <relative-path>              (standard)
//!        <label>  <sha256-hex>  <relative-path>     (Sentinel case)
//!    Listed paths resolve relative to the checksum file's own directory
//!    and must stay inside it. A labeled entry whose file is not a sibling
//!    is bound against coordinator_output/sentinel_run/<name> when that
//!    file exists, and is otherwise a recorded provenance hash that cannot
//!    be re-verified here (skipped, exactly as Python does).
//! 2. Aletheia manifest binding: evidence_manifest.json's
//!    bundled_file_sha256 must match the declared bundled file. This
//!    catches the fix-up attack that rewrites both evidence bytes and the
//!    checksum entry but not the manifest.
//! 3. Evidence directory completeness: every file under
//!    aletheia_bundle/evidence/ must be listed in evidence_checksums.txt.
//!
//! The walk order matches Python's os.walk with sorted dirs and files
//! (a directory's files first, then its subdirectories), so the first
//! reported failure is the same one Python reports.
//!
//! Depth honesty: these passes prove hash consistency of the recorded run
//! only. They do not prove evidence contents are true, and whole-bundle
//! fabrication remains possible without signing. Passing this stage does
//! NOT make a bundle valid; the verdict stays INCONCLUSIVE.

use std::fs;
use std::path::{Path, PathBuf};

use crate::json;
use crate::sha256;

pub type Failure = (String, String);

const TOP_LEVEL_CHECKSUMS: &str = "companion_checksums.txt";
const ALETHEIA_BUNDLE: [&str; 2] = ["coordinator_output", "aletheia_bundle"];
const SENTINEL_RUN_DIR: [&str; 2] = ["coordinator_output", "sentinel_run"];

/// Counts of what the nested stage actually checked.
#[derive(Debug, PartialEq)]
pub struct NestedSummary {
    pub nested_files: usize,
    pub entries_verified: usize,
    pub manifest_binding_checked: bool,
    pub evidence_files: usize,
}

fn fail(code: &str, detail: String) -> Failure {
    (code.to_string(), detail)
}

fn is_hex64_lower(s: &str) -> bool {
    s.len() == 64
        && s.chars().all(|c| c.is_ascii_digit() || ('a'..='f').contains(&c))
}

/// Line split matching Python str.splitlines() for \n, \r\n and \r.
fn split_lines(text: &str) -> Vec<&str> {
    let mut out = Vec::new();
    let bytes = text.as_bytes();
    let mut start = 0;
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'\n' || bytes[i] == b'\r' {
            out.push(&text[start..i]);
            if bytes[i] == b'\r' && i + 1 < bytes.len() && bytes[i + 1] == b'\n'
            {
                i += 1;
            }
            start = i + 1;
        }
        i += 1;
    }
    if start < bytes.len() {
        out.push(&text[start..]);
    }
    out
}

fn read_utf8(path: &Path, rel: &str) -> Result<String, Failure> {
    let data = fs::read(path).map_err(|err| {
        fail("NESTED_READ_ERROR", format!("could not read {}: {}", rel, err))
    })?;
    String::from_utf8(data).map_err(|_| {
        fail(
            "NESTED_CHECKSUMS_MALFORMED",
            format!("{} is not valid UTF-8", rel),
        )
    })
}

fn hash_file(path: &Path, rel: &str) -> Result<String, Failure> {
    sha256::digest_file(path).map_err(|err| {
        fail(
            "NESTED_READ_ERROR",
            format!("could not read {} for hashing: {}", rel, err),
        )
    })
}

/// Parse a 2- or 3-field checksum line into (digest, rel_path, labeled).
fn parse_line<'a>(
    raw_line: &'a str,
    source_rel: &str,
) -> Result<(&'a str, &'a str, bool), Failure> {
    let parts: Vec<&str> = raw_line.split("  ").collect();
    let (digest, rel, labeled) = match parts.len() {
        2 => (parts[0], parts[1], false),
        3 => (parts[1], parts[2], true),
        _ => {
            return Err(fail(
                "NESTED_CHECKSUMS_MALFORMED",
                format!("malformed line in {}: {:?}", source_rel, raw_line),
            ))
        }
    };
    if !is_hex64_lower(digest) {
        return Err(fail(
            "NESTED_CHECKSUMS_MALFORMED",
            format!("malformed digest in {}: {:?}", source_rel, digest),
        ));
    }
    Ok((digest, rel, labeled))
}

/// Canonicalize the deepest existing ancestor of `path` (inclusive).
fn resolve_existing(path: &Path) -> Option<PathBuf> {
    let mut cur = Some(path);
    while let Some(p) = cur {
        if fs::symlink_metadata(p).is_ok() {
            return fs::canonicalize(p).ok();
        }
        cur = p.parent();
    }
    None
}

/// Join rel onto base_dir, refusing traversal, absolute and unsafe paths,
/// and anything that resolves (through symlinks) outside base_dir.
fn safe_join(base_dir: &Path, rel: &str) -> Result<PathBuf, Failure> {
    let unsafe_path = |why: &str| {
        Err(fail(
            "NESTED_PATH_UNSAFE",
            format!("{} in checksum entry: {:?}", why, rel),
        ))
    };
    if rel.is_empty() {
        return unsafe_path("empty path");
    }
    if rel.contains('\\') {
        return unsafe_path("backslash path");
    }
    if rel.starts_with('/') {
        return unsafe_path("absolute path");
    }
    let parts: Vec<&str> = rel.split('/').collect();
    if parts.iter().any(|p| p.is_empty()) {
        return unsafe_path("empty path segment");
    }
    if parts.iter().any(|p| *p == "..") {
        return unsafe_path("path traversal");
    }
    let mut joined = base_dir.to_path_buf();
    for part in &parts {
        joined.push(part);
    }
    let real_base = fs::canonicalize(base_dir).map_err(|err| {
        fail(
            "NESTED_READ_ERROR",
            format!("could not resolve {}: {}", base_dir.display(), err),
        )
    })?;
    if let Some(real_joined) = resolve_existing(&joined) {
        if !real_joined.starts_with(&real_base) {
            return unsafe_path("entry escapes its directory");
        }
    }
    Ok(joined)
}

/// Relative path of `path` under `root`, '/'-separated.
fn rel_string(root: &Path, path: &Path) -> String {
    let rel = path.strip_prefix(root).unwrap_or(path);
    rel.components()
        .map(|c| c.as_os_str().to_string_lossy().into_owned())
        .collect::<Vec<_>>()
        .join("/")
}

/// Walk like Python os.walk(top) with sorted dirs and files: yields regular
/// (and symlink-to-non-directory) file paths, a directory's files before its
/// subdirectories. Directory symlinks are not followed.
fn walk_files(dir: &Path, out: &mut Vec<PathBuf>) -> Result<(), Failure> {
    let entries = fs::read_dir(dir).map_err(|err| {
        fail(
            "NESTED_READ_ERROR",
            format!("could not list {}: {}", dir.display(), err),
        )
    })?;
    let mut files: Vec<PathBuf> = Vec::new();
    let mut dirs: Vec<PathBuf> = Vec::new();
    for entry in entries {
        let entry = entry.map_err(|err| {
            fail(
                "NESTED_READ_ERROR",
                format!("could not list {}: {}", dir.display(), err),
            )
        })?;
        let path = entry.path();
        let ft = entry.file_type().map_err(|err| {
            fail(
                "NESTED_READ_ERROR",
                format!("could not stat {}: {}", path.display(), err),
            )
        })?;
        if ft.is_dir() {
            dirs.push(path);
        } else if ft.is_symlink() && path.is_dir() {
            // os.walk lists it as a directory and does not descend
        } else {
            files.push(path);
        }
    }
    files.sort();
    dirs.sort();
    out.extend(files);
    for d in dirs {
        walk_files(&d, out)?;
    }
    Ok(())
}

/// Deterministic list of nested checksum files, relative to the bundle.
pub fn find_nested_checksum_files(bundle: &Path) -> Result<Vec<String>, Failure> {
    let mut all = Vec::new();
    walk_files(bundle, &mut all)?;
    Ok(all
        .iter()
        .filter(|p| {
            p.file_name()
                .map(|n| n.to_string_lossy().ends_with("checksums.txt"))
                .unwrap_or(false)
        })
        .map(|p| rel_string(bundle, p))
        .filter(|rel| rel != TOP_LEVEL_CHECKSUMS)
        .collect())
}

/// The Coordinator's documented case_manifest replacement: the listed
/// digest must match the preserved raw manifest exactly, and the summary
/// must declare the preservation.
fn raw_manifest_fallback(base_dir: &Path, entry_rel: &str, digest: &str) -> bool {
    if entry_rel != "case_manifest.json" {
        return false;
    }
    let summary_path = base_dir.join("case_manifest.json");
    let raw_path = base_dir.join("raw_case_bundle_manifest.json");
    if !(summary_path.is_file() && raw_path.is_file()) {
        return false;
    }
    let text = match fs::read(&summary_path).ok().and_then(|b| String::from_utf8(b).ok()) {
        Some(t) => t,
        None => return false,
    };
    let summary = match json::parse(&text) {
        Ok(v) => v,
        Err(_) => return false,
    };
    if !summary.is_object() {
        return false;
    }
    if !matches!(
        summary.get("raw_case_bundle_manifest_preserved"),
        Some(json::Value::Bool(true))
    ) {
        return false;
    }
    if summary.get("raw_case_bundle_manifest").and_then(|v| v.as_str())
        != Some("raw_case_bundle_manifest.json")
    {
        return false;
    }
    matches!(sha256::digest_file(&raw_path), Ok(h) if h == digest)
}

/// Verify every entry of every nested checksum file.
/// Returns (nested checksum files, entries verified).
pub fn verify_nested_checksums(bundle: &Path) -> Result<(usize, usize), Failure> {
    let files = find_nested_checksum_files(bundle)?;
    let mut checked = 0;
    for rel in &files {
        let source_path = bundle.join(rel);
        let base_dir = source_path.parent().unwrap_or(bundle).to_path_buf();
        let text = read_utf8(&source_path, rel)?;
        let mut seen: Vec<&str> = Vec::new();
        for raw_line in split_lines(&text) {
            if raw_line.trim().is_empty() {
                continue;
            }
            let (digest, entry_rel, labeled) = parse_line(raw_line, rel)?;
            if seen.contains(&entry_rel) {
                return Err(fail(
                    "NESTED_CHECKSUMS_MALFORMED",
                    format!("duplicate entry in {}: {:?}", rel, entry_rel),
                ));
            }
            seen.push(entry_rel);
            let target = safe_join(&base_dir, entry_rel)?;
            if !target.is_file() {
                if labeled {
                    let mut source_run = bundle.to_path_buf();
                    for part in SENTINEL_RUN_DIR.iter() {
                        source_run.push(part);
                    }
                    if source_run.is_dir() {
                        let bound = safe_join(&source_run, entry_rel)?;
                        if bound.is_file() {
                            if hash_file(&bound, entry_rel)? != digest {
                                return Err(fail(
                                    "SOURCE_RUN_HASH_MISMATCH",
                                    format!(
                                        "recorded source hash in {} does not \
                                         match {:?}",
                                        rel, entry_rel
                                    ),
                                ));
                            }
                            checked += 1;
                        }
                    }
                    // recorded provenance hash only; cannot be re-verified
                    continue;
                }
                return Err(fail(
                    "NESTED_FILE_MISSING",
                    format!("file listed in {} is missing: {:?}", rel, entry_rel),
                ));
            }
            if hash_file(&target, entry_rel)? != digest
                && !raw_manifest_fallback(&base_dir, entry_rel, digest)
            {
                return Err(fail(
                    "NESTED_CHECKSUM_MISMATCH",
                    format!(
                        "deep checksum mismatch for {:?} (listed in {})",
                        entry_rel, rel
                    ),
                ));
            }
            checked += 1;
        }
    }
    Ok((files.len(), checked))
}

fn aletheia_dir(bundle: &Path) -> PathBuf {
    let mut dir = bundle.to_path_buf();
    for part in ALETHEIA_BUNDLE.iter() {
        dir.push(part);
    }
    dir
}

/// Verify evidence_manifest.json's bundled_file_sha256 against the file.
/// Ok(false) when the manifest is absent or declares no bundled-file hash.
pub fn verify_aletheia_manifest_binding(bundle: &Path) -> Result<bool, Failure> {
    let bundle_dir = aletheia_dir(bundle);
    let manifest_path = bundle_dir.join("evidence_manifest.json");
    if !manifest_path.is_file() {
        return Ok(false);
    }
    let malformed = |why: &str| {
        Err(fail(
            "MANIFEST_BINDING_MALFORMED",
            format!("evidence_manifest.json: {}", why),
        ))
    };
    let text = match fs::read(&manifest_path).map(String::from_utf8) {
        Ok(Ok(t)) => t,
        Ok(Err(_)) => return malformed("not valid UTF-8"),
        Err(err) => {
            return Err(fail(
                "NESTED_READ_ERROR",
                format!("could not read evidence_manifest.json: {}", err),
            ))
        }
    };
    let manifest = match json::parse(&text) {
        Ok(v) => v,
        Err(_) => return malformed("not valid JSON"),
    };
    if !manifest.is_object() {
        return malformed("not a JSON object");
    }
    let declared = match manifest.get("bundled_file_sha256") {
        None | Some(json::Value::Null) => return Ok(false),
        Some(v) => v,
    };
    let declared = match declared.as_str() {
        Some(s) if is_hex64_lower(s) => s,
        _ => return malformed("malformed bundled_file_sha256"),
    };
    let bundled_rel = match manifest.get("bundled_file_path").and_then(|v| v.as_str()) {
        Some(s) if !s.is_empty() => s,
        _ => return malformed("bundled_file_sha256 declared without bundled_file_path"),
    };
    let target = safe_join(&bundle_dir, bundled_rel)?;
    if !target.is_file() {
        return Err(fail(
            "MANIFEST_BINDING_FILE_MISSING",
            format!(
                "bundled file declared in evidence_manifest.json is missing: {:?}",
                bundled_rel
            ),
        ));
    }
    if hash_file(&target, bundled_rel)? != declared {
        return Err(fail(
            "MANIFEST_BINDING_MISMATCH",
            format!(
                "manifest bundled_file_sha256 does not match bundled file {:?}",
                bundled_rel
            ),
        ));
    }
    Ok(true)
}

/// Fail if the Aletheia evidence directory holds files not listed in
/// evidence_checksums.txt. Returns the number of evidence files present.
pub fn verify_evidence_dir_completeness(bundle: &Path) -> Result<usize, Failure> {
    let bundle_dir = aletheia_dir(bundle);
    let sums_path = bundle_dir.join("evidence_checksums.txt");
    let evidence_dir = bundle_dir.join("evidence");
    if !(sums_path.is_file() && evidence_dir.is_dir()) {
        return Ok(0);
    }
    let text = read_utf8(&sums_path, "evidence_checksums.txt")?;
    let mut listed: Vec<&str> = Vec::new();
    for raw_line in split_lines(&text) {
        if raw_line.trim().is_empty() {
            continue;
        }
        let (_digest, entry_rel, _labeled) =
            parse_line(raw_line, "evidence_checksums.txt")?;
        if let Some(rest) = entry_rel.strip_prefix("evidence/") {
            listed.push(rest);
        }
    }
    let mut actual = Vec::new();
    walk_files(&evidence_dir, &mut actual)?;
    let mut unlisted: Vec<String> = actual
        .iter()
        .map(|p| rel_string(&evidence_dir, p))
        .filter(|rel| !listed.contains(&rel.as_str()))
        .collect();
    unlisted.sort();
    if !unlisted.is_empty() {
        unlisted.truncate(5);
        return Err(fail(
            "EVIDENCE_DIR_UNLISTED_FILE",
            format!("unlisted file(s) in evidence directory: {:?}", unlisted),
        ));
    }
    Ok(actual.len())
}

/// Run all nested passes in the Python order.
pub fn verify_nested(bundle: &Path) -> Result<NestedSummary, Failure> {
    let (nested_files, entries_verified) = verify_nested_checksums(bundle)?;
    let manifest_binding_checked = verify_aletheia_manifest_binding(bundle)?;
    let evidence_files = verify_evidence_dir_completeness(bundle)?;
    Ok(NestedSummary {
        nested_files,
        entries_verified,
        manifest_binding_checked,
        evidence_files,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    fn reference_bundle() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../freeze_record/python_behaviour_freeze_v01/reference_bundle")
    }

    fn copy_tree(src: &Path, dst: &Path) {
        fs::create_dir_all(dst).unwrap();
        for entry in fs::read_dir(src).unwrap() {
            let entry = entry.unwrap();
            let to = dst.join(entry.file_name());
            if entry.file_type().unwrap().is_dir() {
                copy_tree(&entry.path(), &to);
            } else {
                fs::copy(entry.path(), &to).unwrap();
            }
        }
    }

    /// A private copy of the frozen Move 71 reference bundle.
    fn reference_copy(name: &str) -> PathBuf {
        static SEQ: AtomicUsize = AtomicUsize::new(0);
        let mut dir = std::env::temp_dir();
        dir.push(format!(
            "wv_nested_{}_{}_{}",
            std::process::id(),
            SEQ.fetch_add(1, Ordering::SeqCst),
            name
        ));
        let _ = fs::remove_dir_all(&dir);
        copy_tree(&reference_bundle(), &dir);
        dir
    }

    const EVIDENCE: &str = "coordinator_output/aletheia_bundle/evidence/evidence_001.bin";
    const EVIDENCE_SUMS: &str = "coordinator_output/aletheia_bundle/evidence_checksums.txt";

    fn code_of(dir: &Path) -> String {
        let result = verify_nested(dir);
        fs::remove_dir_all(dir).ok();
        match result {
            Ok(_) => "OK".to_string(),
            Err((code, _)) => code,
        }
    }

    fn flip_byte(path: &Path) {
        let mut data = fs::read(path).unwrap();
        data[5] ^= 0xFF;
        fs::write(path, data).unwrap();
    }

    #[test]
    fn reference_bundle_passes_every_nested_check() {
        let dir = reference_copy("clean");
        let summary = verify_nested(&dir);
        fs::remove_dir_all(&dir).ok();
        let summary = summary.expect("clean reference must pass");
        assert_eq!(summary.nested_files, 11);
        assert!(summary.manifest_binding_checked);
        assert_eq!(summary.evidence_files, 1);
        assert!(summary.entries_verified > 0);
    }

    #[test]
    fn appended_byte_in_nested_evidence_fails() {
        // the exact tamper from the 2026-10-12 evaluation
        let dir = reference_copy("append");
        let mut data = fs::read(dir.join(EVIDENCE)).unwrap();
        data.push(b'x');
        fs::write(dir.join(EVIDENCE), data).unwrap();
        assert_eq!(code_of(&dir), "NESTED_CHECKSUM_MISMATCH");
    }

    #[test]
    fn corpus_evidence_byte_flip_fails() {
        let dir = reference_copy("flip");
        flip_byte(&dir.join(EVIDENCE));
        assert_eq!(code_of(&dir), "NESTED_CHECKSUM_MISMATCH");
    }

    #[test]
    fn corpus_flip_with_checksum_fixup_hits_manifest_binding() {
        let dir = reference_copy("fixup");
        flip_byte(&dir.join(EVIDENCE));
        let new_digest = sha256::digest_file(&dir.join(EVIDENCE)).unwrap();
        let text = fs::read_to_string(dir.join(EVIDENCE_SUMS)).unwrap();
        let fixed: Vec<String> = text
            .lines()
            .map(|l| {
                if l.ends_with("evidence/evidence_001.bin") {
                    format!("{}  evidence/evidence_001.bin", new_digest)
                } else {
                    l.to_string()
                }
            })
            .collect();
        fs::write(dir.join(EVIDENCE_SUMS), fixed.join("\n") + "\n").unwrap();
        assert_eq!(code_of(&dir), "MANIFEST_BINDING_MISMATCH");
    }

    #[test]
    fn corpus_evidence_added_unexpectedly_fails() {
        let dir = reference_copy("planted");
        fs::write(
            dir.join("coordinator_output/aletheia_bundle/evidence/planted_evidence.bin"),
            b"planted\n",
        )
        .unwrap();
        assert_eq!(code_of(&dir), "EVIDENCE_DIR_UNLISTED_FILE");
    }

    #[test]
    fn corpus_delete_nested_listed_file_fails() {
        let dir = reference_copy("deleted");
        fs::remove_file(dir.join("coordinator_output/bridge_output/odin_claims.json")).unwrap();
        assert_eq!(code_of(&dir), "NESTED_FILE_MISSING");
    }

    #[test]
    fn corpus_tamper_source_run_fails() {
        let dir = reference_copy("source_run");
        let path = dir.join("coordinator_output/sentinel_run/sentinel_run.json");
        let mut data = fs::read(&path).unwrap();
        data.push(b' ');
        fs::write(&path, data).unwrap();
        assert_eq!(code_of(&dir), "SOURCE_RUN_HASH_MISMATCH");
    }

    #[test]
    fn traversal_entry_is_rejected() {
        let dir = reference_copy("traversal");
        let sums = dir.join(EVIDENCE_SUMS);
        let mut text = fs::read_to_string(&sums).unwrap();
        text.push_str(&format!("{}  ../outside.txt\n", "a".repeat(64)));
        fs::write(&sums, text).unwrap();
        assert_eq!(code_of(&dir), "NESTED_PATH_UNSAFE");
    }

    #[test]
    fn uppercase_digest_is_rejected() {
        let dir = reference_copy("upper");
        let sums = dir.join(EVIDENCE_SUMS);
        let text = fs::read_to_string(&sums).unwrap().to_uppercase();
        fs::write(&sums, text.replace("EVIDENCE", "evidence")).unwrap();
        assert_eq!(code_of(&dir), "NESTED_CHECKSUMS_MALFORMED");
    }

    #[test]
    fn duplicate_entry_is_rejected() {
        let dir = reference_copy("dup");
        let sums = dir.join(EVIDENCE_SUMS);
        let text = fs::read_to_string(&sums).unwrap();
        let first = text.lines().next().unwrap().to_string();
        fs::write(&sums, format!("{}{}\n", text, first)).unwrap();
        assert_eq!(code_of(&dir), "NESTED_CHECKSUMS_MALFORMED");
    }

    #[test]
    fn split_lines_matches_python_for_common_endings() {
        assert_eq!(split_lines("a\nb\r\nc\rd"), vec!["a", "b", "c", "d"]);
        assert_eq!(split_lines("a\n"), vec!["a"]);
        assert!(split_lines("").is_empty());
    }
}
