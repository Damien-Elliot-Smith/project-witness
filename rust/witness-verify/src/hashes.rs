//! Move 75: file hash verification.
//!
//! Verifies every hash declared in companion_checksums.txt by
//! recomputing SHA-256, and requires the eight REQUIRED_HASH_PATHS
//! (mirroring the Python checksums.REQUIRED_PATHS contract, validated
//! computationally against the frozen reference by the alignment guard)
//! to be declared - an undeclared critical file is a failure.
//!
//! Depth honesty: this verifies TOP-LEVEL declared hashes only. Nested
//! component checksum files, the Aletheia manifest binding, and the
//! Sentinel source-run binding (the Python RT-004 deep-verification
//! layer) are NOT implemented here yet. A bundle passing this stage is
//! therefore still INCONCLUSIVE - claiming otherwise would recreate in
//! Rust the exact depth illusion RT-004 repaired in Python.

use std::fs;
use std::path::Path;

use crate::sha256;

/// Mirror of Python companion_lib/checksums.py REQUIRED_PATHS.
pub const REQUIRED_HASH_PATHS: [&str; 8] = [
    "workflow_request.json",
    "companion_report.json",
    "companion_steps.json",
    "coordinator_output/workflow_report.json",
    "coordinator_output/workflow_steps.json",
    "coordinator_output/atlas_validation_report.json",
    "coordinator_output/atlas_registry_copy.json",
    "coordinator_output/case_bundle_v02/case_manifest.json",
];

const CHECKSUMS_FILE: &str = "companion_checksums.txt";

pub type Failure = (String, String);

fn fail(code: &str, detail: String) -> Failure {
    (code.to_string(), detail)
}

fn is_hex64_lower(s: &str) -> bool {
    if s.len() != 64 {
        return false;
    }
    for c in s.chars() {
        let ok = c.is_ascii_digit() || ('a'..='f').contains(&c);
        if !ok {
            return false;
        }
    }
    true
}

/// Verify all declared hashes and required-path coverage.
/// Returns the number of files whose hashes were verified.
pub fn verify_declared_hashes(bundle: &Path) -> Result<usize, Failure> {
    let sums_path = bundle.join(CHECKSUMS_FILE);
    let text = match fs::read_to_string(&sums_path) {
        Ok(text) => text,
        Err(err) => {
            return Err(fail(
                "MANIFEST_READ_ERROR",
                format!("could not read {}: {}", CHECKSUMS_FILE, err),
            ));
        }
    };

    let mut declared: Vec<String> = Vec::new();
    let mut verified: usize = 0;

    for raw_line in text.lines() {
        if raw_line.trim().is_empty() {
            continue;
        }
        let parts: Vec<&str> = raw_line.split("  ").collect();
        if parts.len() != 2 {
            return Err(fail(
                "MALFORMED_CHECKSUMS_LINE",
                format!("expected '<digest>  <relpath>': {:?}", raw_line),
            ));
        }
        let digest = parts[0];
        let rel = parts[1];
        if !is_hex64_lower(digest) {
            return Err(fail(
                "MALFORMED_DIGEST",
                format!("not 64 lowercase hex chars for {}: {:?}", rel, digest),
            ));
        }
        // path safety and existence were already enforced by the
        // manifest stage; re-check existence defensively anyway
        let target = bundle.join(rel);
        if !target.is_file() {
            return Err(fail(
                "REFERENCED_FILE_MISSING",
                format!("file listed in checksums missing: {}", rel),
            ));
        }
        let actual = match sha256::digest_file(&target) {
            Ok(hex) => hex,
            Err(err) => {
                return Err(fail(
                    "HASH_READ_ERROR",
                    format!("could not read {} for hashing: {}", rel, err),
                ));
            }
        };
        if actual != digest {
            return Err(fail(
                "FILE_HASH_MISMATCH",
                format!("recomputed hash does not match declared for {}", rel),
            ));
        }
        declared.push(rel.to_string());
        verified += 1;
    }

    for required in REQUIRED_HASH_PATHS.iter() {
        if !declared.iter().any(|d| d == required) {
            return Err(fail(
                "REQUIRED_PATH_UNDECLARED",
                format!(
                    "critical file has no declared hash: {}",
                    required
                ),
            ));
        }
    }

    Ok(verified)
}
