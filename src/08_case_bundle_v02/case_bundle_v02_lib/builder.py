# case_bundle_v02_lib/builder.py
# Orchestrate: verify each input case -> confirm shared case_id -> copy each case
# record verbatim into the bundle -> write canonical manifest + strict bundle
# checksums -> self-verify. Deterministic. The input records are preserved exactly.

import os
import shutil

from case_bundle_v02_lib.canonical import canonical_bytes
from case_bundle_v02_lib.checksums import (
    format_checksums, REQUIRED_KEYS, MANIFEST_KEY)
from case_bundle_v02_lib.errors import require, BuildPathError, CaseIdMismatchError
from case_bundle_v02_lib.input_verifiers import InProcessInputVerifier
from case_bundle_v02_lib.manifest import build_manifest
from case_bundle_v02_lib.validation import sha256_bytes, sha256_file
from case_bundle_v02_lib import versions


class BuildResult:
    __slots__ = ("out_dir", "manifest")

    def __init__(self, out_dir, manifest):
        self.out_dir = out_dir
        self.manifest = manifest


def _write_bytes(path, data: bytes):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _copy_case(src_dir, dst_dir, names):
    """Copy exactly the named files from src_dir to dst_dir, byte-for-byte."""
    os.makedirs(dst_dir, exist_ok=True)
    for name in names:
        shutil.copyfile(os.path.join(src_dir, name), os.path.join(dst_dir, name))


def build_bundle(*, sentinel_case, aletheia_case, odin_case, out_dir,
                 input_verifier=None):
    """Build a Case Bundle v0.2 from three verified Histor-lite case folders.
    Raises a typed error on failure. `input_verifier` is injectable for tests."""
    # 1-3. Input dirs exist.
    for label, path, reason in (("Sentinel", sentinel_case, "SENTINEL_CASE_MISSING"),
                                ("Aletheia", aletheia_case, "ALETHEIA_CASE_MISSING"),
                                ("ODIN", odin_case, "ODIN_CASE_MISSING")):
        if not (isinstance(path, str) and os.path.isdir(path)):
            raise BuildPathError(reason, f"{label} case not found: {path!r}")

    # 4. Refuse a non-empty output dir.
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        raise BuildPathError("OUTPUT_DIR_NOT_EMPTY",
                             f"output directory is not empty: {out_dir!r}")

    # 5-8. Verify each input case (raises InputCaseError on failure).
    if input_verifier is None:
        input_verifier = InProcessInputVerifier()
    sentinel_facts = input_verifier.verify_sentinel(sentinel_case)
    aletheia_facts = input_verifier.verify_aletheia(aletheia_case)
    odin_facts = input_verifier.verify_odin(odin_case)

    # 9. Confirm all three case records share the same case_id.
    cids = {sentinel_facts["case_id"], aletheia_facts["case_id"],
            odin_facts["case_id"]}
    require(len(cids) == 1,
            f"case_id mismatch across input cases: sentinel="
            f"{sentinel_facts['case_id']!r}, aletheia="
            f"{aletheia_facts['case_id']!r}, odin={odin_facts['case_id']!r}",
            CaseIdMismatchError)
    case_id = next(iter(cids))

    # 10-12. Copy each case record verbatim into the bundle.
    os.makedirs(out_dir, exist_ok=True)
    _copy_case(sentinel_case, os.path.join(out_dir, versions.SENTINEL_DIR),
               versions.SENTINEL_FILES)
    _copy_case(aletheia_case, os.path.join(out_dir, versions.ALETHEIA_DIR),
               versions.ALETHEIA_FILES)
    _copy_case(odin_case, os.path.join(out_dir, versions.ODIN_DIR),
               versions.ODIN_FILES)

    # 13. Write canonical manifest.
    manifest = build_manifest(
        case_id=case_id, sentinel_facts=sentinel_facts,
        aletheia_facts=aletheia_facts, odin_facts=odin_facts)
    manifest_bytes = canonical_bytes(manifest)
    _write_bytes(os.path.join(out_dir, versions.MANIFEST_NAME), manifest_bytes)

    # 14. Write strict bundle checksums covering manifest + every packaged file.
    digests = {MANIFEST_KEY: sha256_bytes(manifest_bytes)}
    for key in REQUIRED_KEYS:
        if key == MANIFEST_KEY:
            continue
        digests[key] = sha256_file(os.path.join(out_dir, key))
    _write_bytes(os.path.join(out_dir, versions.CHECKSUMS_NAME),
                 format_checksums(digests))

    # 15. Self-verify before returning success.
    from case_bundle_v02_lib.verifier import verify_bundle
    verify_bundle(out_dir)

    return BuildResult(out_dir, manifest)
