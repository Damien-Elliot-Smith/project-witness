# atlas_registry_lib/checksums.py
# atlas_checksums.txt: exactly 2 required lines, each <sha256>  <relative-path>.
# Strict: required keys exactly once, no duplicates/unknowns, lowercase digests.

from atlas_registry_lib.errors import require, ExportError
from atlas_registry_lib.validation import is_valid_sha256
from atlas_registry_lib import versions

REQUIRED_KEYS = versions.EXPORT_CHECKSUM_KEYS  # (registry_copy, summary)
_BAD = versions.FAILED_CHECKSUMS_INVALID


def format_checksums(digests: dict) -> bytes:
    lines = [f"{digests[key]}  {key}" for key in REQUIRED_KEYS]
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_checksums(text) -> dict:
    mapping = {}
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.strip() == "":
            continue
        parts = line.split("  ", 1)
        require(len(parts) == 2, f"malformed checksum line: {line!r}", ExportError,
                reason=_BAD)
        digest, path = parts[0].strip(), parts[1].strip()
        require(is_valid_sha256(digest),
                f"malformed/uppercase sha256 digest: {digest!r}", ExportError,
                reason=_BAD)
        require(path in REQUIRED_KEYS, f"unknown checksum key: {path!r}",
                ExportError, reason=_BAD)
        require(path not in mapping, f"duplicate checksum key: {path!r}",
                ExportError, reason=_BAD)
        mapping[path] = digest
    missing = [k for k in REQUIRED_KEYS if k not in mapping]
    require(not missing, f"missing checksum keys: {missing}", ExportError,
            reason=_BAD)
    return mapping
