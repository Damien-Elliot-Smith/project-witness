# Histor-lite Aletheia Importer v0.1 — a deterministic importer that takes a
# verified Aletheia Evidence Bundle v0.1 and records it as a Histor-lite-style
# evidence case (summary + manifest copy + replay report + checksums). It preserves
# Aletheia's integrity status exactly, records integrity metadata only, and NEVER
# claims the evidence contents are true. It does not copy the evidence file, import
# ODIN, or connect to Coordinator/Companion.
from histor_aletheia_importer.versions import IMPORTER_VERSION

__all__ = ["IMPORTER_VERSION"]
