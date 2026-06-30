# histor_odin_importer/checksums.py
# The odin_case_checksums.txt format: exactly five required lines, each
#     <sha256>  <relative-path>
# Strict: required keys exactly once, no duplicates/unknowns, valid lowercase
# digests only (uppercase rejected).

from histor_odin_importer.errors import require, VerifyError
from histor_odin_importer.validation import is_valid_sha256
from histor_odin_importer import versions

SUMMARY_KEY = versions.SUMMARY_NAME
REPORT_COPY_KEY = versions.REPORT_COPY_NAME
TRACE_COPY_KEY = versions.TRACE_COPY_NAME
CLAIMS_COPY_KEY = versions.CLAIMS_COPY_NAME
REPLAY_REPORT_KEY = versions.REPLAY_REPORT_NAME
REQUIRED_KEYS = (SUMMARY_KEY, REPORT_COPY_KEY, TRACE_COPY_KEY, CLAIMS_COPY_KEY,
                 REPLAY_REPORT_KEY)

_BAD = versions.FAILED_CHECKSUMS_INVALID


def format_checksums(*, summary_sha256, report_copy_sha256, trace_copy_sha256,
                     claims_copy_sha256, replay_report_sha256) -> bytes:
    lines = [
        f"{summary_sha256}  {SUMMARY_KEY}",
        f"{report_copy_sha256}  {REPORT_COPY_KEY}",
        f"{trace_copy_sha256}  {TRACE_COPY_KEY}",
        f"{claims_copy_sha256}  {CLAIMS_COPY_KEY}",
        f"{replay_report_sha256}  {REPLAY_REPORT_KEY}",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_checksums(text) -> dict:
    """Parse odin_case_checksums.txt into {path: sha256}. Strict."""
    mapping = {}
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.strip() == "":
            continue
        parts = line.split("  ", 1)
        require(len(parts) == 2, f"malformed checksum line: {line!r}",
                VerifyError, reason=_BAD)
        digest, path = parts[0].strip(), parts[1].strip()
        require(is_valid_sha256(digest),
                f"malformed/uppercase sha256 digest: {digest!r}",
                VerifyError, reason=_BAD)
        require(path in REQUIRED_KEYS, f"unknown checksum key: {path!r}",
                VerifyError, reason=_BAD)
        require(path not in mapping, f"duplicate checksum key: {path!r}",
                VerifyError, reason=_BAD)
        mapping[path] = digest
    missing = [k for k in REQUIRED_KEYS if k not in mapping]
    require(not missing, f"missing checksum keys: {missing}",
            VerifyError, reason=_BAD)
    return mapping
