# Evidence Reasoning Demo v0.1 — a deterministic demo runner that proves the local
# chain executes and verifies: one local evidence file -> Aletheia Evidence Bundle
# v0.1 -> Aletheia->ODIN Bridge v0.1 -> ODIN Claim Reasoner v0.1 -> verified demo
# output. It proves only that the integrity-reasoning chain runs and verifies; it
# does NOT prove the evidence contents are true, interpret the file, use an LLM, or
# gate actions. Not connected to Companion or Coordinator.
from evidence_reasoning_demo.versions import DEMO_VERSION

__all__ = ["DEMO_VERSION"]
