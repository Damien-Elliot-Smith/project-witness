# case_bundle_v02_lib/checksums.py
# The bundle_checksums.txt format: exactly 14 required lines, each
#     <sha256>  <relative-path>
# Covering the manifest plus every packaged subcase file (including each subcase's
# own checksums file). Strict: required keys exactly once, no duplicates/unknowns,
# valid lowercase digests only (uppercase rejected).

from case_bundle_v02_lib.errors import require, VerifyError
from case_bundle_v02_lib.validation import is_valid_sha256
from case_bundle_v02_lib import versions

# The exact relative paths the bundle checksums must cover, in canonical order.
MANIFEST_KEY = versions.MANIFEST_NAME

SENTINEL_SUMMARY_KEY = f"{versions.SENTINEL_DIR}/{versions.SENTINEL_SUMMARY}"
SENTINEL_REPLAY_KEY = f"{versions.SENTINEL_DIR}/{versions.SENTINEL_REPLAY}"
SENTINEL_CHECKSUMS_KEY = f"{versions.SENTINEL_DIR}/{versions.SENTINEL_CHECKSUMS}"

ALETHEIA_SUMMARY_KEY = f"{versions.ALETHEIA_DIR}/{versions.ALETHEIA_SUMMARY}"
ALETHEIA_MANIFEST_COPY_KEY = (
    f"{versions.ALETHEIA_DIR}/{versions.ALETHEIA_MANIFEST_COPY}")
ALETHEIA_REPLAY_KEY = f"{versions.ALETHEIA_DIR}/{versions.ALETHEIA_REPLAY}"
ALETHEIA_CHECKSUMS_KEY = f"{versions.ALETHEIA_DIR}/{versions.ALETHEIA_CHECKSUMS}"

ODIN_SUMMARY_KEY = f"{versions.ODIN_DIR}/{versions.ODIN_SUMMARY}"
ODIN_REPORT_COPY_KEY = f"{versions.ODIN_DIR}/{versions.ODIN_REPORT_COPY}"
ODIN_TRACE_COPY_KEY = f"{versions.ODIN_DIR}/{versions.ODIN_TRACE_COPY}"
ODIN_CLAIMS_COPY_KEY = f"{versions.ODIN_DIR}/{versions.ODIN_CLAIMS_COPY}"
ODIN_REPLAY_KEY = f"{versions.ODIN_DIR}/{versions.ODIN_REPLAY}"
ODIN_CHECKSUMS_KEY = f"{versions.ODIN_DIR}/{versions.ODIN_CHECKSUMS}"

# Canonical ordered list of all required keys.
REQUIRED_KEYS = (
    MANIFEST_KEY,
    SENTINEL_SUMMARY_KEY, SENTINEL_REPLAY_KEY, SENTINEL_CHECKSUMS_KEY,
    ALETHEIA_SUMMARY_KEY, ALETHEIA_MANIFEST_COPY_KEY, ALETHEIA_REPLAY_KEY,
    ALETHEIA_CHECKSUMS_KEY,
    ODIN_SUMMARY_KEY, ODIN_REPORT_COPY_KEY, ODIN_TRACE_COPY_KEY,
    ODIN_CLAIMS_COPY_KEY, ODIN_REPLAY_KEY, ODIN_CHECKSUMS_KEY,
)

_BAD = versions.FAILED_CHECKSUMS_INVALID


def format_checksums(digests: dict) -> bytes:
    """digests maps each REQUIRED_KEYS entry -> sha256. Emit in canonical order."""
    lines = [f"{digests[key]}  {key}" for key in REQUIRED_KEYS]
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_checksums(text) -> dict:
    """Parse bundle_checksums.txt into {path: sha256}. Strict."""
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
    require(not missing, f"missing checksum keys: {missing}", VerifyError,
            reason=_BAD)
    return mapping
