# Atlas Registry v0.1 — a read-only registry of Project Witness vocabulary and
# component metadata (components, versions, workflow/action types, statuses, claim
# predicates, case record types). It verifies registry structure and exports a
# canonical summary. It runs no workflows, calls no components, decides no truth, and
# is not connected to Coordinator or Companion.
from atlas_registry_lib.versions import ATLAS_REGISTRY_VERSION

__all__ = ["ATLAS_REGISTRY_VERSION"]
