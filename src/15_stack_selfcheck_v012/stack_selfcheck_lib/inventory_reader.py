"""Load and validate a stack inventory file (read-only)."""

import os

from . import canonical, validation, versions
from .errors import (CheckError, FAILED_INVENTORY_MISSING,
                     FAILED_INVENTORY_INVALID, FAILED_REQUIRED_COMPONENT_MISSING)

ALLOWED_TOP_FIELDS = frozenset({
    "stack_inventory_version", "stack_name", "components", "known_limitations"})
REQUIRED_TOP_FIELDS = ("stack_inventory_version", "stack_name", "components")

ALLOWED_COMPONENT_FIELDS = frozenset({
    "component_id", "expected_version", "component_type", "root_path",
    "zip_path", "sha256_path", "required", "sidecar_optional", "read_only",
    "evidence_component", "atlas_connected", "cli_file", "version_file",
    "legacy_documentation_profile"})
REQUIRED_COMPONENT_FIELDS = ("component_id", "expected_version",
                             "component_type", "root_path", "required")


def load_inventory(inventory_path):
    if not inventory_path or not os.path.isfile(inventory_path):
        raise CheckError(FAILED_INVENTORY_MISSING, "inventory file not found")
    raw = canonical.read_bytes(inventory_path)
    if not canonical.is_canonical_bytes(raw):
        raise CheckError(FAILED_INVENTORY_INVALID, "inventory is not canonical JSON")
    try:
        inventory = canonical.load_json(inventory_path)
    except ValueError:
        raise CheckError(FAILED_INVENTORY_INVALID, "inventory is not valid JSON")
    _validate_schema(inventory)
    return inventory


def _validate_schema(inv):
    if not isinstance(inv, dict):
        raise CheckError(FAILED_INVENTORY_INVALID, "inventory is not an object")
    unknown = set(inv) - ALLOWED_TOP_FIELDS
    if unknown:
        raise CheckError(FAILED_INVENTORY_INVALID,
                         "unknown inventory fields: %s" % sorted(unknown))
    for field in REQUIRED_TOP_FIELDS:
        if field not in inv:
            raise CheckError(FAILED_INVENTORY_INVALID, "missing field: %s" % field)
    if inv["stack_inventory_version"] != versions.STACK_INVENTORY_VERSION:
        raise CheckError(FAILED_INVENTORY_INVALID, "bad stack_inventory_version")
    if not isinstance(inv["stack_name"], str) or not inv["stack_name"]:
        raise CheckError(FAILED_INVENTORY_INVALID, "bad stack_name")
    components = inv["components"]
    if not isinstance(components, list) or not components:
        raise CheckError(FAILED_INVENTORY_INVALID, "components must be a non-empty list")
    seen = set()
    for comp in components:
        _validate_component(comp)
        cid = comp["component_id"]
        if cid in seen:
            raise CheckError(FAILED_INVENTORY_INVALID, "duplicate component_id: %s" % cid)
        seen.add(cid)


def _validate_component(comp):
    if not isinstance(comp, dict):
        raise CheckError(FAILED_INVENTORY_INVALID, "component is not an object")
    unknown = set(comp) - ALLOWED_COMPONENT_FIELDS
    if unknown:
        raise CheckError(FAILED_INVENTORY_INVALID,
                         "unknown component fields: %s" % sorted(unknown))
    for field in REQUIRED_COMPONENT_FIELDS:
        if field not in comp:
            raise CheckError(FAILED_INVENTORY_INVALID, "component missing: %s" % field)
    if not validation.is_safe_id(comp["component_id"]):
        raise CheckError(FAILED_INVENTORY_INVALID,
                         "unsafe component_id: %r" % comp.get("component_id"))
    if not validation.is_version(comp["expected_version"]):
        raise CheckError(FAILED_INVENTORY_INVALID,
                         "bad expected_version for %s" % comp["component_id"])
    if not isinstance(comp["required"], bool):
        raise CheckError(FAILED_INVENTORY_INVALID,
                         "required must be bool for %s" % comp["component_id"])
    if "legacy_documentation_profile" in comp:
        value = comp["legacy_documentation_profile"]
        if not isinstance(value, str) or not value:
            raise CheckError(
                FAILED_INVENTORY_INVALID,
                "legacy_documentation_profile must be a non-empty string for %s"
                % comp["component_id"])


def confirm_required_present(inventory):
    present = {c["component_id"] for c in inventory["components"]}
    for cid in versions.REQUIRED_COMPONENT_IDS:
        if cid not in present:
            raise CheckError(FAILED_REQUIRED_COMPONENT_MISSING,
                             "required component missing from inventory: %s" % cid)
