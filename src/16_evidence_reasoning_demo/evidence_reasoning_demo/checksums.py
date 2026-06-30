# evidence_reasoning_demo/checksums.py
# The demo_checksums.txt format: exactly five required lines, each
#     <sha256>  <relative-path>
# Strict: required keys exactly once, no duplicates/unknowns, valid lowercase
# digests only.

from evidence_reasoning_demo.errors import require, VerifyError
from evidence_reasoning_demo.validation import is_valid_sha256
from evidence_reasoning_demo import versions

REPORT_KEY = versions.DEMO_REPORT_NAME
STEPS_KEY = versions.DEMO_STEPS_NAME
ALETHEIA_MANIFEST_KEY = versions.ALETHEIA_MANIFEST_REL
BRIDGE_REPORT_KEY = versions.BRIDGE_REPORT_REL
ODIN_REPORT_KEY = versions.ODIN_REASONING_REPORT_REL
REQUIRED_KEYS = (REPORT_KEY, STEPS_KEY, ALETHEIA_MANIFEST_KEY, BRIDGE_REPORT_KEY,
                 ODIN_REPORT_KEY)

_BAD = versions.FAILED_CHECKSUMS_INVALID


def format_checksums(*, demo_report_sha256, demo_steps_sha256,
                     aletheia_manifest_sha256, bridge_report_sha256,
                     odin_reasoning_report_sha256) -> bytes:
    lines = [
        f"{demo_report_sha256}  {REPORT_KEY}",
        f"{demo_steps_sha256}  {STEPS_KEY}",
        f"{aletheia_manifest_sha256}  {ALETHEIA_MANIFEST_KEY}",
        f"{bridge_report_sha256}  {BRIDGE_REPORT_KEY}",
        f"{odin_reasoning_report_sha256}  {ODIN_REPORT_KEY}",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_checksums(text) -> dict:
    """Parse demo_checksums.txt into {path: sha256}. Strict."""
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
