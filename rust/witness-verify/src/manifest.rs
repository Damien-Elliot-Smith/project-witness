//! Move 74: case manifest structural validator.
//!
//! Mirrors the STRUCTURAL layer of the Python verifier
//! (src/12_companion_cli_v031/companion_lib/verifier.py) against the
//! adopted Move 71 behavioural reference:
//!   - required top-level files present
//!   - no unknown top-level entries (critical unknown handling)
//!   - companion_report.json parses as a JSON object
//!   - schema versions pinned to 0.3.0
//!   - all nineteen reference report fields present, none unknown
//!   - referenced paths exist (existence ONLY - hashing is Step 75)
//!
//! Honesty boundary: structural validity NEVER yields PASS here. The
//! caller maps Ok(()) to INCONCLUSIVE because hash verification,
//! receipt chains, and deep checks are not implemented yet.

use std::fs;
use std::path::Path;

use crate::json;

pub const MANIFEST_FILE: &str = "companion_report.json";
pub const CHECKSUMS_FILE: &str = "companion_checksums.txt";

const REQUIRED_TOP_FILES: [&str; 4] = [
    "workflow_request.json",
    "companion_report.json",
    "companion_steps.json",
    "companion_checksums.txt",
];

const ALLOWED_TOP_LEVEL: [&str; 5] = [
    "workflow_request.json",
    "companion_report.json",
    "companion_steps.json",
    "companion_checksums.txt",
    "coordinator_output",
];

/// The nineteen top-level fields of the frozen reference report. At
/// schema 0.3.0 the required set and the allowed set are identical.
/// NOTE: the SET of entries below is validated against the frozen
/// reference bundle by executable checks (grounding check at
/// authoring; alignment guard in tools/check_rust_workspace.sh). The
/// COUNT has its own history: it was narrated as sixteen, then
/// seventeen, across three review rounds while the true computed
/// count is nineteen; rustc's fixed-length array check was the first
/// mechanical counter in the chain and failed the v2 Termux build
/// correctly. Never narrate this count - compute it.
const REPORT_FIELDS: [&str; 19] = [
    "action_type",
    "aletheia_status",
    "atlas_registry_status",
    "atlas_validation_status",
    "bridge_status",
    "case_bundle_status",
    "case_id",
    "command",
    "companion_cli_version",
    "companion_status",
    "coordinator_output_path",
    "coordinator_workflow_status",
    "coordinator_workflow_version",
    "evidence_id",
    "known_limitations",
    "odin_reasoning_status",
    "requested_case_id",
    "sentinel_status",
    "workflow_type",
];

const SCHEMA_VERSION: &str = "0.3.0";

/// A structural failure: (reason_code, detail).
pub type Failure = (String, String);

fn fail(code: &str, detail: String) -> Failure {
    (code.to_string(), detail)
}

/// Validate the manifest layer of a bundle directory. Read-only.
pub fn validate(bundle: &Path) -> Result<(), Failure> {
    check_required_top_files(bundle)?;
    check_no_unknown_top_level(bundle)?;
    let report = load_report(bundle)?;
    check_schema_versions(&report)?;
    check_report_fields(&report)?;
    check_referenced_paths(bundle, &report)?;
    Ok(())
}

fn check_required_top_files(bundle: &Path) -> Result<(), Failure> {
    for name in REQUIRED_TOP_FILES.iter() {
        let path = bundle.join(name);
        if !path.is_file() {
            if *name == MANIFEST_FILE {
                return Err(fail(
                    "MANIFEST_MISSING",
                    format!("{} is missing", name),
                ));
            }
            return Err(fail(
                "REQUIRED_FILE_MISSING",
                format!("required top-level file missing: {}", name),
            ));
        }
    }
    Ok(())
}

fn check_no_unknown_top_level(bundle: &Path) -> Result<(), Failure> {
    let entries = match fs::read_dir(bundle) {
        Ok(entries) => entries,
        Err(err) => {
            return Err(fail(
                "BUNDLE_READ_ERROR",
                format!("could not list bundle directory: {}", err),
            ));
        }
    };
    let mut names: Vec<String> = Vec::new();
    for entry in entries {
        match entry {
            Ok(item) => {
                names.push(item.file_name().to_string_lossy().to_string());
            }
            Err(err) => {
                return Err(fail(
                    "BUNDLE_READ_ERROR",
                    format!("could not read directory entry: {}", err),
                ));
            }
        }
    }
    names.sort();
    for name in names {
        if !ALLOWED_TOP_LEVEL.contains(&name.as_str()) {
            return Err(fail(
                "CRITICAL_UNKNOWN_TOP_LEVEL_ENTRY",
                format!("unknown top-level entry: {}", name),
            ));
        }
    }
    Ok(())
}

fn load_report(bundle: &Path) -> Result<json::Value, Failure> {
    let path = bundle.join(MANIFEST_FILE);
    let text = match fs::read_to_string(&path) {
        Ok(text) => text,
        Err(err) => {
            return Err(fail(
                "MANIFEST_READ_ERROR",
                format!("could not read {}: {}", MANIFEST_FILE, err),
            ));
        }
    };
    let value = match json::parse(&text) {
        Ok(value) => value,
        Err(err) => {
            return Err(fail(
                "MANIFEST_JSON_INVALID",
                format!("{}: {}", MANIFEST_FILE, err),
            ));
        }
    };
    if !value.is_object() {
        return Err(fail(
            "MANIFEST_NOT_AN_OBJECT",
            format!("{} is not a JSON object", MANIFEST_FILE),
        ));
    }
    Ok(value)
}

fn check_schema_versions(report: &json::Value) -> Result<(), Failure> {
    for field in ["companion_cli_version", "coordinator_workflow_version"] {
        match report.get(field).and_then(|v| v.as_str()) {
            Some(version) => {
                if version != SCHEMA_VERSION {
                    return Err(fail(
                        "SCHEMA_VERSION_UNSUPPORTED",
                        format!(
                            "{} is {:?}, supported: {:?}",
                            field, version, SCHEMA_VERSION
                        ),
                    ));
                }
            }
            None => {
                return Err(fail(
                    "SCHEMA_VERSION_UNSUPPORTED",
                    format!("{} missing or not a string", field),
                ));
            }
        }
    }
    Ok(())
}

fn check_report_fields(report: &json::Value) -> Result<(), Failure> {
    for field in REPORT_FIELDS.iter() {
        if report.get(field).is_none() {
            return Err(fail(
                "REQUIRED_FIELD_MISSING",
                format!("report field missing: {}", field),
            ));
        }
    }
    for key in report.object_keys() {
        if !REPORT_FIELDS.contains(&key.as_str()) {
            return Err(fail(
                "CRITICAL_UNKNOWN_FIELD",
                format!("unknown report field: {}", key),
            ));
        }
    }
    Ok(())
}

fn check_referenced_paths(
    bundle: &Path,
    report: &json::Value,
) -> Result<(), Failure> {
    let coord = match report
        .get("coordinator_output_path")
        .and_then(|v| v.as_str())
    {
        Some(value) => value,
        None => {
            return Err(fail(
                "REQUIRED_FIELD_MISSING",
                "coordinator_output_path missing or not a string".to_string(),
            ));
        }
    };
    if coord.starts_with('/') || coord.contains("..") || coord.contains('\\')
    {
        return Err(fail(
            "REFERENCED_PATH_UNSAFE",
            format!("coordinator_output_path is unsafe: {:?}", coord),
        ));
    }
    if !bundle.join(coord).is_dir() {
        return Err(fail(
            "REFERENCED_PATH_MISSING",
            format!("coordinator_output_path not found: {:?}", coord),
        ));
    }
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
        let rel = parts[1];
        if rel.is_empty()
            || rel.starts_with('/')
            || rel.contains("..")
            || rel.contains('\\')
        {
            return Err(fail(
                "CHECKSUMS_PATH_UNSAFE",
                format!("unsafe path in checksums: {:?}", rel),
            ));
        }
        if !bundle.join(rel).is_file() {
            return Err(fail(
                "REFERENCED_FILE_MISSING",
                format!("file listed in checksums missing: {}", rel),
            ));
        }
    }
    Ok(())
}
