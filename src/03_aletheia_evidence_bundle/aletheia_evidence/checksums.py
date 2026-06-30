# aletheia_evidence/checksums.py
# The evidence_checksums.txt format: exactly two required lines, each
#     <sha256>  <relative-path>
# (two spaces, matching `sha256sum` style). Strict: required keys exactly once,
# no duplicates, no unknowns, well-formed digests only.

from aletheia_evidence.errors import require, VerifyError
from aletheia_evidence.hashing import is_valid_sha256
from aletheia_evidence import versions

MANIFEST_KEY = versions.MANIFEST_NAME  # "evidence_manifest.json"
BUNDLED_KEY = f"{versions.EVIDENCE_DIRNAME}/{versions.BUNDLED_FILE_NAME}"
REQUIRED_KEYS = (MANIFEST_KEY, BUNDLED_KEY)


def format_checksums(*, manifest_sha256, bundled_sha256) -> bytes:
    """Serialise the two required lines deterministically (manifest first)."""
    lines = [
        f"{manifest_sha256}  {MANIFEST_KEY}",
        f"{bundled_sha256}  {BUNDLED_KEY}",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_checksums(text) -> dict:
    """Parse evidence_checksums.txt into {path: sha256}. Strict.

    Raises VerifyError(FAILED_CHECKSUMS_INVALID) on duplicate keys, missing
    required keys, unknown keys, or malformed digests/lines.
    """
    bad = versions.EVIDENCE_FAILED_CHECKSUMS_INVALID
    mapping = {}
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.strip() == "":
            continue  # tolerate blank lines only
        # Exactly "<digest>  <path>" — split on the first double space.
        parts = line.split("  ", 1)
        require(len(parts) == 2,
                f"malformed checksum line: {line!r}", VerifyError, status=bad)
        digest, path = parts[0].strip(), parts[1].strip()
        require(is_valid_sha256(digest),
                f"malformed sha256 digest: {digest!r}", VerifyError, status=bad)
        require(path in REQUIRED_KEYS,
                f"unknown checksum key: {path!r}", VerifyError, status=bad)
        require(path not in mapping,
                f"duplicate checksum key: {path!r}", VerifyError, status=bad)
        mapping[path] = digest

    missing = [k for k in REQUIRED_KEYS if k not in mapping]
    require(not missing,
            f"missing checksum keys: {missing}", VerifyError, status=bad)
    return mapping
