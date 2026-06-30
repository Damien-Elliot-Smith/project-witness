# ODIN Claim Reasoner v0.1 — a deterministic mini-reasoner over already-structured
# claims. It validates a claim set, detects DIRECT structural contradictions
# (same subject + predicate with a different object, or same object with opposite
# polarity), preserves support references, and emits a canonical reasoning report
# and proof trace. It does NOT prove claims true, interpret natural language, use
# an LLM, or execute actions.
from odin_reasoner.versions import ODIN_REASONER_VERSION

__all__ = ["ODIN_REASONER_VERSION"]
