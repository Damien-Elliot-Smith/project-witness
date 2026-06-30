# Aletheia -> ODIN Bridge v0.1 — a deterministic bridge that converts a verified
# Aletheia Evidence Bundle v0.1 into an ODIN Claim Reasoner v0.1 claim set. It
# generates ONLY integrity/presence claims (evidence.present,
# evidence.integrity_verified) and never interprets evidence contents or asserts
# their truth. No signing, no external anchoring.
from aletheia_odin_bridge.versions import BRIDGE_VERSION

__all__ = ["BRIDGE_VERSION"]
