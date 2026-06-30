# aletheia_odin_bridge/checksums.py
# The bridge_checksums.txt format: exactly three required lines, each
#     <sha256>  <relative-path>
# Strict: required keys exactly once, no duplicates/unknowns, valid lowercase
# digests only.

from aletheia_odin_bridge.errors import require, VerifyError
from aletheia_odin_bridge.validation import is_valid_sha256
from aletheia_odin_bridge import versions

CLAIMS_KEY = versions.ODIN_CLAIMS_NAME
REPORT_KEY = versions.BRIDGE_REPORT_NAME
MANIFEST_COPY_KEY = versions.MANIFEST_COPY_NAME
REQUIRED_KEYS = (CLAIMS_KEY, REPORT_KEY, MANIFEST_COPY_KEY)

_BAD = versions.BRIDGE_FAILED_CHECKSUMS_INVALID


def format_checksums(*, claims_sha256, report_sha256, manifest_copy_sha256) -> bytes:
    lines = [
        f"{claims_sha256}  {CLAIMS_KEY}",
        f"{report_sha256}  {REPORT_KEY}",
        f"{manifest_copy_sha256}  {MANIFEST_COPY_KEY}",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_checksums(text) -> dict:
    """Parse bridge_checksums.txt into {path: sha256}. Strict."""
    mapping = {}
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.strip() == "":
            continue
        parts = line.split("  ", 1)
        require(len(parts) == 2, f"malformed checksum line: {line!r}",
                VerifyError, reason=_BAD)
        digest, path = parts[0].strip(), parts[1].strip()
        require(is_valid_sha256(digest), f"malformed sha256 digest: {digest!r}",
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
