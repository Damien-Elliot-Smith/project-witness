# aletheia_evidence/hashing.py
# SHA-256 helpers. Unkeyed hashes give tamper-EVIDENCE within a file, not
# tamper-proofness and not authentication of origin (see KNOWN_LIMITATIONS).

import hashlib
import re

_CHUNK = 1024 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_valid_sha256(value) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))
