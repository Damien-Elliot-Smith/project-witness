# tests/helpers.py
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_odin_bridge.errors import (  # noqa: E402
    AletheiaVerifyError, OdinValidateError)

_SHA = "fe482b5e524c67728f4f2b4f430cd10d9a25659641f995ae537b282ccd181e0b"


def manifest(evidence_status="VERIFIED_PRESENT", evidence_id="evidence_001",
             case_id="case_001", sha=_SHA, extra=None, drop=None):
    """A valid Aletheia v0.1-shaped manifest dict."""
    m = {
        "aletheia_evidence_bundle_version": "0.1.0",
        "case_id": case_id,
        "evidence_id": evidence_id,
        "source_file_name": "input.txt",
        "source_file_size_bytes": 15,
        "source_file_sha256": sha,
        "bundled_file_path": "evidence/evidence_001.bin",
        "bundled_file_sha256": sha,
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
    """Create a temp Aletheia-shaped bundle directory with an
    evidence_manifest.json (only the manifest is needed; the fake verifier does not
    re-read the evidence file)."""
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


class FakeOdinValidator:
    """In-process ODIN validator double. validate() returns True, or raises
    OdinValidateError if constructed with ok=False."""

    def __init__(self, ok=True):
        self._ok = ok
        self.calls = []

    def validate(self, claim_set):
        self.calls.append(claim_set)
        if not self._ok:
            raise OdinValidateError("ODIN_VALIDATE_FAILED",
                                    "fake ODIN validation failure")
        return True


def convert_with_fakes(out_dir, *, bundle_dir=None, manifest_dict=None,
                       aletheia_root=None, odin_root="ODIN", aletheia_ok=True,
                       odin_ok=True):
    """Run bridge.convert with in-process fakes. aletheia_root/odin_root default to
    the package dir (which exists) so path checks pass; pass odin_root=None to skip
    ODIN validation."""
    import bridge
    if aletheia_root is None:
        aletheia_root = HERE
    if odin_root == "ODIN":
        odin_root = HERE
    if bundle_dir is None:
        bundle_dir = make_bundle_dir(manifest_dict)
    return bridge.convert(
        aletheia_root=aletheia_root, odin_root=odin_root, bundle_dir=bundle_dir,
        out_dir=out_dir, aletheia_verifier=FakeAletheiaVerifier(ok=aletheia_ok),
        odin_validator=FakeOdinValidator(ok=odin_ok))


def good_output(out_dir=None):
    """Produce a valid bridge output folder using fakes; return its path."""
    if out_dir is None:
        out_dir = os.path.join(tempfile.mkdtemp(prefix="bridge_out_"), "out")
    convert_with_fakes(out_dir)
    return out_dir


SHA = _SHA
