"""Atlas release-folder structural validation (read-only)."""

import os

REQUIRED_FILES = (
    "README.md",
    "KNOWN_LIMITATIONS.md",
    "RUN_FORMAT.md",
    "RELEASE_COMMANDS.md",
    "REPAIR_LEDGER.md",
    "atlas.py",
    "selfcheck.py",
    "verify_release_manifest.py",
    os.path.join("registry", "atlas_registry.json"),
)
REQUIRED_DIRS = ("atlas_registry_lib", "tests")
TEST_RESULTS_ALTERNATIVES = ("TEST_RESULTS.md", "TEST_RESULTS.pdf")


def atlas_root_exists(atlas_root):
    return bool(atlas_root) and os.path.isdir(atlas_root)


def missing_required(atlas_root):
    """Return a sorted list of missing required entries (empty if complete)."""
    missing = []
    for rel in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(atlas_root, rel)):
            missing.append(rel)
    for rel in REQUIRED_DIRS:
        if not os.path.isdir(os.path.join(atlas_root, rel)):
            missing.append(rel + "/")
    if not any(os.path.isfile(os.path.join(atlas_root, alt))
               for alt in TEST_RESULTS_ALTERNATIVES):
        missing.append("TEST_RESULTS.md|TEST_RESULTS.pdf")
    return sorted(missing)


def registry_present(atlas_root):
    return os.path.isfile(os.path.join(atlas_root, "registry", "atlas_registry.json"))
