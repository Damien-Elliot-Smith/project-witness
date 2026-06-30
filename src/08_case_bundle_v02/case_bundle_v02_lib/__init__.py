# Case Bundle v0.2 — a portable Project Witness case bundle exporter. It combines
# three already-verified Histor-lite case records (Sentinel action, Aletheia
# evidence, ODIN reasoning) into one deterministic bundle: it verifies each input
# case, confirms they share a case_id, copies each record verbatim, and writes a
# canonical manifest + strict checksums, then self-verifies. It packages verified
# records only and NEVER claims the evidence contents or any ODIN claim is true. It
# does not execute actions, run Aletheia, or run ODIN reasoning, and is not
# connected to Coordinator or Companion.
from case_bundle_v02_lib.versions import CASE_BUNDLE_VERSION

__all__ = ["CASE_BUNDLE_VERSION"]
