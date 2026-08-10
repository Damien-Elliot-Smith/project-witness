#!/usr/bin/env python3
"""Move 83 — Rust source sanity check.

This exists because a Python focused suite passing 182/182 said nothing
about whether the modified Rust source was even syntactically valid. A
prior candidate shipped a `DIGEST_SCOPE_BUNDLE` constant whose first
string literal terminated early, leaving English prose sitting outside any
literal as bare Rust tokens. Brace, paren and bracket balance was
unaffected, so a delimiter-counting check could not see it.

**This is not a Rust compiler and does not establish buildability.** Only
`cargo build` and `cargo test` in the adoption gate do that. What this
does is catch gross string-literal and prose-outside-source corruption
cheaply, before the long gate runs.

Two checks:

1. **String-constant shape.** Every `const NAME: &str = ...;` block must
   contain exactly one string literal, and nothing may sit between that
   literal's closing quote and the terminating semicolon.
2. **Prose outside string literals.** After removing comments, string
   literals and char literals, no run of three or more consecutive bare
   identifiers may contain two or more non-keywords. Valid Rust produces
   runs like `pub const fn` (all keywords) or `let mut out` (one
   non-keyword); English prose such as `they are counted separately in`
   produces four non-keywords in a row.
"""

import argparse
import os
import re
import sys

RUST_KEYWORDS = frozenset("""
as async await break const continue crate dyn else enum extern false fn
for if impl in let loop match mod move mut pub ref return self Self static
struct super trait true type unsafe use where while
""".split())


class RustSourceError(Exception):
    """Deterministic, message-only failure."""


def strip_literals_and_comments(source):
    """Return the source with comments, string literals and char literals
    replaced by spaces, preserving offsets so line numbers stay usable."""
    out = []
    i = 0
    n = len(source)
    while i < n:
        c = source[i]
        # line comment
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            while i < n and source[i] != "\n":
                out.append(" ")
                i += 1
            continue
        # block comment
        if c == "/" and i + 1 < n and source[i + 1] == "*":
            depth = 1
            out.append("  ")
            i += 2
            while i < n and depth:
                if source.startswith("/*", i):
                    depth += 1
                    out.append("  ")
                    i += 2
                elif source.startswith("*/", i):
                    depth -= 1
                    out.append("  ")
                    i += 2
                else:
                    out.append(" " if source[i] != "\n" else "\n")
                    i += 1
            continue
        # raw string literal: r"..." / r#"..."# / br##"..."##
        raw = re.match(r'(b?r)(#*)"', source[i:])
        if raw and (i == 0 or not (source[i - 1].isalnum()
                                   or source[i - 1] == "_")):
            hashes = raw.group(2)
            terminator = '"' + hashes
            body_start = i + raw.end()
            end = source.find(terminator, body_start)
            if end == -1:
                end = n
                stop = n
            else:
                stop = end + len(terminator)
            for k in range(i, stop):
                out.append("\n" if source[k] == "\n" else " ")
            i = stop
            continue
        # byte string prefix
        if c == "b" and i + 1 < n and source[i + 1] == '"':
            out.append(" ")
            i += 1
            continue
        # string literal
        if c == '"':
            out.append(" ")
            i += 1
            while i < n:
                if source[i] == "\\":
                    out.append("  " if source[i + 1:i + 2] != "\n"
                               else " \n")
                    i += 2
                    continue
                if source[i] == '"':
                    out.append(" ")
                    i += 1
                    break
                out.append(" " if source[i] != "\n" else "\n")
                i += 1
            continue
        # char literal or lifetime
        if c == "'":
            if source.startswith("'\\", i):
                end = source.find("'", i + 2)
                if end != -1 and end - i <= 6:
                    out.append(" " * (end - i + 1))
                    i = end + 1
                    continue
            elif i + 2 < n and source[i + 2] == "'":
                out.append("   ")
                i += 3
                continue
            # lifetime: leave the tick, it reads as punctuation
            out.append(" ")
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def check_string_constants(source, path):
    """Every `const NAME: &str = <one literal>;` must be exactly that."""
    problems = []
    for match in re.finditer(r"const\s+([A-Z][A-Z0-9_]*)\s*:\s*&(?:'static\s+)?str\s*=",
                             source):
        name = match.group(1)
        start = match.end()
        # find the terminating semicolon that is NOT inside a literal
        masked = strip_literals_and_comments(source)
        end = masked.find(";", start)
        if end == -1:
            problems.append("%s: constant %s has no terminating semicolon"
                            % (path, name))
            continue
        block = source[start:end]
        literals = re.findall(r'"((?:[^"\\]|\\.)*)"', block, re.S)
        if len(literals) != 1:
            problems.append(
                "%s: constant %s contains %d string literals; a &str "
                "constant must contain exactly one"
                % (path, name, len(literals)))
            continue
        closing = block.rfind('"')
        trailing = block[closing + 1:].strip()
        if trailing:
            problems.append(
                "%s: constant %s has stray tokens between the closing "
                "quote and the semicolon: %r"
                % (path, name, trailing[:60]))
    return problems


def check_no_prose_outside_literals(source, path):
    """Prose left outside a string literal reads as bare identifiers."""
    problems = []
    code = strip_literals_and_comments(source)
    for line_no, line in enumerate(code.splitlines(), start=1):
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", line)
        # walk runs of identifiers separated only by whitespace
        for run in re.finditer(
                r"(?:[A-Za-z_][A-Za-z0-9_]*)(?:\s+[A-Za-z_][A-Za-z0-9_]*){2,}",
                line):
            words = run.group(0).split()
            non_keywords = [w for w in words if w not in RUST_KEYWORDS]
            if len(non_keywords) >= 3:
                problems.append(
                    "%s:%d: %d consecutive non-keyword identifiers look "
                    "like prose outside a string literal: %r"
                    % (path, line_no, len(non_keywords),
                       run.group(0)[:60]))
        del tokens
    return problems


def check_quote_balance(source, path):
    """An odd number of literal-delimiting quotes means a literal is
    unterminated somewhere."""
    problems = []
    stripped = strip_literals_and_comments(source)
    if '"' in stripped:
        problems.append(
            "%s: a double quote survives literal stripping, so a string "
            "literal is unterminated" % path)
    return problems


def check_file(path):
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    problems = []
    problems.extend(check_quote_balance(source, os.path.basename(path)))
    problems.extend(check_string_constants(source, os.path.basename(path)))
    problems.extend(
        check_no_prose_outside_literals(source, os.path.basename(path)))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Move 83 Rust source sanity check (NOT a compiler)")
    parser.add_argument("--source", action="append", required=True,
                        help="absolute path to a .rs file (repeatable)")
    args = parser.parse_args(argv)

    problems = []
    for path in args.source:
        if not os.path.isabs(path):
            print("usage error: --source must be absolute: %s" % path)
            return 2
        if not os.path.isfile(path):
            print("usage error: not a regular file: %s" % path)
            return 2
        try:
            problems.extend(check_file(path))
        except (OSError, UnicodeDecodeError) as exc:
            print("RUST_SOURCE_PROBLEM: %s: unreadable (%s)"
                  % (os.path.basename(path), exc))
            problems.append("unreadable")

    for problem in sorted(set(problems)):
        print("RUST_SOURCE_PROBLEM: %s" % problem)
    if problems:
        print("MOVE_83_RUST_SOURCE_SANITY: FAIL (%d problem(s))"
              % len(set(problems)))
        return 1
    print("MOVE_83_RUST_SOURCE_SANITY: PASS (this is a syntax sanity "
          "check and does not establish Rust buildability)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
