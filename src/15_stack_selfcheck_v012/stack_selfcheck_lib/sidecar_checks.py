"""Verify zip external sidecars where provided (read-only)."""

import hashlib
import os
import re

from .errors import CheckError, FAILED_ZIP_SIDECAR_INVALID

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_sidecar(comp):
    """Return True if the sidecar is valid (or legitimately absent for an
    optional sidecar). Raise CheckError otherwise."""
    zip_path = comp.get("zip_path")
    sha_path = comp.get("sha256_path")
    optional = bool(comp.get("sidecar_optional", False))
    if not zip_path and not sha_path:
        if optional:
            return True
        raise CheckError(FAILED_ZIP_SIDECAR_INVALID,
                         "%s missing required zip sidecar" % comp["component_id"])
    if not (zip_path and sha_path):
        raise CheckError(FAILED_ZIP_SIDECAR_INVALID,
                         "%s has incomplete sidecar config" % comp["component_id"])
    if not os.path.isfile(zip_path) or not os.path.isfile(sha_path):
        if optional:
            return True
        raise CheckError(FAILED_ZIP_SIDECAR_INVALID,
                         "%s zip or sidecar file missing" % comp["component_id"])
    with open(sha_path, "r", encoding="utf-8") as handle:
        line = handle.read().strip()
    parts = line.split("  ")
    if len(parts) != 2:
        raise CheckError(FAILED_ZIP_SIDECAR_INVALID,
                         "%s sidecar malformed" % comp["component_id"])
    digest = parts[0]
    if digest != digest.lower() or not _HEX64.match(digest):
        raise CheckError(FAILED_ZIP_SIDECAR_INVALID,
                         "%s sidecar digest invalid" % comp["component_id"])
    if _sha256_file(zip_path) != digest:
        raise CheckError(FAILED_ZIP_SIDECAR_INVALID,
                         "%s zip checksum mismatch" % comp["component_id"])
    return True
