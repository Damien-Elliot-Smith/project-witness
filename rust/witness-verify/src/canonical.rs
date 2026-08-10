//! Move 77: strict canonical JSON and hashing tool.
//!
//! Byte-identical to the Python stack's canonicalization
//! (src/01_sentinel_core/sentinel_core/canonical.py):
//!   json.dumps(obj, sort_keys=True, separators=(",", ":"),
//!              ensure_ascii=False, allow_nan=False)
//! hashed as SHA-256 over the UTF-8 bytes. The recipe was proven before
//! this module was written: the three stored canonical_hash values of
//! the frozen Move 71 reference receipts were reproduced independently
//! in Python, and four cross-implementation vectors (exact canonical
//! string + digest, computed by CPython json.dumps + hashlib) are unit
//! tests below.
//!
//! Key ordering: Python sorts str keys by code point; Rust's &str Ord
//! is UTF-8 byte order, which is equivalent (UTF-8 preserves code
//! point order).
//!
//! Numbers: the Python stack emits integers only (a computed scan of
//! the frozen reference found zero floats). Reproducing CPython's
//! float repr is a known cross-language hazard, so this tool FAILS
//! CLOSED on any non-integer number instead of risking a silent hash
//! divergence.

use crate::json::Value;
use crate::sha256;

/// Serialize a value to the canonical string. Errors fail closed.
pub fn canonical_string(value: &Value) -> Result<String, String> {
    let mut out = String::new();
    write_value(value, &mut out)?;
    Ok(out)
}

/// Canonical SHA-256 (lowercase hex) of a value.
pub fn canonical_hash_hex(value: &Value) -> Result<String, String> {
    let text = canonical_string(value)?;
    Ok(sha256::digest_hex(text.as_bytes()))
}

fn write_value(value: &Value, out: &mut String) -> Result<(), String> {
    match value {
        Value::Null => {
            out.push_str("null");
            Ok(())
        }
        Value::Bool(true) => {
            out.push_str("true");
            Ok(())
        }
        Value::Bool(false) => {
            out.push_str("false");
            Ok(())
        }
        Value::Int(n) => {
            out.push_str(&n.to_string());
            Ok(())
        }
        Value::Number(_) => Err(
            "CANONICAL_FLOAT_UNSUPPORTED: non-integer number cannot be \
             canonicalized without risking divergence from CPython float \
             repr; the Python stack emits integers only"
                .to_string(),
        ),
        Value::Str(s) => {
            write_string(s, out);
            Ok(())
        }
        Value::Array(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                write_value(item, out)?;
            }
            out.push(']');
            Ok(())
        }
        Value::Object(pairs) => {
            let mut keys: Vec<&str> =
                pairs.iter().map(|(k, _)| k.as_str()).collect();
            keys.sort();
            out.push('{');
            for (i, key) in keys.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                write_string(key, out);
                out.push(':');
                let value = pairs
                    .iter()
                    .find(|(k, _)| k == key)
                    .map(|(_, v)| v)
                    .expect("key came from pairs");
                write_value(value, out)?;
            }
            out.push('}');
            Ok(())
        }
    }
}

/// Python json.dumps string escaping with ensure_ascii=False:
/// escape only backslash, double quote and control chars; short escapes
/// for \n \r \t \b \f; \u00XX for other controls; raw UTF-8 otherwise.
fn write_string(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{0008}' => out.push_str("\\b"),
            '\u{000c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::json;

    fn canon(doc: &str) -> String {
        canonical_string(&json::parse(doc).unwrap()).unwrap()
    }

    fn canon_hash(doc: &str) -> String {
        canonical_hash_hex(&json::parse(doc).unwrap()).unwrap()
    }

    // Vectors computed by CPython json.dumps + hashlib during Move 77
    // grounding. Any divergence from the Python recipe fails here.

    #[test]
    fn vector_sorting_and_literals() {
        let doc = "{\"b\": 1, \"a\": [true, null, \"x\"]}";
        assert_eq!(canon(doc), "{\"a\":[true,null,\"x\"],\"b\":1}");
        assert_eq!(
            canon_hash(doc),
            "54a65415ad370228851a1da4b31b6fd42dc58b19a50d35cae759325f7388ce64"
        );
    }

    #[test]
    fn vector_escapes_and_negative_int() {
        let doc =
            "{\"k\": \"a\\\"b\\\\c\\nd\\ttab\", \"n\": -7, \"z\": {}}";
        assert_eq!(
            canon(doc),
            "{\"k\":\"a\\\"b\\\\c\\nd\\ttab\",\"n\":-7,\"z\":{}}"
        );
        assert_eq!(
            canon_hash(doc),
            "213e6034aaf142048025d3f5e3c1c79d2ada87eb099f8dc7640a92b75b6559a6"
        );
    }

    #[test]
    fn vector_raw_utf8_not_escaped() {
        let doc = "{\"unicode\": \"héllo — ✓\", \"empty\": []}";
        assert_eq!(
            canon(doc),
            "{\"empty\":[],\"unicode\":\"héllo — ✓\"}"
        );
        assert_eq!(
            canon_hash(doc),
            "35584bf955af9a61edcaab973b4dd446f9bc16ed625e0cc3218b1a18e084d3f0"
        );
    }

    #[test]
    fn vector_nested_and_slash_unescaped() {
        let doc = "{\"nested\": {\"deep\": [0, {\"i\": 42}]}, \
                   \"s\": \"/slash unescaped/\"}";
        assert_eq!(
            canon(doc),
            "{\"nested\":{\"deep\":[0,{\"i\":42}]},\"s\":\"/slash unescaped/\"}"
        );
        assert_eq!(
            canon_hash(doc),
            "9e28e4e447eb2e324cb3fedcc92da99af7846ee7f0379947bd41f0278e957f8f"
        );
    }

    #[test]
    fn floats_fail_closed() {
        let parsed = json::parse("{\"x\": 1.5}").unwrap();
        assert!(canonical_string(&parsed).is_err());
    }

    #[test]
    fn integers_stay_integers() {
        assert_eq!(canon("{\"i\": 42, \"neg\": -1, \"zero\": 0}"),
                   "{\"i\":42,\"neg\":-1,\"zero\":0}");
    }
}
