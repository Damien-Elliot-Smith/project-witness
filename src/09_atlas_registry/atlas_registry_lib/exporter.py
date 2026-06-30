# atlas_registry_lib/exporter.py
# Export a verified registry to a portable folder (registry copy + summary +
# checksums) and verify such an export. Atlas records vocabulary only.

import json
import os

from atlas_registry_lib.canonical import canonical_bytes
from atlas_registry_lib.checksums import (
    format_checksums, parse_checksums, REQUIRED_KEYS)
from atlas_registry_lib.errors import require, ExportError, BuildPathError
from atlas_registry_lib.validation import sha256_bytes, sha256_file
from atlas_registry_lib.verifier import verify_registry, verify_registry_obj
from atlas_registry_lib import versions


class ExportResult:
    __slots__ = ("out_dir", "summary")

    def __init__(self, out_dir, summary):
        self.out_dir = out_dir
        self.summary = summary


def _write_bytes(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def build_summary(reg, counts):
    return {
        "atlas_registry_version": reg["atlas_registry_version"],
        "registry_id": reg["registry_id"],
        "component_count": counts["component_count"],
        "workflow_type_count": counts["workflow_type_count"],
        "action_type_count": counts["action_type_count"],
        "status_count": counts["status_count"],
        "claim_predicate_count": counts["claim_predicate_count"],
        "registry_status": versions.REGISTRY_VERIFIED,
        "known_limitations": list(reg.get("known_limitations", [])),
    }


def export_registry(registry_path, out_dir):
    """Verify the registry, then write a portable export folder. Raises on failure."""
    result = verify_registry(registry_path)  # rules 1-23; raises if invalid

    if os.path.isdir(out_dir) and os.listdir(out_dir):
        raise BuildPathError("OUTPUT_DIR_NOT_EMPTY",
                             f"output directory is not empty: {out_dir!r}")
    os.makedirs(out_dir, exist_ok=True)

    # Registry copy is the canonical registry bytes (byte-identical to source).
    registry_bytes = canonical_bytes(result.registry)
    summary = build_summary(result.registry, result.counts)
    summary_bytes = canonical_bytes(summary)

    _write_bytes(os.path.join(out_dir, versions.EXPORT_REGISTRY_COPY),
                 registry_bytes)
    _write_bytes(os.path.join(out_dir, versions.EXPORT_SUMMARY), summary_bytes)

    digests = {
        versions.EXPORT_REGISTRY_COPY: sha256_bytes(registry_bytes),
        versions.EXPORT_SUMMARY: sha256_bytes(summary_bytes),
    }
    _write_bytes(os.path.join(out_dir, versions.EXPORT_CHECKSUMS),
                 format_checksums(digests))

    # Self-verify the export before returning.
    verify_export(out_dir)
    return ExportResult(out_dir, summary)


def _load_canonical(path, reason):
    require(os.path.isfile(path), f"missing {os.path.basename(path)}", ExportError,
            reason=reason)
    with open(path, "rb") as f:
        raw = f.read()
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise ExportError(reason, f"{os.path.basename(path)} not valid JSON: {e}")
    require(canonical_bytes(obj) == raw,
            f"{os.path.basename(path)} is not canonical (possible tamper)",
            ExportError, reason=reason)
    return obj, raw


def verify_export(out_dir):
    """Verify an Atlas export folder (rules 1-8). Raises ExportError on failure."""
    require(os.path.isdir(out_dir), f"export dir not found: {out_dir!r}",
            ExportError, reason="EXPORT_MISSING")

    # 1. Required files exist.
    for name in versions.EXPORT_FILES:
        require(os.path.isfile(os.path.join(out_dir, name)),
                f"missing export file {name}", ExportError, reason="FILE_MISSING")

    # 2. Refuse unknown extra files.
    present = {n for n in os.listdir(out_dir) if not n.endswith(".tmp")}
    extra = present - set(versions.EXPORT_FILES)
    require(not extra, f"unknown extra export files: {sorted(extra)}", ExportError,
            reason="UNKNOWN_FILE")

    # 3. Canonical JSON for registry copy + summary.
    registry, registry_raw = _load_canonical(
        os.path.join(out_dir, versions.EXPORT_REGISTRY_COPY), "REGISTRY_NON_CANONICAL")
    summary, _ = _load_canonical(
        os.path.join(out_dir, versions.EXPORT_SUMMARY), "SUMMARY_NON_CANONICAL")

    # 4-5. Checksums parse + recompute.
    with open(os.path.join(out_dir, versions.EXPORT_CHECKSUMS),
              encoding="utf-8") as f:
        checksums = parse_checksums(f.read())
    for key in REQUIRED_KEYS:
        target = os.path.join(out_dir, key)
        require(checksums[key] == sha256_file(target),
                f"export hash mismatch for {key}", ExportError, reason="HASH_MISMATCH")

    # The registry copy must itself be a valid registry (re-verify content), and
    # this also enforces the truth refusals (rule 7).
    vres = verify_registry_obj(registry)

    # 6. Summary counts match the registry copy.
    require(summary.get("component_count") == vres.counts["component_count"],
            "summary component_count mismatch", ExportError, reason="COUNT_MISMATCH")
    require(summary.get("workflow_type_count") == vres.counts["workflow_type_count"],
            "summary workflow_type_count mismatch", ExportError,
            reason="COUNT_MISMATCH")
    require(summary.get("action_type_count") == vres.counts["action_type_count"],
            "summary action_type_count mismatch", ExportError,
            reason="COUNT_MISMATCH")
    require(summary.get("status_count") == vres.counts["status_count"],
            "summary status_count mismatch", ExportError, reason="COUNT_MISMATCH")
    require(summary.get("claim_predicate_count")
            == vres.counts["claim_predicate_count"],
            "summary claim_predicate_count mismatch", ExportError,
            reason="COUNT_MISMATCH")
    require(summary.get("registry_status") == versions.REGISTRY_VERIFIED,
            "summary registry_status != REGISTRY_VERIFIED", ExportError,
            reason="SUMMARY_STATUS_INVALID")

    # 8. Success.
    return summary
