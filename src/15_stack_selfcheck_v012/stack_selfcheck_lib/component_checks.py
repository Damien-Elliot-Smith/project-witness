"""Per-component root, expected-file, and version checks (read-only)."""

import os

from . import validation
from .errors import (CheckError, FAILED_COMPONENT_ROOT_MISSING,
                     FAILED_DOCUMENTATION_BOUNDARY, FAILED_COMPONENT_VERSION_MISMATCH)

REQUIRED_DOC_FILES = ("README.md", "KNOWN_LIMITATIONS.md", "RELEASE_COMMANDS.md")


def check_root(comp):
    root = comp.get("root_path")
    if not validation.is_dir(root):
        raise CheckError(FAILED_COMPONENT_ROOT_MISSING,
                         "component root missing: %s" % comp["component_id"])


def check_expected_files(comp, allowed_missing=frozenset()):
    """Confirm the required documentation and CLI files are present.

    `allowed_missing` is the set of documentation filenames this component is
    explicitly permitted to omit under a recorded legacy profile (empty for all
    non-legacy components). A required documentation file that is missing AND
    not in `allowed_missing` fails exactly as in v0.1. The CLI file, when
    declared, is never covered by a legacy allowance.

    Returns the sorted list of documentation files that were both permitted and
    actually omitted, so the caller can record the allowance honestly.
    """
    root = comp["root_path"]
    omitted = []
    for name in REQUIRED_DOC_FILES:
        if os.path.isfile(os.path.join(root, name)):
            continue
        if name in allowed_missing:
            omitted.append(name)
            continue
        raise CheckError(FAILED_DOCUMENTATION_BOUNDARY,
                         "%s missing %s" % (comp["component_id"], name))
    cli_file = comp.get("cli_file")
    if cli_file and not os.path.isfile(os.path.join(root, cli_file)):
        raise CheckError(FAILED_DOCUMENTATION_BOUNDARY,
                         "%s missing CLI file %s" % (comp["component_id"], cli_file))
    return sorted(omitted)


def check_version(comp):
    version_file = comp.get("version_file")
    if version_file:
        path = os.path.join(comp["root_path"], version_file)
        if not os.path.isfile(path):
            raise CheckError(FAILED_COMPONENT_VERSION_MISMATCH,
                             "%s version_file missing" % comp["component_id"])
        with open(path, "r", encoding="utf-8") as handle:
            observed = handle.read()
        if comp["expected_version"] not in observed:
            raise CheckError(FAILED_COMPONENT_VERSION_MISMATCH,
                             "%s version mismatch" % comp["component_id"])
