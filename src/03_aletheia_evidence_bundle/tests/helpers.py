# tests/helpers.py
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_evidence.builder import build_bundle  # noqa: E402


def make_source(content=b"hello evidence\n", name="evidence.txt"):
    """Create a temp source file, return its path."""
    d = tempfile.mkdtemp(prefix="aletheia_src_")
    p = os.path.join(d, name)
    with open(p, "wb") as f:
        f.write(content)
    return p


def make_bundle(content=b"hello evidence\n", case_id="case_001",
                evidence_id="evidence_001"):
    """Build a valid bundle in a temp dir; return (bundle_dir, source_path)."""
    src = make_source(content)
    out = os.path.join(tempfile.mkdtemp(prefix="aletheia_out_"), "bundle")
    build_bundle(source_file=src, case_id=case_id, evidence_id=evidence_id,
                 out_dir=out)
    return out, src
