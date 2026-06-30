# tests/helpers.py
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_aletheia_importer.errors import AletheiaVerifyError  # noqa: E402

SHA = "fe482b5e524c67728f4f2b4f430cd10d9a25659641f995ae537b282ccd181e0b"


def manifest(evidence_status="VERIFIED_PRESENT", evidence_id="evidence_001",
             case_id="case_001", source_sha=SHA, bundled_sha=SHA, drop=None,
             extra=None):
    m = {
        "aletheia_evidence_bundle_version": "0.1.0",
        "case_id": case_id,
        "evidence_id": evidence_id,
        "source_file_name": "evidence.txt",
        "source_file_size_bytes": 15,
        "source_file_sha256": source_sha,
        "bundled_file_path": "evidence/evidence_001.bin",
        "bundled_file_sha256": bundled_sha,
        "bundle_status": "BUNDLED",
        "evidence_status": evidence_status,
        "created_at_utc": "2026-01-01T00:00:00Z",
        "known_limitations": ["..."],
    }
    if extra:
        m.update(extra)
    if drop:
        for k in drop:
            m.pop(k, None)
    return m


def make_bundle_dir(manifest_dict=None):
    """Create a temp Aletheia-shaped bundle dir with an evidence_manifest.json."""
    d = tempfile.mkdtemp(prefix="ale_bundle_")
    with open(os.path.join(d, "evidence_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest_dict if manifest_dict is not None else manifest(), f)
    return d


class FakeAletheiaVerifier:
    """In-process Aletheia verifier double. verify() returns True, or raises
    AletheiaVerifyError if constructed with ok=False."""

    def __init__(self, ok=True):
        self._ok = ok
        self.calls = []

    def verify(self, bundle_dir):
        self.calls.append(bundle_dir)
        if not self._ok:
            raise AletheiaVerifyError("ALETHEIA_VERIFY_FAILED",
                                      "fake Aletheia verify failure")
        return True


def import_with_fake(out_dir, *, bundle_dir=None, manifest_dict=None,
                     aletheia_root=None, ok=True):
    import histor_aletheia_importer.importer as importer
    if aletheia_root is None:
        aletheia_root = HERE
    if bundle_dir is None:
        bundle_dir = make_bundle_dir(manifest_dict)
    return importer.import_evidence(
        aletheia_root=aletheia_root, bundle_dir=bundle_dir, out_dir=out_dir,
        aletheia_verifier=FakeAletheiaVerifier(ok=ok))


def good_case(out_dir=None, **kwargs):
    if out_dir is None:
        out_dir = os.path.join(tempfile.mkdtemp(prefix="hist_case_"), "case")
    import_with_fake(out_dir, **kwargs)
    return out_dir
