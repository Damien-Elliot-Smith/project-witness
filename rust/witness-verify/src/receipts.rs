//! Move 76: receipt chain verification (declared-value layer).
//!
//! Verifies the Sentinel receipt chain in
//! coordinator_output/sentinel_run/sentinel_run.json, mirroring the
//! declared-value checks of Python's ReceiptChain.verify_chain
//! (src/01_sentinel_core/sentinel_core/receipts.py): receipt order and
//! IDs, GENESIS start, prior-hash linkage, run_id and manifest_hash
//! consistency, seal cross-checks, session continuity, duplicate and
//! malformed receipt detection, and hash field formats.
//!
//! DEPTH HONESTY - what this stage does NOT do: it does not recompute
//! any receipt's canonical_hash, the manifest_hash, or the seal_hash,
//! because recomputation requires the canonical JSON serialization
//! that is Step 77's scope. Linkage here is verified against DECLARED
//! hash values only. A tamperer who rewrites a receipt AND its
//! declared canonical_hash AND every downstream prior_hash link is
//! NOT caught at this stage; Python catches that case by
//! recomputation, and Rust will at Step 77. The verdict therefore
//! stays INCONCLUSIVE for the remaining layers. As of Move 77, each
//! receipt's canonical_hash IS recomputed via the canonical JSON tool
//! and compared to the declared value, closing the Move 76
//! declared-value blind spot for receipts; manifest_hash and
//! seal_hash recomputation are deferred to their own grounded move.

use std::fs;
use std::path::Path;

use crate::canonical;
use crate::json;

const RUN_RECORD: &str = "coordinator_output/sentinel_run/sentinel_run.json";

/// The 21 receipt keys of the frozen reference (computed at grounding;
/// enforced against the reference by the alignment guard).
pub const RECEIPT_KEYS: [&str; 21] = [
    "action_schema_version",
    "canonical_hash",
    "decision",
    "detail",
    "executed",
    "impl_version",
    "intent_hash",
    "intent_receipt_id",
    "manifest_hash",
    "policy_version",
    "post_session_state",
    "pre_session_state",
    "prior_hash",
    "reason_code",
    "reason_registry_version",
    "receipt_id",
    "receipt_schema_version",
    "request",
    "run_id",
    "session_version",
    "stage",
];

pub type Failure = (String, String);

fn fail(code: &str, detail: String) -> Failure {
    (code.to_string(), detail)
}

fn is_hex64_lower(s: &str) -> bool {
    s.len() == 64
        && s.chars()
            .all(|c| c.is_ascii_digit() || ('a'..='f').contains(&c))
}

fn get_str<'a>(
    obj: &'a json::Value,
    key: &str,
    context: &str,
) -> Result<&'a str, Failure> {
    match obj.get(key).and_then(|v| v.as_str()) {
        Some(s) => Ok(s),
        None => Err(fail(
            "RECEIPT_MALFORMED",
            format!("{}: field {} missing or not a string", context, key),
        )),
    }
}

/// Verify the declared-value receipt chain. Returns receipt count.
pub fn verify_receipt_chain(bundle: &Path) -> Result<usize, Failure> {
    let path = bundle.join(RUN_RECORD);
    if !path.is_file() {
        return Err(fail(
            "RUN_RECORD_MISSING",
            format!("{} is missing", RUN_RECORD),
        ));
    }
    let text = match fs::read_to_string(&path) {
        Ok(text) => text,
        Err(err) => {
            return Err(fail(
                "RUN_RECORD_READ_ERROR",
                format!("could not read {}: {}", RUN_RECORD, err),
            ));
        }
    };
    let doc = match json::parse(&text) {
        Ok(value) => value,
        Err(err) => {
            return Err(fail(
                "RUN_RECORD_JSON_INVALID",
                format!("{}: {}", RUN_RECORD, err),
            ));
        }
    };

    let manifest = match doc.get("manifest") {
        Some(m) if m.is_object() => m,
        _ => {
            return Err(fail(
                "RUN_RECORD_MALFORMED",
                "manifest missing or not an object".to_string(),
            ));
        }
    };
    let manifest_hash =
        get_str(manifest, "manifest_hash", "run manifest")?;
    let manifest_run_id = get_str(manifest, "run_id", "run manifest")?;

    let receipts = match doc.get("receipts").and_then(|v| v.as_array()) {
        Some(items) => items,
        None => {
            return Err(fail(
                "RECEIPTS_MISSING",
                "receipts array missing or not an array".to_string(),
            ));
        }
    };
    if receipts.is_empty() {
        return Err(fail(
            "RECEIPTS_MISSING",
            "receipts array is empty".to_string(),
        ));
    }

    let mut prev_canonical: Option<String> = None;
    let mut prev_post_state: Option<String> = None;

    for (i, receipt) in receipts.iter().enumerate() {
        let context = format!("receipt #{}", i);
        if !receipt.is_object() {
            return Err(fail(
                "RECEIPT_MALFORMED",
                format!("{} is not an object", context),
            ));
        }
        // exact key set: missing keys and unknown keys both fail
        let mut keys = receipt.object_keys();
        keys.sort();
        let expected: Vec<String> =
            RECEIPT_KEYS.iter().map(|k| k.to_string()).collect();
        if keys != expected {
            return Err(fail(
                "RECEIPT_MALFORMED",
                format!("{}: key set differs from reference contract", context),
            ));
        }

        let receipt_id = match receipt
            .get("receipt_id")
            .and_then(|v| v.as_number())
        {
            Some(n) => n,
            None => {
                return Err(fail(
                    "RECEIPT_MALFORMED",
                    format!("{}: receipt_id missing or not a number", context),
                ));
            }
        };
        if receipt_id != i as f64 {
            return Err(fail(
                "RECEIPT_ID_SEQUENCE_BROKEN",
                format!(
                    "expected receipt_id {} at position {}, found {}",
                    i, i, receipt_id
                ),
            ));
        }

        let run_id = get_str(receipt, "run_id", &context)?;
        if run_id != manifest_run_id {
            return Err(fail(
                "RECEIPT_RUN_ID_MISMATCH",
                format!("{}: run_id differs from manifest", context),
            ));
        }
        let receipt_manifest_hash =
            get_str(receipt, "manifest_hash", &context)?;
        if receipt_manifest_hash != manifest_hash {
            return Err(fail(
                "RECEIPT_MANIFEST_HASH_MISMATCH",
                format!("{}: manifest_hash differs from manifest", context),
            ));
        }

        let canonical = get_str(receipt, "canonical_hash", &context)?;
        if !is_hex64_lower(canonical) {
            return Err(fail(
                "RECEIPT_HASH_MALFORMED",
                format!("{}: canonical_hash is not 64 lowercase hex", context),
            ));
        }
        let prior = get_str(receipt, "prior_hash", &context)?;
        if i == 0 {
            if prior != "GENESIS" {
                return Err(fail(
                    "GENESIS_PRIOR_HASH_INVALID",
                    "receipt #0 prior_hash is not 'GENESIS'".to_string(),
                ));
            }
        } else {
            if !is_hex64_lower(prior) {
                return Err(fail(
                    "RECEIPT_HASH_MALFORMED",
                    format!("{}: prior_hash is not 64 lowercase hex", context),
                ));
            }
            let expected_prior = prev_canonical.as_deref().unwrap_or("");
            if prior != expected_prior {
                return Err(fail(
                    "RECEIPT_LINKAGE_BROKEN",
                    format!(
                        "{}: prior_hash does not match declared \
                         canonical_hash of receipt #{}",
                        context,
                        i - 1
                    ),
                ));
            }
        }

        let pre_state = get_str(receipt, "pre_session_state", &context)?;
        if let Some(prev_post) = prev_post_state.as_deref() {
            if pre_state != prev_post {
                return Err(fail(
                    "SESSION_CONTINUITY_BROKEN",
                    format!(
                        "receipt #{} pre_session_state does not match \
                         receipt #{} post_session_state",
                        i,
                        i - 1
                    ),
                ));
            }
        }
        let post_state = get_str(receipt, "post_session_state", &context)?;
        prev_post_state = Some(post_state.to_string());

        // Move 77: recompute the canonical hash over the receipt's
        // hashable payload (all fields except canonical_hash itself,
        // mirroring Python Receipt._hashable_payload) and require it to
        // match the declared value. Runs AFTER the structural chain
        // checks so a structural break surfaces its own reason code.
        let payload_pairs: Vec<(String, json::Value)> = match receipt {
            json::Value::Object(pairs) => pairs
                .iter()
                .filter(|(k, _)| k != "canonical_hash")
                .cloned()
                .collect(),
            _ => Vec::new(),
        };
        let payload = json::Value::Object(payload_pairs);
        let recomputed = match canonical::canonical_hash_hex(&payload) {
            Ok(hex) => hex,
            Err(err) => {
                return Err(fail(
                    "RECEIPT_CANONICALIZATION_ERROR",
                    format!("{}: {}", context, err),
                ));
            }
        };
        if recomputed != canonical {
            return Err(fail(
                "RECEIPT_HASH_RECOMPUTATION_MISMATCH",
                format!(
                    "{}: recomputed canonical hash does not match \
                     declared canonical_hash",
                    context
                ),
            ));
        }
        prev_canonical = Some(canonical.to_string());
    }

    let seal = match doc.get("run_seal") {
        Some(s) if s.is_object() => s,
        _ => {
            return Err(fail(
                "SEAL_MISSING",
                "run_seal missing or not an object".to_string(),
            ));
        }
    };
    let seal_count = match seal.get("receipt_count").and_then(|v| v.as_number())
    {
        Some(n) => n,
        None => {
            return Err(fail(
                "SEAL_MALFORMED",
                "seal receipt_count missing or not a number".to_string(),
            ));
        }
    };
    if seal_count != receipts.len() as f64 {
        return Err(fail(
            "SEAL_MISMATCH",
            format!(
                "seal receipt_count {} but chain has {} receipts",
                seal_count,
                receipts.len()
            ),
        ));
    }
    let final_id = match seal
        .get("final_receipt_id")
        .and_then(|v| v.as_number())
    {
        Some(n) => n,
        None => {
            return Err(fail(
                "SEAL_MALFORMED",
                "seal final_receipt_id missing or not a number".to_string(),
            ));
        }
    };
    if final_id != (receipts.len() - 1) as f64 {
        return Err(fail(
            "SEAL_MISMATCH",
            "seal final_receipt_id does not match last receipt".to_string(),
        ));
    }
    let final_hash = get_str(seal, "final_receipt_hash", "run seal")?;
    if Some(final_hash.to_string()) != prev_canonical {
        return Err(fail(
            "SEAL_MISMATCH",
            "seal final_receipt_hash does not match declared \
             canonical_hash of the last receipt"
                .to_string(),
        ));
    }
    let seal_manifest_hash = get_str(seal, "manifest_hash", "run seal")?;
    if seal_manifest_hash != manifest_hash {
        return Err(fail(
            "SEAL_MISMATCH",
            "seal manifest_hash differs from manifest".to_string(),
        ));
    }

    Ok(receipts.len())
}
