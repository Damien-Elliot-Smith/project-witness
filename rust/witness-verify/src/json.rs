//! Minimal strict JSON parser (stdlib only, zero external crates).
//!
//! Scope: parse the small, canonical JSON documents the Python stack
//! writes. Strictness choices are deliberate and deterministic:
//! duplicate object keys are an error, trailing content is an error,
//! and only standard JSON escapes are accepted. This module prefigures
//! the Step 77 canonical JSON tool; at Step 74 it only needs to parse.

#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Int(i64),
    Number(f64),
    Str(String),
    Array(Vec<Value>),
    Object(Vec<(String, Value)>),
}

impl Value {
    /// Look up a key in an object value.
    pub fn get(&self, key: &str) -> Option<&Value> {
        match self {
            Value::Object(pairs) => {
                for (k, v) in pairs {
                    if k == key {
                        return Some(v);
                    }
                }
                None
            }
            _ => None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Value::Str(s) => Some(s.as_str()),
            _ => None,
        }
    }

    pub fn object_keys(&self) -> Vec<String> {
        match self {
            Value::Object(pairs) => {
                pairs.iter().map(|(k, _)| k.clone()).collect()
            }
            _ => Vec::new(),
        }
    }

    pub fn is_object(&self) -> bool {
        matches!(self, Value::Object(_))
    }

    pub fn as_array(&self) -> Option<&Vec<Value>> {
        match self {
            Value::Array(items) => Some(items),
            _ => None,
        }
    }

    pub fn as_number(&self) -> Option<f64> {
        match self {
            Value::Int(n) => Some(*n as f64),
            Value::Number(n) => Some(*n),
            _ => None,
        }
    }
}

pub fn parse(input: &str) -> Result<Value, String> {
    let chars: Vec<char> = input.chars().collect();
    let mut pos: usize = 0;
    skip_ws(&chars, &mut pos);
    let value = parse_value(&chars, &mut pos)?;
    skip_ws(&chars, &mut pos);
    if pos != chars.len() {
        return Err(format!("trailing content at position {}", pos));
    }
    Ok(value)
}

fn skip_ws(chars: &[char], pos: &mut usize) {
    while *pos < chars.len() {
        let c = chars[*pos];
        if c == ' ' || c == '\t' || c == '\n' || c == '\r' {
            *pos += 1;
        } else {
            break;
        }
    }
}

fn peek(chars: &[char], pos: usize) -> Result<char, String> {
    if pos < chars.len() {
        Ok(chars[pos])
    } else {
        Err("unexpected end of input".to_string())
    }
}

fn parse_value(chars: &[char], pos: &mut usize) -> Result<Value, String> {
    let c = peek(chars, *pos)?;
    match c {
        '{' => parse_object(chars, pos),
        '[' => parse_array(chars, pos),
        '"' => {
            let s = parse_string(chars, pos)?;
            Ok(Value::Str(s))
        }
        't' => parse_literal(chars, pos, "true", Value::Bool(true)),
        'f' => parse_literal(chars, pos, "false", Value::Bool(false)),
        'n' => parse_literal(chars, pos, "null", Value::Null),
        '-' | '0'..='9' => parse_number(chars, pos),
        other => Err(format!("unexpected character {:?}", other)),
    }
}

fn parse_literal(
    chars: &[char],
    pos: &mut usize,
    word: &str,
    value: Value,
) -> Result<Value, String> {
    for expected in word.chars() {
        let c = peek(chars, *pos)?;
        if c != expected {
            return Err(format!("invalid literal, expected {}", word));
        }
        *pos += 1;
    }
    Ok(value)
}

fn parse_number(chars: &[char], pos: &mut usize) -> Result<Value, String> {
    let start = *pos;
    if peek(chars, *pos)? == '-' {
        *pos += 1;
    }
    while *pos < chars.len() {
        let c = chars[*pos];
        if c.is_ascii_digit() || c == '.' || c == 'e' || c == 'E'
            || c == '+' || c == '-'
        {
            *pos += 1;
        } else {
            break;
        }
    }
    let text: String = chars[start..*pos].iter().collect();
    let is_integral = !text.contains('.')
        && !text.contains('e')
        && !text.contains('E');
    if is_integral {
        if let Ok(n) = text.parse::<i64>() {
            return Ok(Value::Int(n));
        }
        // integral but outside i64: keep as float so the canonical
        // serializer rejects it (fail closed) rather than lose bits
    }
    match text.parse::<f64>() {
        Ok(n) => Ok(Value::Number(n)),
        Err(_) => Err(format!("invalid number {:?}", text)),
    }
}

fn parse_hex4(chars: &[char], pos: &mut usize) -> Result<u32, String> {
    let mut code: u32 = 0;
    for _ in 0..4 {
        let c = peek(chars, *pos)?;
        let digit = c.to_digit(16);
        match digit {
            Some(d) => {
                code = code * 16 + d;
                *pos += 1;
            }
            None => return Err("invalid \\u escape".to_string()),
        }
    }
    Ok(code)
}

fn parse_string(chars: &[char], pos: &mut usize) -> Result<String, String> {
    if peek(chars, *pos)? != '"' {
        return Err("expected string".to_string());
    }
    *pos += 1;
    let mut out = String::new();
    loop {
        let c = peek(chars, *pos)?;
        *pos += 1;
        if c == '"' {
            return Ok(out);
        }
        if c == '\\' {
            let esc = peek(chars, *pos)?;
            *pos += 1;
            match esc {
                '"' => out.push('"'),
                '\\' => out.push('\\'),
                '/' => out.push('/'),
                'b' => out.push('\u{0008}'),
                'f' => out.push('\u{000c}'),
                'n' => out.push('\n'),
                'r' => out.push('\r'),
                't' => out.push('\t'),
                'u' => {
                    let hi = parse_hex4(chars, pos)?;
                    let code: u32;
                    if (0xD800..=0xDBFF).contains(&hi) {
                        if peek(chars, *pos)? != '\\' {
                            return Err("lone high surrogate".to_string());
                        }
                        *pos += 1;
                        if peek(chars, *pos)? != 'u' {
                            return Err("lone high surrogate".to_string());
                        }
                        *pos += 1;
                        let lo = parse_hex4(chars, pos)?;
                        if !(0xDC00..=0xDFFF).contains(&lo) {
                            return Err("invalid surrogate pair".to_string());
                        }
                        code = 0x10000
                            + ((hi - 0xD800) << 10)
                            + (lo - 0xDC00);
                    } else if (0xDC00..=0xDFFF).contains(&hi) {
                        return Err("lone low surrogate".to_string());
                    } else {
                        code = hi;
                    }
                    match char::from_u32(code) {
                        Some(ch) => out.push(ch),
                        None => {
                            return Err("invalid unicode escape".to_string())
                        }
                    }
                }
                other => {
                    return Err(format!("invalid escape \\{}", other));
                }
            }
        } else if (c as u32) < 0x20 {
            return Err("unescaped control character in string".to_string());
        } else {
            out.push(c);
        }
    }
}

fn parse_array(chars: &[char], pos: &mut usize) -> Result<Value, String> {
    *pos += 1; // consume '['
    let mut items: Vec<Value> = Vec::new();
    skip_ws(chars, pos);
    if peek(chars, *pos)? == ']' {
        *pos += 1;
        return Ok(Value::Array(items));
    }
    loop {
        skip_ws(chars, pos);
        let value = parse_value(chars, pos)?;
        items.push(value);
        skip_ws(chars, pos);
        let c = peek(chars, *pos)?;
        *pos += 1;
        if c == ']' {
            return Ok(Value::Array(items));
        }
        if c != ',' {
            return Err("expected ',' or ']' in array".to_string());
        }
    }
}

fn parse_object(chars: &[char], pos: &mut usize) -> Result<Value, String> {
    *pos += 1; // consume '{'
    let mut pairs: Vec<(String, Value)> = Vec::new();
    skip_ws(chars, pos);
    if peek(chars, *pos)? == '}' {
        *pos += 1;
        return Ok(Value::Object(pairs));
    }
    loop {
        skip_ws(chars, pos);
        let key = parse_string(chars, pos)?;
        for (existing, _) in &pairs {
            if existing == &key {
                return Err(format!("duplicate object key {:?}", key));
            }
        }
        skip_ws(chars, pos);
        if peek(chars, *pos)? != ':' {
            return Err("expected ':' in object".to_string());
        }
        *pos += 1;
        skip_ws(chars, pos);
        let value = parse_value(chars, pos)?;
        pairs.push((key, value));
        skip_ws(chars, pos);
        let c = peek(chars, *pos)?;
        *pos += 1;
        if c == '}' {
            return Ok(Value::Object(pairs));
        }
        if c != ',' {
            return Err("expected ',' or '}' in object".to_string());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_reference_shaped_object() {
        let doc = "{\"a\": \"x\", \"b\": [1, 2], \"c\": {\"d\": null}, \
                   \"e\": true, \"f\": -1.5e2}";
        let v = parse(doc).unwrap();
        assert!(v.is_object());
        assert_eq!(v.get("a").and_then(|x| x.as_str()), Some("x"));
        assert_eq!(v.get("e"), Some(&Value::Bool(true)));
    }

    #[test]
    fn rejects_duplicate_keys() {
        assert!(parse("{\"a\": 1, \"a\": 2}").is_err());
    }

    #[test]
    fn rejects_trailing_content() {
        assert!(parse("{} extra").is_err());
    }

    #[test]
    fn rejects_malformed_documents() {
        assert!(parse("{\"a\": }").is_err());
        assert!(parse("[1, 2").is_err());
        assert!(parse("").is_err());
        assert!(parse("nul").is_err());
    }

    #[test]
    fn handles_escapes() {
        let v = parse("{\"k\": \"a\\n\\\"b\\u0041\"}").unwrap();
        assert_eq!(v.get("k").and_then(|x| x.as_str()), Some("a\n\"bA"));
    }
}
