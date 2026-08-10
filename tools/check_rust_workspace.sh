#!/bin/sh
# check_rust_workspace.sh — Rust workspace checker (three-valued verdict).
# Contract tracked: Move 78 (zipguard archive safety). Update the
# banner and contract rules with each Rust move; stale banners/headers
# have been repeated external-review findings, so the banner is now
# also checked against VERSION.
#
# Verdicts, following the PASS/FAIL/INCONCLUSIVE model established in the
# project's earlier AletheiaGate work:
#   PASS          structural checks passed AND cargo build + cargo test
#                 passed on this machine (exit 0)
#   FAIL          a structural check failed, or the toolchain is present
#                 and build/test failed (exit 1)
#   INCONCLUSIVE  structural checks passed but no Rust toolchain is
#                 available here, so build/test could not run (exit 3)
#
# INCONCLUSIVE is not success. A machine without cargo cannot claim the
# workspace builds; it can only claim the declared structure and the
# zero-external-dependency policy hold. Never treat exit 3 as green.

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2

fail=0
ok()  { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; fail=1; }

echo "Rust workspace check (current contract: Move 79 diagnostics)"
echo "------------------------------"

echo "Structural checks:"
[ -f rust/Cargo.toml ] && ok "rust/Cargo.toml exists" \
    || bad "rust/Cargo.toml exists"
[ -f rust/witness-verify/Cargo.toml ] && ok "member crate manifest exists" \
    || bad "member crate manifest exists"
[ -f rust/witness-verify/src/main.rs ] && ok "member crate main.rs exists" \
    || bad "member crate main.rs exists"
[ -f rust/README.md ] && ok "rust/README.md exists" \
    || bad "rust/README.md exists"

grep -q '^members = \["witness-verify"\]' rust/Cargo.toml \
    && ok "workspace declares witness-verify member" \
    || bad "workspace declares witness-verify member"

# Zero-external-dependency policy: nothing may follow [dependencies]
# in any crate manifest except blank lines, comments, or the next section.
deps=$(awk '/^\[dependencies\]/{f=1;next} /^\[/{f=0} f && NF && $0 !~ /^#/' \
    rust/witness-verify/Cargo.toml)
if [ -z "$deps" ]; then
    ok "zero external crates declared"
else
    bad "external dependencies declared: $deps"
fi

# Fail-closed contract (Move 73): exit 0 is reserved for a real PASS and
# must be unreachable in the skeleton; INCONCLUSIVE and FAIL exits are
# named constants; the no-checks reason code must be present.
grep -q 'const EXIT_INCONCLUSIVE: i32 = 3' rust/witness-verify/src/main.rs \
    && ok "INCONCLUSIVE exit constant is 3" \
    || bad "INCONCLUSIVE exit constant is 3"
grep -q 'const EXIT_FAIL: i32 = 1' rust/witness-verify/src/main.rs \
    && ok "FAIL exit constant is 1" \
    || bad "FAIL exit constant is 1"
grep -q 'RECEIPT_CHAIN_HASHES_RECOMPUTED' rust/witness-verify/src/main.rs \
    && ok "recomputed receipt hashes yield INCONCLUSIVE, not PASS" \
    || bad "recomputed receipt hashes yield INCONCLUSIVE, not PASS"
[ -f rust/witness-verify/src/canonical.rs ] \
    && ok "canonical JSON module present" \
    || bad "canonical JSON module present"
grep -q 'CANONICAL_FLOAT_UNSUPPORTED' rust/witness-verify/src/canonical.rs \
    && ok "canonical tool fails closed on floats" \
    || bad "canonical tool fails closed on floats"
grep -q 'RECEIPT_HASH_RECOMPUTATION_MISMATCH' rust/witness-verify/src/receipts.rs \
    && ok "receipt hash recomputation present" \
    || bad "receipt hash recomputation present"
[ -f rust/witness-verify/src/zipguard.rs ] \
    && ok "zipguard module present" \
    || bad "zipguard module present"
grep -q 'ARCHIVE_SAFETY_OK' rust/witness-verify/src/main.rs \
    && ok "clean archive yields INCONCLUSIVE, not PASS" \
    || bad "clean archive yields INCONCLUSIVE, not PASS"
grep -q 'inspect-archive' rust/witness-verify/src/main.rs \
    && ok "inspect-archive command present" \
    || bad "inspect-archive command present"
grep -q 'fn evaluate_bundle' rust/witness-verify/src/main.rs \
    && ok "existing verify command preserved" \
    || bad "existing verify command preserved"
grep -q 'never decompress\|NEVER decompress\|never extract' rust/witness-verify/src/zipguard.rs \
    && ok "read-only no-extraction stated in code" \
    || bad "read-only no-extraction stated in code"
grep -q 'fn validate_local_header' rust/witness-verify/src/zipguard.rs \
    && ok "local-header validation present" \
    || bad "local-header validation present"
grep -q 'ARCHIVE_LOCAL_HEADER_MISMATCH' rust/witness-verify/src/zipguard.rs \
    && ok "local/central mismatch detection present" \
    || bad "local/central mismatch detection present"
grep -q 'local_header_name_mismatch_fails' rust/witness-verify/src/main.rs \
    && ok "central/local mismatch test present" \
    || bad "central/local mismatch test present"
grep -q 'unicode_path_extra_field_fails_closed' rust/witness-verify/src/main.rs \
    && ok "extra-field fail-closed test present" \
    || bad "extra-field fail-closed test present"
grep -q 'dot_component_collision_fails' rust/witness-verify/src/main.rs \
    && ok "dot-component test present" \
    || bad "dot-component test present"
grep -q 'repeated_separator_fails' rust/witness-verify/src/main.rs \
    && ok "repeated-separator test present" \
    || bad "repeated-separator test present"
grep -q 'validate_path_components' rust/witness-verify/src/zipguard.rs \
    && ok "hardened path-component validation present" \
    || bad "hardened path-component validation present"
# v3 repairs (hostile review): each required capability is checked
grep -q 'fn is_non_ascii' rust/witness-verify/src/zipguard.rs \
    && ok "all non-ASCII names fail closed (no unsound heuristic)" \
    || bad "all non-ASCII names fail closed (no unsound heuristic)"
if grep -q 'fn has_combining_mark' rust/witness-verify/src/zipguard.rs; then
    bad "unsound combining-mark heuristic removed"
else
    ok "unsound combining-mark heuristic removed"
fi
grep -q 'local version-needed {} != central' rust/witness-verify/src/zipguard.rs \
    && ok "local/central version-needed comparison present" \
    || bad "local/central version-needed comparison present"
grep -q 'entries consumed' rust/witness-verify/src/zipguard.rs \
    && ok "exact central-directory boundary check present" \
    || bad "exact central-directory boundary check present"
grep -q 'entry disk-start' rust/witness-verify/src/zipguard.rs \
    && ok "entry disk-start check present" \
    || bad "entry disk-start check present"
grep -q 'every ancestor prefix of this entry must be a directory' rust/witness-verify/src/zipguard.rs \
    && ok "file/dir collision ordered before case collision" \
    || bad "file/dir collision ordered before case collision"
grep -q 'non_ascii_precomposed_uppercase_fails' rust/witness-verify/src/main.rs \
    && ok "precomposed non-ASCII test present" \
    || bad "precomposed non-ASCII test present"
grep -q 'local_version_needed_mismatch_fails' rust/witness-verify/src/main.rs \
    && ok "local version-needed mismatch test present" \
    || bad "local version-needed mismatch test present"
grep -q 'local_unicode_path_extra_fails_closed' rust/witness-verify/src/main.rs \
    && ok "local extra-field fail-closed test present" \
    || bad "local extra-field fail-closed test present"
# stale wording forbidden
if grep -rq 'ONLY the ZIP central\|parses ONLY the ZIP central directory' rust/; then
    bad "rust/ free of stale ONLY-central-directory wording"
else
    ok "rust/ free of stale ONLY-central-directory wording"
fi
# v4 repairs (second hostile-review round)
grep -q 'raw_flags: u16' rust/witness-verify/src/zipguard.rs \
    && ok "raw central flags stored" || bad "raw central flags stored"
grep -q 'l_flags != e.raw_flags' rust/witness-verify/src/zipguard.rs \
    && ok "raw flags exactly compared" || bad "raw flags exactly compared"
grep -q 'SUPPORTED_FLAG_MASK' rust/witness-verify/src/zipguard.rs \
    && ok "unsupported flag mask enforced" || bad "unsupported flag mask enforced"
grep -q 'flags_unknown_bit_fails_closed' rust/witness-verify/src/main.rs \
    && ok "unsupported flag test present" || bad "unsupported flag test present"
grep -q 'file_prefixes' rust/witness-verify/src/zipguard.rs \
    && ok "parent-prefix collision tracking present" || bad "parent-prefix collision tracking present"
grep -q 'file_then_dir_prefix_collision' rust/witness-verify/src/main.rs \
    && ok "parent-prefix collision test present" || bad "parent-prefix collision test present"
grep -q 'local/central CRC-32' rust/witness-verify/src/zipguard.rs \
    && ok "CRC comparison present" || bad "CRC comparison present"
grep -q 'compressed size disagree' rust/witness-verify/src/zipguard.rs \
    && ok "size comparison present" || bad "size comparison present"
grep -q 'entry data ends at' rust/witness-verify/src/zipguard.rs \
    && ok "local data boundary check present" || bad "local data boundary check present"
grep -q 'overlaps' rust/witness-verify/src/zipguard.rs \
    && ok "overlapping range detection present" || bad "overlapping range detection present"
grep -q 'ARCHIVE_WINDOWS_NAME_UNSAFE' rust/witness-verify/src/zipguard.rs \
    && ok "windows reserved-name handling present" || bad "windows reserved-name handling present"
grep -q 'reserved_com1_fails' rust/witness-verify/src/main.rs \
    && ok "windows reserved-name test present" || bad "windows reserved-name test present"
grep -q 'ads_colon_fails' rust/witness-verify/src/main.rs \
    && ok "ADS test present" || bad "ADS test present"
# v5 repairs (third hostile-review round)
grep -q 'Flag policy ORDER matters' rust/witness-verify/src/zipguard.rs \
    && ok "flag-mask gate ordered after local-header check" || bad "flag-mask gate ordered after local-header check"
grep -q 'entry_data_into_central_directory_fails' rust/witness-verify/src/main.rs \
    && ok "data-into-CD test present" || bad "data-into-CD test present"
grep -q 'overlapping_entry_ranges_fail' rust/witness-verify/src/main.rs \
    && ok "overlapping-range test present" || bad "overlapping-range test present"
grep -q 'nonzero_disk_start_fails' rust/witness-verify/src/main.rs \
    && ok "disk-start test present" || bad "disk-start test present"
grep -q 'cd_not_ending_at_eocd_fails' rust/witness-verify/src/main.rs \
    && ok "CD-ends-at-EOCD test present" || bad "CD-ends-at-EOCD test present"
grep -q 'eocd_comment_length_mismatch_fails' rust/witness-verify/src/main.rs \
    && ok "EOCD comment-length test present" || bad "EOCD comment-length test present"
grep -q 'fn parse_extra_fields' rust/witness-verify/src/zipguard.rs \
    && ok "strict extra-field allowlist parser present" || bad "strict extra-field allowlist parser present"
grep -q 'ARCHIVE_UNREFERENCED_DATA' rust/witness-verify/src/zipguard.rs \
    && ok "unreferenced-data layout check present" || bad "unreferenced-data layout check present"
grep -q 'creator host system' rust/witness-verify/src/zipguard.rs \
    && ok "creator host parsed and enforced" || bad "creator host parsed and enforced"
grep -q 'real_extra_field_pattern_accepted' rust/witness-verify/src/main.rs \
    && ok "real-archive extra pattern test present" || bad "real-archive extra pattern test present"
grep -q 'orphan_local_header_fails' rust/witness-verify/src/main.rs \
    && ok "orphan local-header test present" || bad "orphan local-header test present"
grep -q 'non_unix_creator_rejected' rust/witness-verify/src/main.rs \
    && ok "creator-host test present" || bad "creator-host test present"
# v7: duplicate inherent methods are a compile error; prove uniqueness
dup_ele=$(grep -c 'fn entry_local_extra' rust/witness-verify/src/main.rs)
if [ "$dup_ele" -eq 1 ]; then
    ok "exactly one entry_local_extra method in Zw impl"
else
    bad "exactly one entry_local_extra method in Zw impl (found $dup_ele)"
fi
dups=$(grep -oE '^ +fn [a-z_]+\(' rust/witness-verify/src/main.rs | sed 's/.*fn //; s/(//' | sort | uniq -d | tr '\n' ' ')
if [ -z "$dups" ]; then
    ok "no duplicate method definitions in main.rs"
else
    bad "duplicate method definitions in main.rs: $dups"
fi
grep -q 'Extended Timestamp flags disagree' rust/witness-verify/src/zipguard.rs \
    && ok "central/local UT flags compared" || bad "central/local UT flags compared"
# v8: unqualified associated-fn calls inside impl Zw are a compile error
# (cargo test failed on exactly this in v7). Prove none remain.
if python3 - << 'SELFEOF'
def _read(p, mode="r"):
    with open(p, mode) as _h:
        return _h.read()


def _readjson(p):
    import json as _j
    with open(p) as _h:
        return _j.load(_h)


import re, sys
src = _read("rust/witness-verify/src/main.rs")
m = re.search(r"impl Zw \{(.*?)\n    \}\n", src, re.S)
if m is None:
    print("  detail: impl Zw block not found"); sys.exit(1)
block = m.group(1)
assoc = re.findall(r"fn ([a-z_0-9]+)\(\s*(?!&)", block)
bad = []
for name in assoc:
    for mm in re.finditer(r"(?<!fn )(?<!Self::)(?<!Zw::)\b%s\(" % name, block):
        if "fn " in block[max(0, mm.start()-8):mm.start()]:
            continue
        if name == "new":
            continue
        bad.append(name)
if bad:
    print("  detail: unqualified associated-fn calls in impl Zw: %s"
          % sorted(set(bad)))
    sys.exit(1)
sys.exit(0)
SELFEOF
then
    ok "no unqualified associated-fn calls in impl Zw"
else
    bad "no unqualified associated-fn calls in impl Zw"
fi
grep -q 'central_local_ut_flags_disagreement_fails' rust/witness-verify/src/main.rs \
    && ok "UT flags disagreement test present" || bad "UT flags disagreement test present"
# v9: reason-code precedence tests and documented taxonomy
grep -q "dot_component_is_traversal_not_windows" rust/witness-verify/src/main.rs \
    && ok "dot-vs-windows precedence test present" \
    || bad "dot-vs-windows precedence test present"
grep -q "unc_beats_generic_absolute" rust/witness-verify/src/main.rs \
    && ok "UNC-vs-absolute precedence test present" \
    || bad "UNC-vs-absolute precedence test present"
grep -q "REASON-CODE TAXONOMY" rust/witness-verify/src/zipguard.rs \
    && ok "reason-code taxonomy documented in code" \
    || bad "reason-code taxonomy documented in code"
grep -q "Reason-code taxonomy" rust/README.md \
    && ok "reason-code taxonomy documented in README" \
    || bad "reason-code taxonomy documented in README"
# v10: no-extraction tests must NEVER snapshot the shared global temp
# root - parallel tests create/delete fixtures there, which races (this
# failed the v9 parallel Cargo gate).
if python3 - << 'RDEOF'
def _read(p, mode="r"):
    with open(p, mode) as _h:
        return _h.read()


def _readjson(p):
    import json as _j
    with open(p) as _h:
        return _j.load(_h)


import re, sys
src = _read("rust/witness-verify/src/main.rs")
bad = []
for m in re.finditer(r"read_dir\(([^)]*)\)", src):
    arg = m.group(1)
    if "parent()" in arg or "temp_dir()" in arg:
        bad.append(arg.strip())
if re.search(r"let\s+parent\s*=\s*\w+\.parent\(\)", src):
    bad.append("p.parent() snapshot idiom")
if bad:
    print("  detail: test reads the shared temp root: %s" % bad)
    sys.exit(1)
sys.exit(0)
RDEOF
then
    ok "no test snapshots the shared global temp directory"
else
    bad "no test snapshots the shared global temp directory"
fi
grep -q "CONCURRENCY SAFETY" rust/witness-verify/src/main.rs \
    && ok "no-extraction test documents its concurrency-safety rule" \
    || bad "no-extraction test documents its concurrency-safety rule"
grep -q "inspection modified the archive bytes" rust/witness-verify/src/main.rs \
    && ok "no-extraction test proves the archive is unmodified" \
    || bad "no-extraction test proves the archive is unmodified"
if grep -qF 'ANY non-empty extra' rust/witness-verify/src/zipguard.rs; then
    bad "zipguard free of stale reject-all-extra-fields wording"
else
    ok "zipguard free of stale reject-all-extra-fields wording"
fi
# Forbid the ASSERTIVE false claim (the exact v5 sentences). Quoted
# disavowals in the correction text are fine and must not trip this.
if grep -rqF 'archives have zero extra fields, computed' rust/; then
    bad "rust/ free of the assertive zero-extra-fields claim"
else
    ok "rust/ free of the assertive zero-extra-fields claim"
fi
# the real archives DO have extra fields: require the corrected fact
grep -q 'they are NOT free of extra fields' rust/witness-verify/src/zipguard.rs \
    && ok "zipguard states the corrected extra-field grounding" \
    || bad "zipguard states the corrected extra-field grounding"
grep -q 'unknown_central_extra_field_fails' rust/witness-verify/src/main.rs \
    && ok "unknown-extra-field test present" || bad "unknown-extra-field test present"
grep -q 'ARCHIVE_SPECIAL_FILE_TYPE' rust/witness-verify/src/zipguard.rs \
    && ok "special-file-type handling present" || bad "special-file-type handling present"
grep -q 'fifo_entry_fails' rust/witness-verify/src/main.rs \
    && ok "FIFO test present" || bad "FIFO test present"
if grep -q 'the UTF-8 general-purpose-flag,' rust/witness-verify/src/zipguard.rs; then
    bad "zipguard free of stale UTF-8-flag-unsupported comment"
else
    ok "zipguard free of stale UTF-8-flag-unsupported comment"
fi
if grep -Fq 'central-directory inspection), not a full verifier' "CURRENT_RELEASE_STATE.md"; then
    bad "state doc free of central-directory-only wording"
else
    ok "state doc free of central-directory-only wording"
fi
# forbid stale truth text (external-review findings)
if grep -q 'Step 74: case manifest validator' rust/witness-verify/src/main.rs; then
    bad "main.rs free of stale Step 74 docstring"
else
    ok "main.rs free of stale Step 74 docstring"
fi
if grep -q 'receipt chains are not implemented' rust/README.md; then
    bad "README free of stale receipt-chains-not-implemented wording"
else
    ok "README free of stale receipt-chains-not-implemented wording"
fi
[ -f rust/witness-verify/src/receipts.rs ] \
    && ok "receipt chain module present" \
    || bad "receipt chain module present"
grep -q 'RECEIPT_LINKAGE_BROKEN' rust/witness-verify/src/receipts.rs \
    && ok "linkage break detection present" \
    || bad "linkage break detection present"
grep -q 'manifest_hash and\|seal_hash recomputation are deferred' rust/witness-verify/src/receipts.rs \
    && ok "remaining recomputation gaps stated in code" \
    || bad "remaining recomputation gaps stated in code"
[ -f rust/witness-verify/src/sha256.rs ] \
    && ok "stdlib SHA-256 module present" \
    || bad "stdlib SHA-256 module present"
grep -q 'fips_vector_two_block' rust/witness-verify/src/sha256.rs \
    && ok "FIPS test vectors present in sha256 tests" \
    || bad "FIPS test vectors present in sha256 tests"
grep -q 'cross_implementation_agreement_with_python_hashlib' rust/witness-verify/src/sha256.rs \
    && ok "Python hashlib cross-check vector present" \
    || bad "Python hashlib cross-check vector present"
grep -q 'FILE_HASH_MISMATCH' rust/witness-verify/src/hashes.rs \
    && ok "hash mismatch detection present" \
    || bad "hash mismatch detection present"
grep -q 'REQUIRED_PATH_UNDECLARED' rust/witness-verify/src/hashes.rs \
    && ok "undeclared critical file detection present" \
    || bad "undeclared critical file detection present"
[ -f rust/witness-verify/src/json.rs ] \
    && ok "zero-crate JSON parser module present" \
    || bad "zero-crate JSON parser module present"
[ -f rust/witness-verify/src/manifest.rs ] \
    && ok "manifest validator module present" \
    || bad "manifest validator module present"
grep -q 'CRITICAL_UNKNOWN_FIELD' rust/witness-verify/src/manifest.rs \
    && ok "critical unknown-field handling present" \
    || bad "critical unknown-field handling present"
grep -q 'SCHEMA_VERSION_UNSUPPORTED' rust/witness-verify/src/manifest.rs \
    && ok "schema version pinning present" \
    || bad "schema version pinning present"

# Reference-alignment guard (added after the v2 Termux build failure,
# where the REPORT_FIELDS array held 19 entries under a declared length
# of 17). The field COUNT was narrated wrongly three times across review
# rounds; it is never narrated again, only computed. Four sources must
# agree exactly: the frozen reference report's keys, the Rust array's
# entries, the Rust array's declared length, and the unit-test fixture's
# keys. Any disagreement fails structurally, before any toolchain gate.
if python3 - << 'ALIGNEOF'
def _read(p, mode="r"):
    with open(p, mode) as _h:
        return _h.read()


def _readjson(p):
    import json as _j
    with open(p) as _h:
        return _j.load(_h)


import json, re, sys
ref = _readjson(
    "freeze_record/python_behaviour_freeze_v01/reference_bundle/"
    "companion_report.json")
ref_keys = sorted(ref.keys())
src = _read("rust/witness-verify/src/manifest.rs")
m = re.search(r'const REPORT_FIELDS: \[&str; (\d+)\] = \[(.*?)\];', src, re.S)
if m is None:
    print("  detail: REPORT_FIELDS not found"); sys.exit(1)
declared = int(m.group(1))
entries = sorted(re.findall(r'"([a-z_]+)"', m.group(2)))
fx = re.search(r'const VALID_REPORT: &str = "(.*?)";',
               _read("rust/witness-verify/src/main.rs"), re.S)
if fx is None:
    print("  detail: VALID_REPORT fixture not found"); sys.exit(1)
fixture = sorted(set(re.findall(r'\\"([a-z_]+)\\":', fx.group(1))))
problems = []
if entries != ref_keys:
    problems.append("array entries != reference keys: %s"
                    % sorted(set(entries) ^ set(ref_keys)))
if declared != len(entries):
    problems.append("declared length %d != actual entries %d"
                    % (declared, len(entries)))
if fixture != ref_keys:
    problems.append("fixture keys != reference keys: %s"
                    % sorted(set(fixture) ^ set(ref_keys)))
hp = re.search(r'const REQUIRED_HASH_PATHS: \[&str; (\d+)\] = \[(.*?)\];',
               _read("rust/witness-verify/src/hashes.rs"), re.S)
if hp is None:
    print("  detail: REQUIRED_HASH_PATHS not found"); sys.exit(1)
hp_declared = int(hp.group(1))
hp_entries = sorted(re.findall(r'"([a-z_./0-9]+)"', hp.group(2)))
py = re.search(r'REQUIRED_PATHS = \((.*?)\)',
               _read("src/12_companion_cli_v031/companion_lib/"
                     "checksums.py"), re.S)
py_paths = sorted(re.findall(r'"([a-z_./0-9]+)"', py.group(1)))
ref_paths = sorted(
    l.split("  ")[1]
    for l in _read("freeze_record/python_behaviour_freeze_v01/"
                   "reference_bundle/companion_checksums.txt").splitlines()
    if l.strip())
if hp_entries != py_paths:
    problems.append("Rust REQUIRED_HASH_PATHS != Python REQUIRED_PATHS: %s"
                    % sorted(set(hp_entries) ^ set(py_paths)))
if hp_declared != len(hp_entries):
    problems.append("REQUIRED_HASH_PATHS declared length %d != entries %d"
                    % (hp_declared, len(hp_entries)))
if hp_entries != ref_paths:
    problems.append("Rust REQUIRED_HASH_PATHS != reference declared paths: %s"
                    % sorted(set(hp_entries) ^ set(ref_paths)))
mv = re.search(r'const VERSION: &str = "([^"]+)"',
               _read("rust/witness-verify/src/main.rs"))
if mv is None:
    print("  detail: VERSION const not found"); sys.exit(1)
version = mv.group(1)
step = re.search(r'step(\d+)', version)
if step is None:
    print("  detail: VERSION carries no step marker: %s" % version)
    sys.exit(1)
step_num = step.group(1)
main_src = _read("rust/witness-verify/src/main.rs")
vt = re.search(r'fn version_marks_step(\d+)\(\) \{\s*'
               r'assert!\(VERSION\.contains\("([^"]+)"\)\);', main_src)
if vt is None:
    problems.append("version-marker test not found")
else:
    if vt.group(1) != step_num:
        problems.append("version test marks step%s but VERSION is step%s"
                        % (vt.group(1), step_num))
    if vt.group(2) not in version:
        problems.append("version test asserts %r, not a substring of "
                        "VERSION %r" % (vt.group(2), version))
rk = re.search(r'const RECEIPT_KEYS: \[&str; (\d+)\] = \[(.*?)\];',
               _read("rust/witness-verify/src/receipts.rs"), re.S)
if rk is None:
    print("  detail: RECEIPT_KEYS not found"); sys.exit(1)
rk_declared = int(rk.group(1))
rk_entries = sorted(re.findall(r'"([a-z_]+)"', rk.group(2)))
run_doc = _readjson("freeze_record/python_behaviour_freeze_v01/reference_bundle/coordinator_output/sentinel_run/sentinel_run.json")
ref_receipt_keysets = [sorted(r.keys()) for r in run_doc["receipts"]]
if any(k != ref_receipt_keysets[0] for k in ref_receipt_keysets):
    problems.append("reference receipts disagree on their own key set")
elif rk_entries != ref_receipt_keysets[0]:
    problems.append("Rust RECEIPT_KEYS != reference receipt keys: %s"
                    % sorted(set(rk_entries) ^ set(ref_receipt_keysets[0])))
if rk_declared != len(rk_entries):
    problems.append("RECEIPT_KEYS declared length %d != entries %d"
                    % (rk_declared, len(rk_entries)))
# Move 77: the canonical recipe the Rust encodes must reproduce the
# frozen reference receipts' stored canonical_hash values. We validate
# the recipe in Python (Rust runs on the Termux gate); the Rust unit
# tests carry the same vectors as CPython-precomputed constants.
import hashlib as _hl
run_doc = _readjson("freeze_record/python_behaviour_freeze_v01/reference_bundle/coordinator_output/sentinel_run/sentinel_run.json")
recipe_ok = True
for _r in run_doc["receipts"]:
    _payload = {k: v for k, v in _r.items() if k != "canonical_hash"}
    _canon = json.dumps(_payload, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=False, allow_nan=False)
    _digest = _hl.sha256(_canon.encode("utf-8")).hexdigest()
    if _digest != _r["canonical_hash"]:
        recipe_ok = False
if not recipe_ok:
    problems.append("canonical recipe does not reproduce reference "
                    "receipt hashes")
# guard: the four cross-impl vectors in canonical.rs must be present
_canon_src = _read("rust/witness-verify/src/canonical.rs")
for _needed in ["vector_sorting_and_literals", "floats_fail_closed",
                "vector_raw_utf8_not_escaped"]:
    if _needed not in _canon_src:
        problems.append("canonical.rs missing test %s" % _needed)
# Move 77 v3: Rust test count must be computed, not narrated. Count
# #[test] attributes in source and require CHANGELOG_MOVE_77.md to state
# that exact number in a machine-checkable marker line.
import glob as _glob
_test_count = 0
for _f in sorted(_glob.glob("rust/witness-verify/src/*.rs")):
    _test_count += _read(_f).count("#[test]")
_arch_codes = sorted(set(re.findall(r"ARCHIVE_[A-Z_]+",
    _read("rust/witness-verify/src/zipguard.rs"))))
_arch_count = len(_arch_codes)
_cl = _read("CHANGELOG_MOVE_79.md")  # CURRENT counts live here;
# CHANGELOG_MOVE_78.md is an ADOPTED historical record (123 tests) and
# must never be edited to satisfy a current check.
_marker = "<!-- RUST_TEST_COUNT: %d -->" % _test_count
if _marker not in _cl:
    problems.append("CHANGELOG_MOVE_79.md test-count marker missing or "
                    "wrong; computed %d" % _test_count)
_amarker = "<!-- ARCHIVE_REASON_CODE_COUNT: %d -->" % _arch_count
if _amarker not in _cl:
    problems.append("CHANGELOG_MOVE_79.md archive-code marker missing or "
                    "wrong; computed %d" % _arch_count)
# v6: prove the Rust allowlist covers the tags the REAL archives use.
import struct as _st, zipfile as _zf
_zg = _read("rust/witness-verify/src/zipguard.rs")
_allow = set(re.findall(r"const TAG_(?:UT|UX): u16 = (0x[0-9a-fA-F]+);", _zg))
_allow = {int(x, 16) for x in _allow}
_real_zip = ("releases/roadmap_one_complete/move_70_final/"
             "Project_Witness_WORKING_STACK_v20_MOVE_70.zip")
_seen = set()
try:
    with _zf.ZipFile(_real_zip) as _z:
        for _i in _z.infolist():
            _b, _p = _i.extra, 0
            while _p + 4 <= len(_b):
                _t, _s = _st.unpack("<HH", _b[_p:_p+4])
                _seen.add(_t); _p += 4 + _s
except Exception as _e:
    problems.append("could not read real archive for extra-tag guard: %s" % _e)
if _seen and not _seen <= _allow:
    problems.append("real archive uses extra tags %s not in Rust allowlist %s"
                    % (sorted(hex(t) for t in _seen - _allow),
                       sorted(hex(t) for t in _allow)))
readme = _read("rust/README.md")
if ("Step %s status:" % step_num) not in readme:
    problems.append("rust/README.md status section does not say "
                    "'Step %s status:' (stale README)" % step_num)
if problems:
    for p in problems:
        print("  detail:", p)
    sys.exit(1)
print("  detail: %d fields, %d hash paths, %d receipt keys, %d rust "
      "tests, %d archive codes, step%s markers; all computed values "
      "agree" % (len(ref_keys), len(hp_entries), len(rk_entries),
                 _test_count, _arch_count, step_num))
sys.exit(0)
ALIGNEOF
then
    ok "REPORT_FIELDS aligned with frozen reference (computed)"
else
    bad "REPORT_FIELDS aligned with frozen reference (computed)"
fi
grep -q 'no_reachable_path_emits_pass' rust/witness-verify/src/main.rs \
    && ok "PASS-unreachable property is tested" \
    || bad "PASS-unreachable property is tested"

grep -q 'freeze_record/python_behaviour_freeze_v01' rust/README.md \
    && ok "README names the Move 71 freeze as the behavioural reference" \
    || bad "README names the Move 71 freeze as the behavioural reference"

if [ "$fail" -ne 0 ]; then
    echo "RUST_WORKSPACE_CHECK: FAIL"
    exit 1
fi

echo "Toolchain checks:"
if command -v cargo >/dev/null 2>&1; then
    ok "cargo present: $(cargo --version 2>&1)"
    ( cd rust && cargo build -q ) \
        && ok "cargo build" || { bad "cargo build"; }
    cargo_out=$( cd rust && cargo test 2>&1 )
    cargo_rc=$?
    if printf "%s" "$cargo_out" | grep -q "test result: ok"; then
        expected=$(python3 -B -c "
import glob
n = 0
for f in glob.glob('rust/witness-verify/src/*.rs'):
    with open(f) as h:
        n += h.read().count(chr(35) + '[test]')
print(n)")
        if printf "%s" "$cargo_out" | grep -Eq "$expected (passed|tests)"; then
            ok "cargo test ($expected tests, count matches source)"
        else
            bad "cargo test count does not match source ($expected)"
            printf "%s\n" "$cargo_out" | tail -30
        fi
    else
        bad "cargo test (exit $cargo_rc) - compiler output follows"
        echo "---------------- cargo test output ----------------"
        printf "%s\n" "$cargo_out" | grep -E "^error|^warning|^ *-->|^thread|panicked|test result" | head -40
        echo "--------------------------------------------------"
        echo "(full output: cd rust && cargo test)"
    fi
    if [ "$fail" -ne 0 ]; then
        echo "RUST_WORKSPACE_CHECK: FAIL"
        exit 1
    fi
    echo "RUST_WORKSPACE_CHECK: PASS"
    exit 0
fi

echo "  NOTE  no Rust toolchain on this machine; build/test not executed"
echo "RUST_WORKSPACE_CHECK: INCONCLUSIVE_TOOLCHAIN_UNAVAILABLE"
exit 3
