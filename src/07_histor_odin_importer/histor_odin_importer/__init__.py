# Histor-lite ODIN Importer v0.1 — a deterministic importer that takes a verified
# ODIN Claim Reasoner v0.1 output and records it as a Histor-lite-style reasoning
# case (summary + verbatim report/trace/claims copies + replay report + checksums).
# It preserves ODIN's reasoning status exactly (both CONSISTENT and
# CONTRADICTION_DETECTED are valid outcomes; INVALID_INPUT is refused), records
# structural reasoning metadata only, and NEVER claims any claim is true. It does
# not import Aletheia evidence metadata or connect to Coordinator/Companion.
from histor_odin_importer.versions import IMPORTER_VERSION

__all__ = ["IMPORTER_VERSION"]
