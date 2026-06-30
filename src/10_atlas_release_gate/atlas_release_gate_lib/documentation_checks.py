"""Documentation boundary and honesty checks for an Atlas release folder."""


def _normalize(text):
    return " ".join(text.lower().split())


# Each requirement: a tuple of acceptable phrasings; any one present satisfies it.
_DOC_BOUNDARIES = (
    ("read_only_registry",
     ("read-only registry", "read only registry",
      "registry is read-only", "registry is read only")),
    ("no_run_workflows",
     ("does not run workflows", "do not run workflows",
      "does not run project witness workflows")),
    ("no_prove_truth",
     ("does not prove truth", "do not prove truth")),
    ("not_connected_coordinator",
     ("not connected to coordinator", "does not connect atlas to coordinator",
      "does not connect to coordinator")),
    ("not_connected_companion",
     ("not connected to companion", "does not connect atlas to companion",
      "does not connect to companion")),
    ("no_llm",
     ("no llm", "does not use llm", "no llm integration")),
    ("no_signing",
     ("no signing", "does not sign", "does not sign or externally anchor")),
    ("no_external_anchoring",
     ("no external anchoring", "does not externally anchor",
      "does not sign or externally anchor")),
)

# The honesty boundary is satisfied by the registry's honest read-only / no-run
# /no-truth boundary, expressed through ANY equivalent statement. It must NOT
# require the exact phrase "does not modify the registry", because frozen Atlas
# Registry v0.1 was frozen using equivalent wording (e.g. "read-only registry",
# "records vocabulary", "does not call components", "does not decide truth").
# Each concept group is satisfied if any one of its phrasings is present.
_HONESTY_STATEMENTS = (
    ("read_only_or_vocabulary",
     ("read-only registry", "read only registry", "registry is read-only",
      "records vocabulary", "vocabulary registry",
      "does not modify the registry", "does not modify registry")),
    ("no_workflows_or_calls",
     ("does not run workflows", "do not run workflows",
      "does not call components", "does not call other components")),
    ("no_prove_or_decide_truth",
     ("does not prove truth", "do not prove truth",
      "does not decide truth", "do not decide truth")),
)


def check_documentation(doc_text):
    """Return a list of missing documentation-boundary names (empty if all present)."""
    norm = _normalize(doc_text)
    return [name for name, options in _DOC_BOUNDARIES
            if not any(opt in norm for opt in options)]


def check_honesty(doc_text):
    """Return a list of missing honesty-statement names (empty if all present)."""
    norm = _normalize(doc_text)
    return [name for name, options in _HONESTY_STATEMENTS
            if not any(opt in norm for opt in options)]
