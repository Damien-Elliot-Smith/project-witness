//! witness-verify: read-only Rust verification spine (Part Two).
//!
//! Step 78 state: the CLI validates the manifest layer (Move 74),
//! top-level declared file hashes (Move 75), the receipt chain by
//! declared values and recomputed canonical hashes (Moves 76-77), and
//! inspects ZIP archives for extraction-time safety (Move 78). Manifest
//! and seal hash recomputation, nested component checksums, and manifest
//! bindings are NOT implemented.
//!
//! HONESTY PROPERTY: no code path can emit a PASS verdict. Every
//! successful stage yields INCONCLUSIVE with a stage-specific reason,
//! because no single stage makes a bundle or archive valid. Exit 0
//! remains reserved and unreachable.
//!
//! Output contract: one JSON object on stdout, one line:
//!   {"verifier": "witness-verify", "version": ..., "verdict": ...,
//!    "reason_code": ..., "detail": ...}
//! Verdicts: FAIL | INCONCLUSIVE. Exit codes: 1 FAIL, 2 usage, 3
//! INCONCLUSIVE.

mod canonical;
mod hashes;
mod json;
mod manifest;
mod receipts;
mod report;
mod sha256;
mod zipguard;

use std::env;
use std::path::Path;
use std::process;

const VERSION: &str = "0.0.8-step79-diagnostics";

const VERDICT_FAIL: &str = "FAIL";
const VERDICT_INCONCLUSIVE: &str = "INCONCLUSIVE";

const EXIT_FAIL: i32 = 1;
const EXIT_USAGE: i32 = 2;
const EXIT_INCONCLUSIVE: i32 = 3;

/// Minimal JSON string escaping (stdlib only, no external crates).
fn json_escape(input: &str) -> String {
    let mut out = String::new();
    for c in input.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => out.push(c),
        }
    }
    out
}

/// Build the single-line controlled output object.
/// Move 79 (read-only diagnostic): same as verdict_line but appends a
/// structured numeric field. Adds NO check, changes NO verdict, NO reason
/// code, NO precedence and NO ordering — it only exposes a count the
/// inspector already computed, so the agreement harness never has to
/// parse free-text detail.
fn verdict_line_with_count(
    verdict: &str,
    reason_code: &str,
    detail: &str,
    entry_count: usize,
) -> String {
    format!(
        "{{\"verifier\": \"witness-verify\", \"version\": \"{}\", \
         \"verdict\": \"{}\", \"reason_code\": \"{}\", \"detail\": \"{}\", \
         \"entry_count\": {}}}",
        json_escape(VERSION),
        json_escape(verdict),
        json_escape(reason_code),
        json_escape(detail),
        entry_count
    )
}

fn verdict_line(verdict: &str, reason_code: &str, detail: &str) -> String {
    format!(
        "{{\"verifier\": \"witness-verify\", \"version\": \"{}\", \
         \"verdict\": \"{}\", \"reason_code\": \"{}\", \"detail\": \"{}\"}}",
        json_escape(VERSION),
        json_escape(verdict),
        json_escape(reason_code),
        json_escape(detail)
    )
}

/// Evaluate a bundle path. Read-only.
fn evaluate_bundle(path: &Path) -> (String, i32) {
    if !path.exists() {
        return (
            verdict_line(
                VERDICT_FAIL,
                "BUNDLE_PATH_MISSING",
                "bundle path does not exist",
            ),
            EXIT_FAIL,
        );
    }
    if !path.is_dir() {
        return (
            verdict_line(
                VERDICT_FAIL,
                "BUNDLE_PATH_NOT_A_DIRECTORY",
                "bundle path is not a directory",
            ),
            EXIT_FAIL,
        );
    }
    if let Err((code, detail)) = manifest::validate(path) {
        return (verdict_line(VERDICT_FAIL, &code, &detail), EXIT_FAIL);
    }
    let hash_count = match hashes::verify_declared_hashes(path) {
        Ok(count) => count,
        Err((code, detail)) => {
            return (verdict_line(VERDICT_FAIL, &code, &detail), EXIT_FAIL);
        }
    };
    match receipts::verify_receipt_chain(path) {
        Ok(receipt_count) => (
            verdict_line(
                VERDICT_INCONCLUSIVE,
                "RECEIPT_CHAIN_HASHES_RECOMPUTED",
                &format!(
                    "manifest structure valid, {} declared top-level hashes \
                     verified, and {}-receipt chain verified with per-receipt \
                     canonical hash RECOMPUTATION; manifest/seal hash \
                     recomputation, nested component checksums, manifest \
                     bindings and archive safety are not implemented yet, \
                     so the bundle cannot be declared valid",
                    hash_count, receipt_count
                ),
            ),
            EXIT_INCONCLUSIVE,
        ),
        Err((code, detail)) => {
            (verdict_line(VERDICT_FAIL, &code, &detail), EXIT_FAIL)
        }
    }
}

fn evaluate_archive(path: &Path) -> (String, i32) {
    match zipguard::inspect_archive(path) {
        Ok(count) => (
            verdict_line_with_count(
                VERDICT_INCONCLUSIVE,
                "ARCHIVE_SAFETY_OK",
                &format!(
                    "archive passed Move 78 safety checks ({} entries); \
                     this does NOT mean the bundle contents are valid",
                    count
                ),
                count,
            ),
            EXIT_INCONCLUSIVE,
        ),
        Err((code, detail)) => {
            (verdict_line(VERDICT_FAIL, &code, &detail), EXIT_FAIL)
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() == 3 && args[1] == "verify" {
        let path = Path::new(&args[2]);
        let (line, code) = evaluate_bundle(path);
        println!("{}", line);
        process::exit(code);
    }
    if args.len() == 3 && args[1] == "inspect-archive" {
        let path = Path::new(&args[2]);
        let (line, code) = evaluate_archive(path);
        println!("{}", line);
        process::exit(code);
    }
    // MOVE 83, strictly additive. Reached only when the two adopted
    // invocations above did not match, so their behaviour is unchanged.
    // The usage text below is deliberately NOT extended: it is part of
    // the adopted CLI contract whose exact stderr bytes are asserted by
    // the Move 82 gate.
    if args.len() == 3 && args[1] == "report-bundle" {
        let path = Path::new(&args[2]);
        let (line, code) = report::report_bundle(path);
        println!("{}", line);
        process::exit(code);
    }
    if args.len() == 3 && args[1] == "report-archive" {
        let path = Path::new(&args[2]);
        let (line, code) = report::report_archive(path);
        println!("{}", line);
        process::exit(code);
    }
    eprintln!("usage: witness-verify verify <bundle-dir>");
    eprintln!("       witness-verify inspect-archive <archive.zip>");
    println!(
        "{}",
        verdict_line(
            VERDICT_FAIL,
            "USAGE_ERROR",
            "expected: verify <bundle-dir> | inspect-archive <archive.zip>"
        )
    );
    process::exit(EXIT_USAGE);
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::{Path, PathBuf};

    const VALID_REPORT: &str = "{\
\"action_type\": \"CREATE_DIRECTORY\", \
\"aletheia_status\": \"VERIFIED_PRESENT\", \
\"atlas_registry_status\": \"REGISTRY_VERIFIED\", \
\"atlas_validation_status\": \"ATLAS_VALIDATED\", \
\"bridge_status\": \"CONVERTED\", \
\"case_bundle_status\": \"BUNDLED_VERIFIED_CASE\", \
\"case_id\": \"case_0000000000000000\", \
\"command\": \"create-evidence-case\", \
\"companion_cli_version\": \"0.3.0\", \
\"companion_status\": \"COMPANION_COMPLETED\", \
\"coordinator_output_path\": \"coordinator_output\", \
\"coordinator_workflow_status\": \"WORKFLOW_COMPLETED\", \
\"coordinator_workflow_version\": \"0.3.0\", \
\"evidence_id\": \"evidence_test\", \
\"known_limitations\": [\"test fixture\"], \
\"odin_reasoning_status\": \"CONSISTENT\", \
\"requested_case_id\": \"case_test\", \
\"sentinel_status\": \"PASS_STRICT\", \
\"workflow_type\": \"CREATE_EVIDENCE_REASONING_CASE\"}";

    fn temp_bundle(name: &str) -> PathBuf {
        let mut dir = std::env::temp_dir();
        dir.push(format!("wv74_{}_{}", std::process::id(), name));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn write(dir: &Path, rel: &str, content: &str) {
        fs::write(dir.join(rel), content).unwrap();
    }

    fn receipt_body(id: usize, prior: &str) -> String {
        let hm = "a".repeat(64);
        format!(
            r#"{{"action_schema_version": "1.1.0", "decision": "ALLOW", "detail": {{}}, "executed": false, "impl_version": "0.2.0", "intent_hash": null, "intent_receipt_id": null, "manifest_hash": "{}", "policy_version": "0.1.1", "post_session_state": "OPEN", "pre_session_state": "OPEN", "prior_hash": "{}", "reason_code": "TEST", "reason_registry_version": "0.1.0", "receipt_id": {}, "receipt_schema_version": "0.2.0", "request": {{}}, "run_id": "run_fixture", "session_version": "0.1.0", "stage": "INTENT"}}"#,
            hm, prior, id
        )
    }

    fn receipt_with_real_hash(id: usize, prior: &str) -> (String, String) {
        let body = receipt_body(id, prior);
        let payload = json::parse(&body).unwrap();
        let hash = canonical::canonical_hash_hex(&payload).unwrap();
        let with_hash = body.replacen(
            "{",
            &format!("{{\"canonical_hash\": \"{}\", ", hash),
            1,
        );
        (with_hash, hash)
    }

    fn sentinel_run_json() -> String {
        let hm = "a".repeat(64);
        let (r0, c0) = receipt_with_real_hash(0, "GENESIS");
        let (r1, c1) = receipt_with_real_hash(1, &c0);
        format!(
            r#"{{"manifest": {{"manifest_hash": "{}", "run_id": "run_fixture"}}, "receipts": [{}, {}], "run_seal": {{"final_receipt_hash": "{}", "final_receipt_id": 1, "final_session_state": "OPEN", "manifest_hash": "{}", "receipt_count": 2, "run_id": "run_fixture", "seal_hash": "{}", "seal_version": "0.1.0"}}}}"#,
            hm, r0, r1, c1, hm,
            "d".repeat(64)
        )
    }

    fn valid_bundle(name: &str) -> PathBuf {
        let dir = temp_bundle(name);
        fs::create_dir_all(
            dir.join("coordinator_output").join("case_bundle_v02"),
        )
        .unwrap();
        let mut sums = String::new();
        let contents: [(&str, &str); 8] = [
            ("workflow_request.json", "{}"),
            ("companion_report.json", VALID_REPORT),
            ("companion_steps.json", "{}"),
            ("coordinator_output/workflow_report.json", "{}"),
            ("coordinator_output/workflow_steps.json", "{}"),
            ("coordinator_output/atlas_validation_report.json", "{}"),
            ("coordinator_output/atlas_registry_copy.json", "{}"),
            (
                "coordinator_output/case_bundle_v02/case_manifest.json",
                "{}",
            ),
        ];
        for (rel, content) in contents.iter() {
            fs::write(dir.join(rel), content).unwrap();
            sums.push_str(&format!(
                "{}  {}\n",
                sha256::digest_hex(content.as_bytes()),
                rel
            ));
        }
        write(&dir, "companion_checksums.txt", &sums);
        fs::create_dir_all(
            dir.join("coordinator_output").join("sentinel_run"),
        )
        .unwrap();
        write(
            &dir,
            "coordinator_output/sentinel_run/sentinel_run.json",
            &sentinel_run_json(),
        );
        dir
    }

    #[test]
    fn version_marks_step79() {
        assert!(VERSION.contains("step79-diagnostics"));
    }

    #[test]
    fn valid_bundle_full_chain_is_inconclusive_never_pass() {
        let dir = valid_bundle("valid");
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("\"verdict\": \"INCONCLUSIVE\""));
        assert!(line.contains("RECEIPT_CHAIN_HASHES_RECOMPUTED"));
        assert_eq!(code, EXIT_INCONCLUSIVE);
    }

    #[test]
    fn missing_manifest_fails() {
        let dir = valid_bundle("missing_manifest");
        fs::remove_file(dir.join("companion_report.json")).unwrap();
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("MANIFEST_MISSING"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn malformed_json_fails() {
        let dir = valid_bundle("malformed");
        write(&dir, "companion_report.json", "{\"broken\": ");
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("MANIFEST_JSON_INVALID"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn unsupported_schema_fails() {
        let dir = valid_bundle("schema");
        let report = VALID_REPORT.replace(
            "\"companion_cli_version\": \"0.3.0\"",
            "\"companion_cli_version\": \"9.9.9\"",
        );
        write(&dir, "companion_report.json", &report);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("SCHEMA_VERSION_UNSUPPORTED"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn missing_required_field_fails() {
        let dir = valid_bundle("missing_field");
        let report = VALID_REPORT.replace(
            "\"sentinel_status\": \"PASS_STRICT\"",
            "\"sentinel_status_renamed\": \"PASS_STRICT\"",
        );
        write(&dir, "companion_report.json", &report);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("\"verdict\": \"FAIL\""));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn critical_unknown_field_fails() {
        let dir = valid_bundle("unknown_field");
        let report = VALID_REPORT.replace(
            "\"workflow_type\": \"CREATE_EVIDENCE_REASONING_CASE\"}",
            "\"workflow_type\": \"CREATE_EVIDENCE_REASONING_CASE\", \
             \"injected_claim\": \"trusted\"}",
        );
        write(&dir, "companion_report.json", &report);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("CRITICAL_UNKNOWN_FIELD"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn unknown_top_level_entry_fails() {
        let dir = valid_bundle("stray");
        write(&dir, "stray.txt", "planted");
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("CRITICAL_UNKNOWN_TOP_LEVEL_ENTRY"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn missing_referenced_file_fails() {
        let dir = valid_bundle("refmissing");
        let digest = "a".repeat(64);
        let sums = format!("{}  not_actually_there.json\n", digest);
        write(&dir, "companion_checksums.txt", &sums);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("REFERENCED_FILE_MISSING"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn unsafe_checksums_path_fails() {
        let dir = valid_bundle("unsafe");
        let digest = "a".repeat(64);
        let sums = format!("{}  ../escape.json\n", digest);
        write(&dir, "companion_checksums.txt", &sums);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("CHECKSUMS_PATH_UNSAFE"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn file_hash_mismatch_fails() {
        let dir = valid_bundle("hashmismatch");
        // change bytes of a declared file without updating its digest
        fs::write(dir.join("companion_steps.json"), "{ }").unwrap();
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("FILE_HASH_MISMATCH"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn malformed_digest_fails() {
        let dir = valid_bundle("baddigest");
        let sums = format!("{}  workflow_request.json\n", "Z".repeat(64));
        write(&dir, "companion_checksums.txt", &sums);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("MALFORMED_DIGEST"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn undeclared_required_path_fails() {
        let dir = valid_bundle("undeclared");
        // rebuild checksums with the case_manifest line removed: the
        // file still exists but its hash is no longer declared
        let sums_path = dir.join("companion_checksums.txt");
        let text = fs::read_to_string(&sums_path).unwrap();
        let kept: Vec<&str> = text
            .lines()
            .filter(|l| !l.ends_with("case_manifest.json"))
            .collect();
        fs::write(&sums_path, kept.join("\n") + "\n").unwrap();
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("REQUIRED_PATH_UNDECLARED"));
        assert_eq!(code, EXIT_FAIL);
    }

    fn write_run(dir: &Path, content: &str) {
        write(
            dir,
            "coordinator_output/sentinel_run/sentinel_run.json",
            content,
        );
    }

    #[test]
    fn run_record_missing_fails() {
        let dir = valid_bundle("norunrecord");
        fs::remove_file(
            dir.join("coordinator_output/sentinel_run/sentinel_run.json"),
        )
        .unwrap();
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("RUN_RECORD_MISSING"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn receipt_id_gap_fails() {
        let dir = valid_bundle("idgap");
        let run = sentinel_run_json().replace(
            "\"receipt_id\": 1",
            "\"receipt_id\": 5",
        );
        write_run(&dir, &run);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("RECEIPT_ID_SEQUENCE_BROKEN"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn broken_linkage_fails() {
        // Build a chain, then overwrite receipt 1's prior_hash with a
        // wrong (but well-formed) value AND recompute receipt 1's own
        // canonical_hash so the linkage break - not a hash mismatch -
        // is what fails. This exercises the structural check ordering.
        let dir = valid_bundle("linkage");
        let hm = "a".repeat(64);
        let (r0, _c0) = receipt_with_real_hash(0, "GENESIS");
        let wrong_prior = "e".repeat(64);
        let (r1, c1) = receipt_with_real_hash(1, &wrong_prior);
        let run = format!(
            r#"{{"manifest": {{"manifest_hash": "{}", "run_id": "run_fixture"}}, "receipts": [{}, {}], "run_seal": {{"final_receipt_hash": "{}", "final_receipt_id": 1, "final_session_state": "OPEN", "manifest_hash": "{}", "receipt_count": 2, "run_id": "run_fixture", "seal_hash": "{}", "seal_version": "0.1.0"}}}}"#,
            hm, r0, r1, c1, hm, "d".repeat(64)
        );
        write_run(&dir, &run);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("RECEIPT_LINKAGE_BROKEN"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn genesis_prior_hash_invalid_fails() {
        let dir = valid_bundle("genesis");
        let hm = "a".repeat(64);
        // receipt 0 with a hex prior instead of GENESIS, hash recomputed
        // to match so the GENESIS check (before recomputation) is what
        // fails
        let (r0, c0) = receipt_with_real_hash(0, &"f".repeat(64));
        let (r1, c1) = receipt_with_real_hash(1, &c0);
        let run = format!(
            r#"{{"manifest": {{"manifest_hash": "{}", "run_id": "run_fixture"}}, "receipts": [{}, {}], "run_seal": {{"final_receipt_hash": "{}", "final_receipt_id": 1, "final_session_state": "OPEN", "manifest_hash": "{}", "receipt_count": 2, "run_id": "run_fixture", "seal_hash": "{}", "seal_version": "0.1.0"}}}}"#,
            hm, r0, r1, c1, hm, "d".repeat(64)
        );
        write_run(&dir, &run);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("GENESIS_PRIOR_HASH_INVALID"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn seal_count_mismatch_fails() {
        let dir = valid_bundle("sealcount");
        let run = sentinel_run_json()
            .replace("\"receipt_count\": 2", "\"receipt_count\": 3");
        write_run(&dir, &run);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("SEAL_MISMATCH"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn session_continuity_broken_fails() {
        let dir = valid_bundle("continuity");
        // anchor on GENESIS (inside receipt 0's prior_hash): the first
        // state field after it is receipt 1's pre_session_state, which
        // must break continuity against receipt 0's post state
        let run = sentinel_run_json();
        let parts: Vec<&str> = run.splitn(2, "GENESIS").collect();
        let fixed = format!(
            "{}GENESIS{}",
            parts[0],
            parts[1].replacen(
                "\"pre_session_state\": \"OPEN\"",
                "\"pre_session_state\": \"HALTED\"",
                1
            )
        );
        write_run(&dir, &fixed);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("SESSION_CONTINUITY_BROKEN"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn malformed_receipt_key_set_fails() {
        let dir = valid_bundle("badkeys");
        let run = sentinel_run_json().replacen(
            "\"stage\": \"INTENT\"",
            "\"stage_renamed\": \"INTENT\"",
            1,
        );
        write_run(&dir, &run);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("RECEIPT_MALFORMED"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn receipt_hash_recomputation_mismatch_fails() {
        // change a hashed payload field (reason_code) without updating
        // canonical_hash: this is the tamper Move 76 could NOT catch and
        // Move 77 now does
        let dir = valid_bundle("recompute");
        let run = sentinel_run_json()
            .replacen("\"reason_code\": \"TEST\"",
                      "\"reason_code\": \"TAMPERED\"", 1);
        write_run(&dir, &run);
        let (line, code) = evaluate_bundle(&dir);
        assert!(line.contains("RECEIPT_HASH_RECOMPUTATION_MISMATCH"));
        assert_eq!(code, EXIT_FAIL);
    }

    #[test]
    fn no_reachable_path_emits_pass() {
        let valid = valid_bundle("nopass");
        let outcomes = [
            evaluate_bundle(Path::new("/nonexistent/witness/bundle")),
            evaluate_bundle(Path::new("Cargo.toml")),
            evaluate_bundle(&valid),
        ];
        for (line, code) in outcomes {
            assert!(!line.contains("\"verdict\": \"PASS\""));
            assert!(code != 0);
        }
    }

    #[test]
    fn json_escaping_is_safe() {
        let escaped = json_escape("a\"b\\c\nd");
        assert_eq!(escaped, "a\\\"b\\\\c\\nd");
    }
}

#[cfg(test)]
mod zipguard_tests {
    use super::zipguard;
    use std::fs;
    use std::path::{Path, PathBuf};

    // Minimal store-only ZIP writer for tests. Byte layout validated in
    // Python against the parser during Move 78 grounding.
    struct Zw {
        buf: Vec<u8>,
        central: Vec<(Vec<u8>, u16, u16, u32, u32, Vec<u8>)>,
    }
    impl Zw {
        fn new() -> Self {
            Zw { buf: Vec::new(), central: Vec::new() }
        }
        fn u16(&mut self, v: u16) {
            self.buf.extend_from_slice(&v.to_le_bytes());
        }
        fn u32(&mut self, v: u32) {
            self.buf.extend_from_slice(&v.to_le_bytes());
        }
        // Byte-faithful extras matching the REAL project archives:
        // central UT (len 5, flags 0x03, mtime), local UT (len 9, mtime +
        // atime), and UX (len 11, version 1, 4-byte uid/gid) on both.
        fn ut_central(mtime: i32) -> Vec<u8> {
            let mut v = Vec::new();
            v.extend_from_slice(&0x5455u16.to_le_bytes());
            v.extend_from_slice(&5u16.to_le_bytes());
            v.push(0x03);
            v.extend_from_slice(&mtime.to_le_bytes());
            v
        }
        fn ut_local(mtime: i32, atime: i32) -> Vec<u8> {
            let mut v = Vec::new();
            v.extend_from_slice(&0x5455u16.to_le_bytes());
            v.extend_from_slice(&9u16.to_le_bytes());
            v.push(0x03);
            v.extend_from_slice(&mtime.to_le_bytes());
            v.extend_from_slice(&atime.to_le_bytes());
            v
        }
        fn ux() -> Vec<u8> {
            let mut v = Vec::new();
            v.extend_from_slice(&0x7875u16.to_le_bytes());
            v.extend_from_slice(&11u16.to_le_bytes());
            v.push(1); v.push(4);
            v.extend_from_slice(&0u32.to_le_bytes());
            v.push(4);
            v.extend_from_slice(&0u32.to_le_bytes());
            v
        }
        fn real_central_extra() -> Vec<u8> {
            let mut v = Self::ut_central(1783018176);
            v.extend(Self::ux());
            v
        }
        fn real_local_extra() -> Vec<u8> {
            let mut v = Self::ut_local(1783018176, 1783018930);
            v.extend(Self::ux());
            v
        }

        fn entry(&mut self, name: &[u8], unix_mode: u32, method: u16,
                 utf8: bool, encrypted: bool) {
            let ce = Self::real_central_extra();
            let le = Self::real_local_extra();
            self.entry_x(name, name, unix_mode, method, utf8, encrypted,
                         &ce, &le);
        }
        // legacy signature kept for tests that pass a central extra only
        fn entry_full(&mut self, cname: &[u8], lname: &[u8], unix_mode: u32,
                      method: u16, utf8: bool, encrypted: bool,
                      cextra: &[u8]) {
            let le = Self::real_local_extra();
            self.entry_x(cname, lname, unix_mode, method, utf8, encrypted,
                         cextra, &le);
        }
        fn entry_local_extra(&mut self, name: &[u8], unix_mode: u32,
                             method: u16, utf8: bool, encrypted: bool,
                             lextra: &[u8]) {
            let ce = Self::real_central_extra();
            self.entry_x(name, name, unix_mode, method, utf8, encrypted,
                         &ce, lextra);
        }
        // Full control: distinct local name, central AND local extras.
        fn entry_x(&mut self, cname: &[u8], lname: &[u8], unix_mode: u32,
                   method: u16, utf8: bool, encrypted: bool,
                   cextra: &[u8], lextra: &[u8]) {
            let mut flags: u16 = 0;
            if utf8 { flags |= 0x0800; }
            if encrypted { flags |= 0x0001; }
            let lho = self.buf.len() as u32;
            self.u32(0x0403_4b50);
            self.u16(20); self.u16(flags); self.u16(method);
            self.u16(0); self.u16(0);
            self.u32(0); self.u32(0); self.u32(0);
            self.u16(lname.len() as u16);
            self.u16(lextra.len() as u16);
            self.buf.extend_from_slice(lname);
            self.buf.extend_from_slice(lextra);
            self.central.push((cname.to_vec(), flags, method, unix_mode, lho,
                               cextra.to_vec()));
        }
        fn finish(mut self) -> Vec<u8> {
            let cd_start = self.buf.len() as u32;
            let central = std::mem::take(&mut self.central);
            for (name, flags, method, unix_mode, lho, extra) in &central {
                self.u32(0x0201_4b50);
                self.u16(0x031e); self.u16(20); self.u16(*flags); self.u16(*method);
                self.u16(0); self.u16(0);
                self.u32(0); self.u32(0); self.u32(0);
                self.u16(name.len() as u16);
                self.u16(extra.len() as u16); self.u16(0);
                self.u16(0); self.u16(0);
                self.u32((unix_mode & 0xffff) << 16);
                self.u32(*lho);
                self.buf.extend_from_slice(name);
                self.buf.extend_from_slice(extra);
            }
            let cd_size = self.buf.len() as u32 - cd_start;
            let n = central.len() as u16;
            self.u32(0x0605_4b50);
            self.u16(0); self.u16(0); self.u16(n); self.u16(n);
            self.u32(cd_size); self.u32(cd_start); self.u16(0);
            self.buf
        }
    }

    fn tmp(name: &str, bytes: &[u8]) -> PathBuf {
        let mut p = std::env::temp_dir();
        p.push(format!("zg_{}_{}.zip", std::process::id(), name));
        fs::write(&p, bytes).unwrap();
        p
    }

    fn find_eocd(data: &[u8]) -> usize {
        let mut i = data.len() - 22;
        loop {
            if &data[i..i + 4] == &[0x50, 0x4b, 0x05, 0x06] { return i; }
            if i == 0 { panic!("no eocd"); }
            i -= 1;
        }
    }
    fn find_cd(data: &[u8]) -> usize {
        for i in 0..data.len() - 4 {
            if &data[i..i + 4] == &[0x50, 0x4b, 0x01, 0x02] { return i; }
        }
        panic!("no central dir")
    }
    fn inspect(bytes: &[u8], name: &str) -> Result<usize, (String, String)> {
        let p = tmp(name, bytes);
        let r = zipguard::inspect_archive(&p);
        fs::remove_file(&p).ok();
        r
    }

    const F: u32 = 0o100644;
    const D: u32 = 0o040755;

    #[test]
    fn clean_archive_ok() {
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        z.entry(b"dir/", D, 0, false, false);
        z.entry(b"dir/b.txt", F, 0, false, false);
        assert_eq!(inspect(&z.finish(), "clean").unwrap(), 3);
    }

    fn expect_fail(bytes: &[u8], name: &str, code: &str) {
        match inspect(bytes, name) {
            Err((c, _)) => assert_eq!(c, code, "wrong code for {}", name),
            Ok(_) => panic!("{} should have failed with {}", name, code),
        }
    }

    #[test]
    fn traversal() {
        let mut z = Zw::new();
        z.entry(b"../evil", F, 0, false, false);
        expect_fail(&z.finish(), "trav", "ARCHIVE_PATH_TRAVERSAL");
    }
    #[test]
    fn nested_traversal() {
        let mut z = Zw::new();
        z.entry(b"a/b/../../../evil", F, 0, false, false);
        expect_fail(&z.finish(), "ntrav", "ARCHIVE_PATH_TRAVERSAL");
    }
    #[test]
    fn absolute_unix() {
        let mut z = Zw::new();
        z.entry(b"/etc/passwd", F, 0, false, false);
        expect_fail(&z.finish(), "abs", "ARCHIVE_ABSOLUTE_PATH");
    }
    #[test]
    fn windows_drive() {
        let mut z = Zw::new();
        z.entry(b"C:windows", F, 0, false, false);
        expect_fail(&z.finish(), "drive", "ARCHIVE_WINDOWS_DRIVE_PATH");
    }
    #[test]
    fn unc_path() {
        let mut z = Zw::new();
        z.entry(b"//server/share", F, 0, false, false);
        expect_fail(&z.finish(), "unc", "ARCHIVE_UNC_PATH");
    }
    #[test]
    fn backslash() {
        let mut z = Zw::new();
        z.entry(b"a\\b", F, 0, false, false);
        expect_fail(&z.finish(), "bs", "ARCHIVE_BACKSLASH_PATH");
    }
    #[test]
    fn mixed_separator_backslash_traversal() {
        let mut z = Zw::new();
        z.entry(b"a/..\\b", F, 0, false, false);
        // backslash is caught first (any backslash is unsafe here)
        expect_fail(&z.finish(), "mix", "ARCHIVE_BACKSLASH_PATH");
    }
    #[test]
    fn exact_duplicate() {
        let mut z = Zw::new();
        z.entry(b"same.txt", F, 0, false, false);
        z.entry(b"same.txt", F, 0, false, false);
        expect_fail(&z.finish(), "dup", "ARCHIVE_DUPLICATE_NAME");
    }
    #[test]
    fn case_collision() {
        let mut z = Zw::new();
        z.entry(b"File.txt", F, 0, false, false);
        z.entry(b"file.txt", F, 0, false, false);
        expect_fail(&z.finish(), "case", "ARCHIVE_CASE_COLLISION");
    }
    #[test]
    fn symlink_entry() {
        let mut z = Zw::new();
        z.entry(b"link", 0o120777, 0, false, false);
        expect_fail(&z.finish(), "sym", "ARCHIVE_SYMLINK_ENTRY");
    }
    #[test]
    fn file_directory_collision() {
        let mut z = Zw::new();
        z.entry(b"x", F, 0, false, false);
        z.entry(b"x/", D, 0, false, false);
        expect_fail(&z.finish(), "fdc", "ARCHIVE_FILE_DIRECTORY_COLLISION");
    }
    #[test]
    fn control_character() {
        let mut z = Zw::new();
        z.entry(b"a\x01b", F, 0, false, false);
        expect_fail(&z.finish(), "ctrl", "ARCHIVE_CONTROL_CHARACTER");
    }
    #[test]
    fn bidi_character() {
        let mut z = Zw::new();
        // U+202E RIGHT-TO-LEFT OVERRIDE in UTF-8, utf8 flag set
        z.entry("a\u{202E}b.txt".as_bytes(), F, 0, true, false);
        expect_fail(&z.finish(), "bidi", "ARCHIVE_BIDI_CHARACTER");
    }
    #[test]
    fn non_ascii_without_utf8_flag_fails_closed() {
        let mut z = Zw::new();
        z.entry(&[0x66, 0xC3, 0xA9], F, 0, false, false); // "fé" no flag
        expect_fail(&z.finish(), "enc", "ARCHIVE_UNICODE_NAME_UNSAFE");
    }
    #[test]
    fn combining_mark_fails_closed() {
        let mut z = Zw::new();
        // e + combining acute (U+0301), utf8 flagged: normalization unsafe
        z.entry("e\u{0301}.txt".as_bytes(), F, 0, true, false);
        expect_fail(&z.finish(), "comb", "ARCHIVE_UNICODE_NAME_UNSAFE");
    }
    #[test]
    fn invalid_utf8_with_flag_fails() {
        let mut z = Zw::new();
        z.entry(&[0xFF, 0xFE], F, 0, true, false); // flag set, bad utf8
        expect_fail(&z.finish(), "badutf8", "ARCHIVE_UNICODE_NAME_UNSAFE");
    }
    #[test]
    fn malformed_no_eocd() {
        expect_fail(b"not a zip at all", "malformed", "ARCHIVE_MALFORMED");
    }
    #[test]
    fn encrypted_unsupported() {
        let mut z = Zw::new();
        z.entry(b"secret", F, 0, false, true);
        expect_fail(&z.finish(), "enc2", "ARCHIVE_UNSUPPORTED_FEATURE");
    }
    #[test]
    fn unsupported_compression() {
        let mut z = Zw::new();
        z.entry(b"data", F, 99, false, false); // method 99 = unsupported
        expect_fail(&z.finish(), "method", "ARCHIVE_UNSUPPORTED_FEATURE");
    }
    #[test]
    fn local_header_name_mismatch_fails() {
        // central says safe.txt, local header says ../x.txt (same length)
        let mut z = Zw::new();
        z.entry_full(b"safe.txt", b"../x.txt", F, 0, false, false, &[]);
        expect_fail(&z.finish(), "lhmismatch",
                    "ARCHIVE_LOCAL_HEADER_MISMATCH");
    }

    #[test]
    fn unicode_path_extra_field_fails_closed() {
        // Unicode Path extra field (tag 0x7075) present in central entry
        let mut z = Zw::new();
        let extra = {
            let mut v = Vec::new();
            v.extend_from_slice(&0x7075u16.to_le_bytes());
            v.extend_from_slice(&5u16.to_le_bytes());
            v.push(1); // version
            v.extend_from_slice(&[0, 0, 0, 0]); // name crc
            v
        };
        z.entry_full(b"a.txt", b"a.txt", F, 0, false, false, &extra);
        expect_fail(&z.finish(), "upextra",
                    "ARCHIVE_UNSUPPORTED_FEATURE");
    }

    #[test]
    fn malformed_extra_length_fails() {
        let mut z = Zw::new();
        // extra field claims 200 bytes of payload but supplies none
        let extra = {
            let mut v = Vec::new();
            v.extend_from_slice(&0x9999u16.to_le_bytes());
            v.extend_from_slice(&200u16.to_le_bytes());
            v
        };
        z.entry_full(b"a.txt", b"a.txt", F, 0, false, false, &extra);
        expect_fail(&z.finish(), "badextra", "ARCHIVE_MALFORMED");
    }

    #[test]
    fn dot_component_collision_fails() {
        let mut z = Zw::new();
        z.entry(b"a/./b", F, 0, false, false);
        expect_fail(&z.finish(), "dot", "ARCHIVE_PATH_TRAVERSAL");
    }

    #[test]
    fn repeated_separator_fails() {
        let mut z = Zw::new();
        z.entry(b"a//b", F, 0, false, false);
        expect_fail(&z.finish(), "repsep", "ARCHIVE_PATH_TRAVERSAL");
    }

    #[test]
    fn empty_filename_fails() {
        let mut z = Zw::new();
        z.entry(b"/", F, 0, false, false); // becomes empty after dir strip
        // leading slash is absolute; check the empty-name path directly
        let mut z2 = Zw::new();
        z2.entry(b"dir/", D, 0, false, false);
        z2.entry(b"dir//", D, 0, false, false);
        expect_fail(&z2.finish(), "empty", "ARCHIVE_PATH_TRAVERSAL");
        let _ = z;
    }

    #[test]
    fn multiple_trailing_slash_fails() {
        let mut z = Zw::new();
        z.entry(b"dir//", D, 0, false, false);
        expect_fail(&z.finish(), "multislash", "ARCHIVE_PATH_TRAVERSAL");
    }

    // v3: EVERY non-ASCII name fails closed while Unicode normalization
    // and case folding are unimplemented. v2's combining-mark heuristic
    // was unsound: precomposed É has no combining mark, so it was
    // accepted and then case-compared with ASCII-only lowercase.
    fn assert_non_ascii_fails(name: &str, tag: &str) {
        let mut z = Zw::new();
        z.entry(name.as_bytes(), F, 0, true, false);
        match inspect(&z.finish(), tag) {
            Err((c, _)) => assert_eq!(
                c, "ARCHIVE_UNICODE_NAME_UNSAFE",
                "non-ascii {:?} must fail closed", name),
            Ok(_) => panic!("non-ascii name {:?} accepted", name),
        }
    }

    #[test]
    fn non_ascii_precomposed_uppercase_fails() {
        assert_non_ascii_fails("\u{00C9}.txt", "na_precomp_upper"); // É
    }

    #[test]
    fn non_ascii_precomposed_lowercase_fails() {
        assert_non_ascii_fails("\u{00E9}.txt", "na_precomp_lower"); // é
    }

    #[test]
    fn non_ascii_decomposed_fails() {
        // E + combining acute: the NFD equivalent of É
        assert_non_ascii_fails("E\u{0301}.txt", "na_decomp");
    }

    #[test]
    fn non_ascii_greek_and_cyrillic_fail() {
        assert_non_ascii_fails("\u{03B1}.txt", "na_greek");    // α
        assert_non_ascii_fails("\u{0431}.txt", "na_cyrillic"); // б
    }

    #[test]
    fn local_version_needed_mismatch_fails() {
        // build a zip, then patch the LOCAL header's version-needed only
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let mut bytes = z.finish();
        // local header version-needed is at offset 4 of the first LFH
        bytes[4] = 45;
        bytes[5] = 0;
        expect_fail(&bytes, "lver", "ARCHIVE_LOCAL_HEADER_MISMATCH");
    }

    #[test]
    fn local_unicode_path_extra_fails_closed() {
        // Unicode Path extra in the LOCAL header, absent centrally
        let mut z = Zw::new();
        z.entry_local_extra(b"a.txt", F, 0, false, false, &{
            let mut v = Vec::new();
            v.extend_from_slice(&0x7075u16.to_le_bytes());
            v.extend_from_slice(&5u16.to_le_bytes());
            v.push(1);
            v.extend_from_slice(&[0, 0, 0, 0]);
            v
        });
        expect_fail(&z.finish(), "lupextra", "ARCHIVE_UNSUPPORTED_FEATURE");
    }

    #[test]
    fn malformed_local_extra_length_fails() {
        let mut z = Zw::new();
        z.entry_local_extra(b"a.txt", F, 0, false, false, &{
            let mut v = Vec::new();
            v.extend_from_slice(&0x9999u16.to_le_bytes());
            v.extend_from_slice(&200u16.to_le_bytes()); // claims 200, gives 0
            v
        });
        expect_fail(&z.finish(), "lbadextra",
                    "ARCHIVE_LOCAL_HEADER_MALFORMED");
    }

    // ---- Move 78 v4: raw flags ----
    fn zw_with_flags(name: &[u8], cflags: u16, lflags: u16) -> Vec<u8> {
        // hand-build a one-entry zip with distinct central/local flags
        let mut b: Vec<u8> = Vec::new();
        let put16 = |b: &mut Vec<u8>, v: u16| b.extend_from_slice(&v.to_le_bytes());
        let put32 = |b: &mut Vec<u8>, v: u32| b.extend_from_slice(&v.to_le_bytes());
        let lho = 0u32;
        put32(&mut b, 0x0403_4b50);
        put16(&mut b, 20); put16(&mut b, lflags); put16(&mut b, 0);
        put16(&mut b, 0); put16(&mut b, 0);
        put32(&mut b, 0); put32(&mut b, 0); put32(&mut b, 0);
        put16(&mut b, name.len() as u16); put16(&mut b, 0);
        b.extend_from_slice(name);
        let cd_start = b.len() as u32;
        put32(&mut b, 0x0201_4b50);
        put16(&mut b, 0x031e); put16(&mut b, 20); put16(&mut b, cflags);
        put16(&mut b, 0); put16(&mut b, 0); put16(&mut b, 0);
        put32(&mut b, 0); put32(&mut b, 0); put32(&mut b, 0);
        put16(&mut b, name.len() as u16); put16(&mut b, 0); put16(&mut b, 0);
        put16(&mut b, 0); put16(&mut b, 0);
        put32(&mut b, (0o100644u32 & 0xffff) << 16);
        put32(&mut b, lho);
        b.extend_from_slice(name);
        let cd_size = b.len() as u32 - cd_start;
        put32(&mut b, 0x0605_4b50);
        put16(&mut b, 0); put16(&mut b, 0); put16(&mut b, 1); put16(&mut b, 1);
        put32(&mut b, cd_size); put32(&mut b, cd_start); put16(&mut b, 0);
        b
    }

    #[test]
    fn flags_bit3_central_local_mismatch_fails() {
        // central bit3 set, local clear -> raw flags disagree
        expect_fail(&zw_with_flags(b"a.txt", 0x0008, 0x0000), "f3mis",
                    "ARCHIVE_LOCAL_HEADER_MISMATCH");
    }
    #[test]
    fn flags_bit3_equal_but_unsupported_fails() {
        // both set bit3 -> flags agree but bit3 is unsupported
        expect_fail(&zw_with_flags(b"a.txt", 0x0008, 0x0008), "f3eq",
                    "ARCHIVE_UNSUPPORTED_FEATURE");
    }
    #[test]
    fn flags_unknown_bit_fails_closed() {
        expect_fail(&zw_with_flags(b"a.txt", 0x4000, 0x4000), "funk",
                    "ARCHIVE_UNSUPPORTED_FEATURE");
    }
    #[test]
    fn flags_supported_agreement_ok() {
        // utf8 flag (0x0800) on an ASCII name, both headers -> fine
        let bytes = zw_with_flags(b"a.txt", 0x0800, 0x0800);
        assert_eq!(inspect(&bytes, "fok").unwrap(), 1);
    }

    // ---- parent-prefix file/dir collisions ----
    #[test]
    fn file_then_dir_prefix_collision() {
        let mut z = Zw::new();
        z.entry(b"a", F, 0, false, false);
        z.entry(b"a/b", F, 0, false, false);
        expect_fail(&z.finish(), "fpx", "ARCHIVE_FILE_DIRECTORY_COLLISION");
    }
    #[test]
    fn dir_prefix_then_file_collision() {
        let mut z = Zw::new();
        z.entry(b"a/b", F, 0, false, false);
        z.entry(b"a", F, 0, false, false);
        expect_fail(&z.finish(), "pxf", "ARCHIVE_FILE_DIRECTORY_COLLISION");
    }
    #[test]
    fn case_folded_prefix_collision() {
        let mut z = Zw::new();
        z.entry(b"A", F, 0, false, false);
        z.entry(b"a/b", F, 0, false, false);
        expect_fail(&z.finish(), "cpx", "ARCHIVE_FILE_DIRECTORY_COLLISION");
    }
    #[test]
    fn explicit_dir_plus_child_is_valid() {
        let mut z = Zw::new();
        z.entry(b"a/", D, 0, false, false);
        z.entry(b"a/b", F, 0, false, false);
        assert_eq!(inspect(&z.finish(), "okdir").unwrap(), 2);
    }

    // ---- CRC / size mismatch (patch local header bytes) ----
    #[test]
    fn crc_mismatch_fails() {
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let mut bytes = z.finish();
        // local CRC at offset 14 of the first LFH
        bytes[14] = 0xAA;
        expect_fail(&bytes, "crc", "ARCHIVE_LOCAL_HEADER_MISMATCH");
    }
    #[test]
    fn compressed_size_mismatch_fails() {
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let mut bytes = z.finish();
        bytes[18] = 0x05; // local comp size at offset 18
        expect_fail(&bytes, "csz", "ARCHIVE_LOCAL_HEADER_MISMATCH");
    }
    #[test]
    fn uncompressed_size_mismatch_fails() {
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let mut bytes = z.finish();
        bytes[22] = 0x05; // local uncomp size at offset 22
        expect_fail(&bytes, "usz", "ARCHIVE_LOCAL_HEADER_MISMATCH");
    }
    #[test]
    fn data_descriptor_flag_fails_closed() {
        expect_fail(&zw_with_flags(b"a.txt", 0x0008, 0x0008), "dd",
                    "ARCHIVE_UNSUPPORTED_FEATURE");
    }

    // ---- Windows-hostile names ----
    #[test]
    fn trailing_dot_fails() {
        let mut z = Zw::new();
        z.entry(b"file.", F, 0, false, false);
        expect_fail(&z.finish(), "tdot", "ARCHIVE_WINDOWS_NAME_UNSAFE");
    }
    #[test]
    fn trailing_space_fails() {
        let mut z = Zw::new();
        z.entry(b"file ", F, 0, false, false);
        expect_fail(&z.finish(), "tsp", "ARCHIVE_WINDOWS_NAME_UNSAFE");
    }
    #[test]
    fn reserved_con_fails() {
        let mut z = Zw::new();
        z.entry(b"CON", F, 0, false, false);
        expect_fail(&z.finish(), "con", "ARCHIVE_WINDOWS_NAME_UNSAFE");
    }
    #[test]
    fn reserved_con_with_ext_fails() {
        let mut z = Zw::new();
        z.entry(b"con.txt", F, 0, false, false);
        expect_fail(&z.finish(), "conext", "ARCHIVE_WINDOWS_NAME_UNSAFE");
    }
    #[test]
    fn reserved_com1_fails() {
        let mut z = Zw::new();
        z.entry(b"COM1.log", F, 0, false, false);
        expect_fail(&z.finish(), "com1", "ARCHIVE_WINDOWS_NAME_UNSAFE");
    }
    #[test]
    fn ads_colon_fails() {
        let mut z = Zw::new();
        z.entry(b"file.txt:stream", F, 0, false, false);
        expect_fail(&z.finish(), "ads", "ARCHIVE_ALTERNATE_DATA_STREAM");
    }

    // ---- missing structural tests (v5) ----
    #[test]
    fn entry_data_into_central_directory_fails() {
        // patch the first entry's central compressed-size to a large
        // value so its computed data range runs past the central dir
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let mut bytes = z.finish();
        // find central header (starts after local data); set both local
        // and central comp_size equal and large so ranges overlap the CD.
        // local comp size at offset 18, central at cd header +20.
        // Simpler: set local+central comp size to 0xF000 (both agree).
        bytes[18] = 0x00; bytes[19] = 0xF0; // local comp size low..high
        // central comp size: locate central sig
        let cd = find_cd(&bytes);
        bytes[cd + 20] = 0x00; bytes[cd + 21] = 0xF0;
        expect_fail(&bytes, "dataintocd", "ARCHIVE_MALFORMED");
    }

    #[test]
    fn overlapping_entry_ranges_fail() {
        // two entries whose local ranges overlap: set entry 0 comp_size
        // large enough to cover entry 1's local header
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        z.entry(b"b.txt", F, 0, false, false);
        let mut bytes = z.finish();
        // entry 0 local comp size (offset 18) -> 60 bytes, enough to
        // swallow entry 1's local header; set central to match
        bytes[18] = 60;
        let cd = find_cd(&bytes);
        bytes[cd + 20] = 60;
        // taxonomy (v9): individually valid ranges that conflict are a
        // LAYOUT problem; OFFSET_INVALID is reserved for an offset that
        // is itself invalid (out of range / duplicated).
        expect_fail(&bytes, "overlap", "ARCHIVE_LOCAL_LAYOUT_INVALID");
    }

    #[test]
    fn nonzero_disk_start_fails() {
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let mut bytes = z.finish();
        let cd = find_cd(&bytes);
        // central disk-start field at cd header + 34
        bytes[cd + 34] = 1;
        expect_fail(&bytes, "disk", "ARCHIVE_UNSUPPORTED_FEATURE");
    }

    #[test]
    fn cd_not_ending_at_eocd_fails() {
        // insert a stray byte between central directory and EOCD
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let bytes = z.finish();
        let eocd = find_eocd(&bytes);
        let mut patched = bytes[..eocd].to_vec();
        patched.push(0x00); // stray byte
        patched.extend_from_slice(&bytes[eocd..]);
        // EOCD cd_offset/size now no longer reach the EOCD position
        expect_fail(&patched, "cdgap", "ARCHIVE_UNSUPPORTED_FEATURE");
    }

    #[test]
    fn eocd_comment_length_mismatch_fails() {
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let mut bytes = z.finish();
        let eocd = find_eocd(&bytes);
        // comment length field at eocd+20; claim 5 with no comment bytes
        bytes[eocd + 20] = 5;
        expect_fail(&bytes, "comment", "ARCHIVE_MALFORMED");
    }

    // ---- extra-field fail-closed ----
    #[test]
    fn unknown_central_extra_field_fails() {
        let mut z = Zw::new();
        let extra = { let mut v = Vec::new();
            v.extend_from_slice(&0x1234u16.to_le_bytes());
            v.extend_from_slice(&2u16.to_le_bytes());
            v.extend_from_slice(&[0, 0]); v };
        z.entry_full(b"a.txt", b"a.txt", F, 0, false, false, &extra);
        expect_fail(&z.finish(), "cextra", "ARCHIVE_UNSUPPORTED_FEATURE");
    }

    #[test]
    fn unknown_local_extra_field_fails() {
        let mut z = Zw::new();
        let extra = { let mut v = Vec::new();
            v.extend_from_slice(&0x1234u16.to_le_bytes());
            v.extend_from_slice(&2u16.to_le_bytes());
            v.extend_from_slice(&[0, 0]); v };
        z.entry_local_extra(b"a.txt", F, 0, false, false, &extra);
        // taxonomy (v9): an unknown tag is an UNSUPPORTED FEATURE, not a
        // central/local mismatch (mismatch is for SUPPORTED fields whose
        // values disagree).
        expect_fail(&z.finish(), "lextra", "ARCHIVE_UNSUPPORTED_FEATURE");
    }

    // ---- special file types ----
    #[test]
    fn fifo_entry_fails() {
        let mut z = Zw::new();
        z.entry(b"pipe", 0o010644, 0, false, false); // S_IFIFO
        expect_fail(&z.finish(), "fifo", "ARCHIVE_SPECIAL_FILE_TYPE");
    }

    #[test]
    fn char_device_entry_fails() {
        let mut z = Zw::new();
        z.entry(b"dev", 0o020644, 0, false, false); // S_IFCHR
        expect_fail(&z.finish(), "chardev", "ARCHIVE_SPECIAL_FILE_TYPE");
    }

    #[test]
    fn trailing_slash_with_file_mode_fails() {
        let mut z = Zw::new();
        z.entry(b"x/", F, 0, false, false); // regular-file mode, dir name
        expect_fail(&z.finish(), "slashfile",
                    "ARCHIVE_FILE_DIRECTORY_COLLISION");
    }

    #[test]
    fn directory_mode_without_slash_fails() {
        let mut z = Zw::new();
        z.entry(b"x", D, 0, false, false); // dir mode, no trailing slash
        expect_fail(&z.finish(), "dirnoslash",
                    "ARCHIVE_FILE_DIRECTORY_COLLISION");
    }

    // ---- v6: real-archive extra-field pattern ----
    #[test]
    fn real_extra_field_pattern_accepted() {
        // byte-faithful UT(5/9) + UX(11) pattern from the actual v20 and
        // 70.5 archives, creator host 3
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        z.entry(b"dir/", D, 0, false, false);
        assert_eq!(inspect(&z.finish(), "realextra").unwrap(), 2);
    }

    #[test]
    fn central_local_mtime_disagreement_fails() {
        let mut z = Zw::new();
        let mut ce = Zw::ut_central(1000); ce.extend(Zw::ux());
        let mut le = Zw::ut_local(2000, 3000); le.extend(Zw::ux());
        z.entry_x(b"a.txt", b"a.txt", F, 0, false, false, &ce, &le);
        expect_fail(&z.finish(), "mtime", "ARCHIVE_LOCAL_HEADER_MISMATCH");
    }

    #[test]
    fn malformed_ut_field_fails() {
        let mut z = Zw::new();
        // UT claiming len 5 but flags advertise nothing (no mtime bit)
        let ce = {
            let mut v = Vec::new();
            v.extend_from_slice(&0x5455u16.to_le_bytes());
            v.extend_from_slice(&5u16.to_le_bytes());
            v.push(0x00); // no mtime bit
            v.extend_from_slice(&0u32.to_le_bytes());
            v
        };
        z.entry_x(b"a.txt", b"a.txt", F, 0, false, false, &ce,
                  &Zw::real_local_extra());
        expect_fail(&z.finish(), "badut", "ARCHIVE_UNSUPPORTED_FEATURE");
    }

    #[test]
    fn malformed_uid_gid_field_fails() {
        let mut z = Zw::new();
        let ce = {
            let mut v = Zw::ut_central(1783018176);
            v.extend_from_slice(&0x7875u16.to_le_bytes());
            v.extend_from_slice(&3u16.to_le_bytes());
            v.push(1); v.push(9); v.push(0); // uidsz 9 > 8 -> malformed
            v
        };
        z.entry_x(b"a.txt", b"a.txt", F, 0, false, false, &ce,
                  &Zw::real_local_extra());
        expect_fail(&z.finish(), "baduid", "ARCHIVE_MALFORMED");
    }

    #[test]
    fn duplicate_extra_tag_fails() {
        let mut z = Zw::new();
        let mut ce = Zw::ut_central(1783018176);
        ce.extend(Zw::ut_central(1783018176)); // duplicate UT
        ce.extend(Zw::ux());
        z.entry_x(b"a.txt", b"a.txt", F, 0, false, false, &ce,
                  &Zw::real_local_extra());
        expect_fail(&z.finish(), "duptag", "ARCHIVE_MALFORMED");
    }

    #[test]
    fn zip64_extra_tag_rejected() {
        let mut z = Zw::new();
        let mut ce = Zw::ut_central(1783018176);
        ce.extend_from_slice(&0x0001u16.to_le_bytes());
        ce.extend_from_slice(&0u16.to_le_bytes());
        ce.extend(Zw::ux());
        z.entry_x(b"a.txt", b"a.txt", F, 0, false, false, &ce,
                  &Zw::real_local_extra());
        expect_fail(&z.finish(), "z64tag", "ARCHIVE_UNSUPPORTED_FEATURE");
    }

    // ---- v6: unreferenced data / layout ----
    #[test]
    fn prepended_sfx_bytes_fail() {
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let bytes = z.finish();
        // prepend junk and fix nothing: local offsets now leave a gap
        let mut sfx = vec![0x4Du8, 0x5A, 0x90, 0x00]; // MZ stub
        sfx.extend_from_slice(&bytes);
        // the EOCD's cd_offset still points at the OLD offset, so this is
        // a structurally broken archive -> must fail (not ACCEPT)
        match inspect(&sfx, "sfx") {
            Err((c, _)) => assert!(
                c == "ARCHIVE_UNREFERENCED_DATA"
                    || c == "ARCHIVE_MALFORMED"
                    || c == "ARCHIVE_LOCAL_HEADER_MALFORMED"
                    || c == "ARCHIVE_LOCAL_LAYOUT_INVALID",
                "sfx stub must fail closed, got {}", c),
            Ok(_) => panic!("prepended SFX bytes accepted"),
        }
    }

    #[test]
    fn orphan_local_header_fails() {
        // build a valid one-entry zip, then splice an unreferenced local
        // header (with a traversal name) before the central directory
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let bytes = z.finish();
        let cd = find_cd(&bytes);
        let mut orphan: Vec<u8> = Vec::new();
        orphan.extend_from_slice(&0x0403_4b50u32.to_le_bytes());
        orphan.extend_from_slice(&20u16.to_le_bytes());
        orphan.extend_from_slice(&0u16.to_le_bytes());
        orphan.extend_from_slice(&0u16.to_le_bytes());
        orphan.extend_from_slice(&[0u8; 4]);
        orphan.extend_from_slice(&[0u8; 12]);
        orphan.extend_from_slice(&8u16.to_le_bytes()); // name len
        orphan.extend_from_slice(&0u16.to_le_bytes());
        orphan.extend_from_slice(b"../x.txt");
        let mut patched = bytes[..cd].to_vec();
        patched.extend_from_slice(&orphan);
        // EOCD cd_offset now stale -> unreferenced data before CD
        patched.extend_from_slice(&bytes[cd..]);
        match inspect(&patched, "orphan") {
            Err(_) => {}
            Ok(_) => panic!("orphan local header accepted"),
        }
    }

    #[test]
    fn contiguous_clean_archive_accepted() {
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        z.entry(b"b.txt", F, 0, false, false);
        assert_eq!(inspect(&z.finish(), "contig").unwrap(), 2);
    }

    // ---- v6: creator host / file type ----
    #[test]
    fn non_unix_creator_rejected() {
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let mut bytes = z.finish();
        let cd = find_cd(&bytes);
        bytes[cd + 5] = 0x00; // creator host 0 = DOS
        expect_fail(&bytes, "dos", "ARCHIVE_UNSUPPORTED_FEATURE");
    }

    #[test]
    fn zero_file_type_rejected() {
        let mut z = Zw::new();
        z.entry(b"a.txt", 0, 0, false, false); // zero unix mode
        expect_fail(&z.finish(), "zeroft", "ARCHIVE_SPECIAL_FILE_TYPE");
    }

    #[test]
    fn directory_with_data_rejected() {
        let mut z = Zw::new();
        z.entry(b"dir/", D, 0, false, false);
        let mut bytes = z.finish();
        let cd = find_cd(&bytes);
        bytes[cd + 20] = 5;  // central comp size
        bytes[18] = 5;       // local comp size
        match inspect(&bytes, "dirdata") {
            Err(_) => {}
            Ok(_) => panic!("directory carrying data accepted"),
        }
    }

    #[test]
    fn central_local_ut_flags_disagreement_fails() {
        // same mtime, different UT flag bytes -> must fail
        let mut z = Zw::new();
        let mut ce = {
            let mut v = Vec::new();
            v.extend_from_slice(&0x5455u16.to_le_bytes());
            v.extend_from_slice(&5u16.to_le_bytes());
            v.push(0x01); // mtime only
            v.extend_from_slice(&1783018176i32.to_le_bytes());
            v
        };
        ce.extend(Zw::ux());
        // local advertises 0x03 (mtime+atime) with the SAME mtime
        let mut le = Zw::ut_local(1783018176, 1783018930);
        le.extend(Zw::ux());
        z.entry_x(b"a.txt", b"a.txt", F, 0, false, false, &ce, &le);
        expect_fail(&z.finish(), "utflags",
                    "ARCHIVE_LOCAL_HEADER_MISMATCH");
    }

    // ---- v9: neighbouring reason-code distinctions ----
    #[test]
    fn dot_component_is_traversal_not_windows() {
        let mut z = Zw::new();
        z.entry(b"a/./b", F, 0, false, false);
        expect_fail(&z.finish(), "dotcomp", "ARCHIVE_PATH_TRAVERSAL");
    }

    #[test]
    fn trailing_dot_name_is_windows_not_traversal() {
        let mut z = Zw::new();
        z.entry(b"file.", F, 0, false, false);
        expect_fail(&z.finish(), "trailingdot",
                    "ARCHIVE_WINDOWS_NAME_UNSAFE");
    }

    #[test]
    fn unc_beats_generic_absolute() {
        let mut z = Zw::new();
        z.entry(b"//server/share", F, 0, false, false);
        expect_fail(&z.finish(), "uncfirst", "ARCHIVE_UNC_PATH");
    }

    #[test]
    fn plain_absolute_is_absolute() {
        let mut z = Zw::new();
        z.entry(b"/etc/passwd", F, 0, false, false);
        expect_fail(&z.finish(), "absplain", "ARCHIVE_ABSOLUTE_PATH");
    }

    #[test]
    fn out_of_range_local_offset_is_offset_invalid() {
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let mut bytes = z.finish();
        let cd = find_cd(&bytes);
        // central local-header offset field at cd+42: point it past the CD
        bytes[cd + 42] = 0xF0;
        bytes[cd + 43] = 0xFF;
        expect_fail(&bytes, "offrange",
                    "ARCHIVE_LOCAL_HEADER_OFFSET_INVALID");
    }

    #[test]
    fn supported_extra_value_disagreement_is_mismatch() {
        // UT present in both, mtime differs -> MISMATCH (not UNSUPPORTED)
        let mut z = Zw::new();
        let mut ce = Zw::ut_central(1000); ce.extend(Zw::ux());
        let mut le = Zw::ut_local(2000, 3000); le.extend(Zw::ux());
        z.entry_x(b"a.txt", b"a.txt", F, 0, false, false, &ce, &le);
        expect_fail(&z.finish(), "valdis",
                    "ARCHIVE_LOCAL_HEADER_MISMATCH");
    }

    #[test]
    fn malformed_local_extra_is_local_malformed() {
        let mut z = Zw::new();
        let bad = {
            let mut v = Vec::new();
            v.extend_from_slice(&0x5455u16.to_le_bytes());
            v.extend_from_slice(&200u16.to_le_bytes()); // claims 200, gives 0
            v
        };
        z.entry_local_extra(b"a.txt", F, 0, false, false, &bad);
        expect_fail(&z.finish(), "lmalformed",
                    "ARCHIVE_LOCAL_HEADER_MALFORMED");
    }

    #[test]
    fn accepted_archive_exposes_structured_entry_count() {
        // Move 79: the harness must never parse counts from free text.
        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        z.entry(b"dir/", D, 0, false, false);
        z.entry(b"dir/b.txt", F, 0, false, false);
        let p = tmp("count", &z.finish());
        let (line, code) = super::evaluate_archive(&p);
        fs::remove_file(&p).ok();
        assert!(line.contains("\"entry_count\": 3"),
                "structured entry_count missing: {}", line);
        assert!(line.contains("ARCHIVE_SAFETY_OK"));
        assert_eq!(code, 3);
    }

    #[test]
    fn inspection_creates_no_files() {
        // CONCURRENCY SAFETY (v10): this test must NEVER snapshot the
        // shared global temp root. Other tests create and delete their
        // own fixtures there in parallel, so a directory-wide count of
        // std::env::temp_dir() races with them (this failed the v9
        // parallel Cargo gate while passing --test-threads=1).
        // Instead: create a DEDICATED directory for this test alone and
        // snapshot only that.
        use std::sync::atomic::{AtomicUsize, Ordering};
        static SEQ: AtomicUsize = AtomicUsize::new(0);

        let mut dir = std::env::temp_dir();
        dir.push(format!(
            "zg_noextract_{}_{}",
            std::process::id(),
            SEQ.fetch_add(1, Ordering::SeqCst)
        ));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir(&dir).expect("dedicated test dir");

        let mut z = Zw::new();
        z.entry(b"a.txt", F, 0, false, false);
        let archive_bytes = z.finish();
        let archive = dir.join("fixture.zip");
        fs::write(&archive, &archive_bytes).unwrap();

        // snapshot the DEDICATED directory only
        let snapshot = |d: &Path| -> Vec<String> {
            let mut v: Vec<String> = fs::read_dir(d)
                .unwrap()
                .map(|e| e.unwrap().file_name().to_string_lossy().to_string())
                .collect();
            v.sort();
            v
        };
        let before = snapshot(&dir);
        assert_eq!(before, vec!["fixture.zip".to_string()]);

        let _ = zipguard::inspect_archive(&archive);

        let after = snapshot(&dir);

        // 1. nothing new appeared (no extracted member, no temp output)
        assert_eq!(
            before, after,
            "inspection created or removed files in its own directory"
        );
        // 2. no archive member was extracted anywhere in the tree
        assert!(!dir.join("a.txt").exists(), "archive member was extracted");
        // 3. the archive itself is still present and byte-identical
        let after_bytes = fs::read(&archive).unwrap();
        assert_eq!(
            archive_bytes, after_bytes,
            "inspection modified the archive bytes"
        );

        fs::remove_dir_all(&dir).ok();
    }
}
