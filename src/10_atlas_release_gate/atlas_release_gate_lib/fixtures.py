"""Deterministic fake Atlas Registry v0.1 root builder.

Used by selfcheck and the unit tests to produce an Atlas-shaped release folder
without requiring the real frozen Atlas component.
"""

import os

from . import canonical

GOOD_README = (
    "# Atlas Registry v0.1\n"
    "\n"
    "The Atlas registry is a read-only registry.\n"
    "It does not run workflows.\n"
    "It does not prove truth.\n"
    "It is not connected to Coordinator.\n"
    "It is not connected to Companion.\n"
    "It uses no LLM.\n"
    "It performs no signing.\n"
    "It performs no external anchoring.\n"
    "It does not modify the registry.\n"
)

GOOD_KNOWN_LIMITATIONS = (
    "# Known Limitations\n"
    "\n"
    "- read-only registry\n"
    "- does not run workflows\n"
    "- does not prove truth\n"
    "- not connected to Coordinator\n"
    "- not connected to Companion\n"
    "- no LLM\n"
    "- no signing\n"
    "- no external anchoring\n"
)

GOOD_REGISTRY = {
    "atlas_registry_version": "0.1.0",
    "terms": {
        "evidence": {"id": "evidence", "kind": "node"},
        "claim": {"id": "claim", "kind": "node"},
        "chain": {"id": "chain", "kind": "edge"},
    },
}

# Documentation wording representative of the real frozen Atlas Registry v0.1.
# It expresses the honesty boundary through equivalent statements and does NOT
# contain the exact phrase "does not modify the registry".
FROZEN_ATLAS_README = (
    "# Atlas Registry v0.1\n"
    "\n"
    "Atlas Registry v0.1 is a read-only registry.\n"
    "It records vocabulary.\n"
    "It does not run workflows.\n"
    "It does not prove truth.\n"
    "It does not call components.\n"
    "It does not decide truth.\n"
    "It is not connected to Coordinator.\n"
    "It is not connected to Companion.\n"
    "It uses no LLM.\n"
    "It performs no signing.\n"
    "It performs no external anchoring.\n"
)

FROZEN_ATLAS_KNOWN_LIMITATIONS = (
    "# Known Limitations\n"
    "\n"
    "- read-only registry\n"
    "- records vocabulary\n"
    "- does not run workflows\n"
    "- does not prove truth\n"
    "- does not call components\n"
    "- does not decide truth\n"
    "- not connected to Coordinator\n"
    "- not connected to Companion\n"
    "- no LLM\n"
    "- no signing\n"
    "- no external anchoring\n"
)

# Documentation wording that mirrors the genuine frozen Atlas Registry v0.1 and
# exercises the forbidden-feature scanner's false-positive surface: forbidden
# terms appearing as registry vocabulary, listed components, refused
# out-of-roadmap actions, and out-of-scope items -- none of them affirmative
# support claims.
FROZEN_ATLAS_FEATURE_WORDING = (
    "Atlas Registry v0.1 records the canonical vocabulary the stack uses: "
    "components and their versions, workflow types, action types, the status "
    "vocabulary, claim predicates, and case record types.\n"
    "The status vocabulary spans Sentinel, ODIN, Case Bundle, Coordinator, "
    "Companion, workflow steps, and verification.\n"
    "Coordinator and Companion are listed as components.\n"
    "It does not run workflows and does not call any component.\n"
    "It is not connected to Coordinator and not connected to Companion.\n"
    "No natural language, no LLM, no signing, no external anchoring.\n"
    "It also refuses out-of-roadmap action types: WRITE_FILE, DELETE_FILE, "
    "SHELL_COMMAND, NETWORK_CALL.\n"
    "No queue, no concurrency, no schema migration, no plugin system, no "
    "ontology expansion.\n"
    "Defeating that requires signing or external anchoring, which are out of "
    "scope here.\n"
)

_OTHER_FILES = {
    "RUN_FORMAT.md": "# Run Format\n",
    "RELEASE_COMMANDS.md": "# Release Commands\n",
    "REPAIR_LEDGER.md": "# Repair Ledger\n",
    "TEST_RESULTS.md": "# Test Results\n",
    "atlas.py": "# atlas (frozen)\n",
    "selfcheck.py": "# atlas selfcheck (frozen)\n",
    "verify_release_manifest.py": "# atlas manifest (frozen)\n",
}


def make_fake_atlas_root(base_dir, omit=None, registry_obj=None,
                         readme_text=None, limitations_text=None):
    """Create a fake Atlas Registry v0.1 release folder under base_dir.

    omit: iterable of relative names to leave out (e.g. {"README.md"} or
          {"registry/atlas_registry.json"}).
    """
    omit = set(omit or ())
    root = base_dir
    os.makedirs(os.path.join(root, "registry"), exist_ok=True)
    if "atlas_registry_lib" not in omit:
        os.makedirs(os.path.join(root, "atlas_registry_lib"), exist_ok=True)
        canonical.atomic_write_bytes(
            os.path.join(root, "atlas_registry_lib", "__init__.py"), b"")
    if "tests" not in omit:
        os.makedirs(os.path.join(root, "tests"), exist_ok=True)
        canonical.atomic_write_bytes(
            os.path.join(root, "tests", "__init__.py"), b"")

    readme = readme_text if readme_text is not None else GOOD_README
    limits = limitations_text if limitations_text is not None else GOOD_KNOWN_LIMITATIONS

    files = {"README.md": readme, "KNOWN_LIMITATIONS.md": limits}
    files.update(_OTHER_FILES)
    for name, text in files.items():
        if name in omit:
            continue
        canonical.atomic_write_bytes(
            os.path.join(root, name), text.encode("utf-8"))

    if ("registry/atlas_registry.json" not in omit) and ("registry" not in omit):
        reg = registry_obj if registry_obj is not None else GOOD_REGISTRY
        canonical.write_canonical(
            os.path.join(root, "registry", "atlas_registry.json"), reg)
    return root
