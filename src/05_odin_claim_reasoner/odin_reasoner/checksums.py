# odin_reasoner/checksums.py
# The odin_checksums.txt format: exactly three required lines, each
#     <sha256>  <relative-path>
# Strict: required keys exactly once, no duplicates, no unknowns, valid digests.

from odin_reasoner.errors import require, VerifyError
from odin_reasoner.validation import is_valid_sha256
from odin_reasoner import versions

CLAIMS_KEY = versions.CLAIMS_CANONICAL_NAME
REPORT_KEY = versions.REASONING_REPORT_NAME
TRACE_KEY = versions.PROOF_TRACE_NAME
REQUIRED_KEYS = (CLAIMS_KEY, REPORT_KEY, TRACE_KEY)


def format_checksums(*, claims_sha256, report_sha256, trace_sha256) -> bytes:
    lines = [
        f"{claims_sha256}  {CLAIMS_KEY}",
        f"{report_sha256}  {REPORT_KEY}",
        f"{trace_sha256}  {TRACE_KEY}",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_checksums(text) -> dict:
    """Parse odin_checksums.txt into {path: sha256}. Strict; raises
    VerifyError(CHECKSUMS_INVALID) on any problem."""
    bad = "CHECKSUMS_INVALID"
    mapping = {}
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.strip() == "":
            continue
        parts = line.split("  ", 1)
        require(len(parts) == 2, f"malformed checksum line: {line!r}",
                VerifyError, reason=bad)
        digest, path = parts[0].strip(), parts[1].strip()
        require(is_valid_sha256(digest), f"malformed sha256 digest: {digest!r}",
                VerifyError, reason=bad)
        require(path in REQUIRED_KEYS, f"unknown checksum key: {path!r}",
                VerifyError, reason=bad)
        require(path not in mapping, f"duplicate checksum key: {path!r}",
                VerifyError, reason=bad)
        mapping[path] = digest
    missing = [k for k in REQUIRED_KEYS if k not in mapping]
    require(not missing, f"missing checksum keys: {missing}",
            VerifyError, reason=bad)
    return mapping
