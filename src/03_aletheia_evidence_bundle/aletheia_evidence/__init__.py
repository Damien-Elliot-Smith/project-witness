# Aletheia Evidence Bundle v0.1 — a deterministic tool that bundles ONE local
# file as evidence: it hashes the file, records metadata in a canonical manifest,
# writes a checksums file, and verifies the bundle later. It proves preservation
# and hash consistency only — never the truth of the file's contents. No signing,
# no external anchoring, no content interpretation.
from aletheia_evidence.versions import ALETHEIA_EVIDENCE_BUNDLE_VERSION

__all__ = ["ALETHEIA_EVIDENCE_BUNDLE_VERSION"]
