# atlas_registry_lib/verifier.py
# Verify an Atlas registry is structurally valid. Returns REGISTRY_VERIFIED only if
# every rule passes. Atlas records vocabulary; it never decides truth, and it
# refuses any entry that claims truth.

import json
import os

from atlas_registry_lib.canonical import canonical_bytes
from atlas_registry_lib.errors import require, RegistryError
from atlas_registry_lib.validation import validate_id, is_safe_id
from atlas_registry_lib import versions

_SCHEMA = versions.FAILED_SCHEMA_INVALID
_DUP = versions.FAILED_DUPLICATE_ENTRY
_NONCANON = versions.FAILED_NON_CANONICAL_JSON
_TRUTH = versions.FAILED_TRUTH_CLAIM


class VerifyResult:
    __slots__ = ("registry_status", "registry", "counts")

    def __init__(self, registry_status, registry, counts):
        self.registry_status = registry_status
        self.registry = registry
        self.counts = counts


def _require_list_of_dicts(reg, key):
    val = reg.get(key)
    require(isinstance(val, list), f"{key} must be a list", RegistryError,
            registry_status=_SCHEMA, reason="SECTION_NOT_LIST")
    for item in val:
        require(isinstance(item, dict), f"{key} entries must be objects",
                RegistryError, registry_status=_SCHEMA, reason="ENTRY_NOT_OBJECT")
    return val


def _no_dupes(values, *, reason, label):
    seen = set()
    for v in values:
        require(v not in seen, f"duplicate {label}: {v!r}", RegistryError,
                registry_status=_DUP, reason=reason)
        seen.add(v)


def load_registry(path):
    require(os.path.isfile(path), f"registry file not found: {path!r}",
            RegistryError, registry_status=_SCHEMA, reason="REGISTRY_MISSING")
    with open(path, "rb") as f:
        raw = f.read()
    try:
        reg = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise RegistryError(_NONCANON, "REGISTRY_NOT_JSON",
                            f"registry is not valid JSON: {e}")
    # 3. Require canonical JSON.
    require(canonical_bytes(reg) == raw,
            "registry is not in canonical JSON form", RegistryError,
            registry_status=_NONCANON, reason="NON_CANONICAL")
    return reg


def verify_registry_obj(reg) -> VerifyResult:
    """Verify an already-parsed registry dict (rules 4-23)."""
    require(isinstance(reg, dict), "registry must be an object", RegistryError,
            registry_status=_SCHEMA, reason="NOT_OBJECT")

    # 4-5. Required top-level fields only.
    keys = set(reg.keys())
    missing = set(versions.REQUIRED_TOP_FIELDS) - keys
    require(not missing, f"registry missing top-level fields: {sorted(missing)}",
            RegistryError, registry_status=_SCHEMA, reason="MISSING_TOP_FIELD")
    unknown = keys - set(versions.REQUIRED_TOP_FIELDS)
    require(not unknown, f"unknown top-level fields: {sorted(unknown)}",
            RegistryError, registry_status=_SCHEMA, reason="UNKNOWN_TOP_FIELD")

    require(reg["atlas_registry_version"] == versions.ATLAS_REGISTRY_VERSION,
            f"unexpected atlas_registry_version "
            f"{reg['atlas_registry_version']!r}", RegistryError,
            registry_status=_SCHEMA, reason="BAD_VERSION")
    validate_id(reg["registry_id"], label="registry_id")

    components = _require_list_of_dicts(reg, "components")
    workflow_types = _require_list_of_dicts(reg, "workflow_types")
    action_types = _require_list_of_dicts(reg, "action_types")
    statuses = _require_list_of_dicts(reg, "statuses")
    predicates = _require_list_of_dicts(reg, "claim_predicates")
    record_types = _require_list_of_dicts(reg, "case_record_types")
    require(isinstance(reg["known_limitations"], list),
            "known_limitations must be a list", RegistryError,
            registry_status=_SCHEMA, reason="LIMITATIONS_NOT_LIST")

    # ---- components ----
    comp_ids = []
    comp_names = []
    for c in components:
        for field in ("component_id", "component_name", "component_version",
                      "component_type", "frozen_status", "description"):
            require(field in c, f"component missing {field}", RegistryError,
                    registry_status=_SCHEMA, reason="COMPONENT_FIELD_MISSING")
        # 11. id valid; 12. version is string.
        validate_id(c["component_id"], label="component_id")
        require(isinstance(c["component_version"], str)
                and c["component_version"] != "",
                f"component_version must be a string: {c['component_id']}",
                RegistryError, registry_status=_SCHEMA, reason="VERSION_NOT_STRING")
        # 13. allowed component_type.
        require(c["component_type"] in versions.ALLOWED_COMPONENT_TYPES,
                f"invalid component_type {c['component_type']!r}", RegistryError,
                registry_status=_SCHEMA, reason="BAD_COMPONENT_TYPE")
        # 14. allowed frozen_status.
        require(c["frozen_status"] in versions.ALLOWED_FROZEN_STATUS,
                f"invalid frozen_status {c['frozen_status']!r}", RegistryError,
                registry_status=_SCHEMA, reason="BAD_FROZEN_STATUS")
        comp_ids.append(c["component_id"])
        comp_names.append(c["component_name"])
    # 6. no duplicate component ids (and names).
    _no_dupes(comp_ids, reason="DUP_COMPONENT_ID", label="component_id")
    _no_dupes(comp_names, reason="DUP_COMPONENT_NAME", label="component_name")

    # ---- workflow_types ----
    wt_names = []
    for w in workflow_types:
        require("workflow_type" in w, "workflow_type entry missing workflow_type",
                RegistryError, registry_status=_SCHEMA, reason="WT_FIELD_MISSING")
        validate_id(w["workflow_type"], label="workflow_type")
        wt_names.append(w["workflow_type"])
    _no_dupes(wt_names, reason="DUP_WORKFLOW_TYPE", label="workflow_type")

    # ---- action_types ----
    at_names = []
    for a in action_types:
        require("action_type" in a, "action_type entry missing action_type",
                RegistryError, registry_status=_SCHEMA, reason="AT_FIELD_MISSING")
        validate_id(a["action_type"], label="action_type")
        # forbidden (out-of-roadmap) action types.
        require(a["action_type"] not in versions.FORBIDDEN_ACTION_TYPES,
                f"forbidden action_type {a['action_type']!r}", RegistryError,
                registry_status=_SCHEMA, reason="FORBIDDEN_ACTION_TYPE")
        at_names.append(a["action_type"])
    _no_dupes(at_names, reason="DUP_ACTION_TYPE", label="action_type")

    # ---- statuses ----
    status_group_pairs = []
    all_status_names = set()
    for s in statuses:
        for field in ("status", "status_group", "meaning", "truth_claim",
                      "allowed_contexts"):
            require(field in s, f"status missing {field}", RegistryError,
                    registry_status=_SCHEMA, reason="STATUS_FIELD_MISSING")
        name = s["status"]
        require(is_safe_id(name), f"unsafe status name {name!r}", RegistryError,
                registry_status=_SCHEMA, reason="UNSAFE_STATUS")
        # 15. truth_claim must be a bool and false.
        require(isinstance(s["truth_claim"], bool),
                f"status {name} truth_claim must be boolean", RegistryError,
                registry_status=_SCHEMA, reason="TRUTH_CLAIM_NOT_BOOL")
        require(s["truth_claim"] is False,
                f"status {name} claims truth (truth_claim=true)", RegistryError,
                registry_status=_TRUTH, reason="STATUS_TRUTH_CLAIM")
        # 17. truth-like status names refused.
        require(name.upper() not in versions.FORBIDDEN_STATUS_NAMES,
                f"truth-like status name {name!r}", RegistryError,
                registry_status=_TRUTH, reason="STATUS_TRUTH_NAME")
        status_group_pairs.append((s["status_group"], name))
        all_status_names.add(name)
    # 9. no duplicate status within the same group.
    _no_dupes(status_group_pairs, reason="DUP_STATUS_IN_GROUP",
              label="status-in-group")

    # ---- claim_predicates ----
    pred_names = []
    for p in predicates:
        for field in ("predicate", "meaning", "allowed_object_types",
                      "truth_claim", "introduced_by_component"):
            require(field in p, f"predicate missing {field}", RegistryError,
                    registry_status=_SCHEMA, reason="PRED_FIELD_MISSING")
        pname = p["predicate"]
        require(is_safe_id(pname), f"unsafe predicate {pname!r}", RegistryError,
                registry_status=_SCHEMA, reason="UNSAFE_PREDICATE")
        # 16. truth_claim must be false.
        require(isinstance(p["truth_claim"], bool),
                f"predicate {pname} truth_claim must be boolean", RegistryError,
                registry_status=_SCHEMA, reason="PRED_TRUTH_NOT_BOOL")
        require(p["truth_claim"] is False,
                f"predicate {pname} claims truth", RegistryError,
                registry_status=_TRUTH, reason="PREDICATE_TRUTH_CLAIM")
        # 18. truth-like predicates refused.
        require(pname not in versions.FORBIDDEN_PREDICATES,
                f"truth-like predicate {pname!r}", RegistryError,
                registry_status=_TRUTH, reason="PREDICATE_TRUTH_NAME")
        pred_names.append(pname)
    _no_dupes(pred_names, reason="DUP_PREDICATE", label="predicate")

    # ---- case_record_types ----
    rt_names = []
    for r in record_types:
        for field in ("record_type", "produced_by_component", "required_files",
                      "description"):
            require(field in r, f"record type missing {field}", RegistryError,
                    registry_status=_SCHEMA, reason="RECORD_FIELD_MISSING")
        validate_id(r["record_type"], label="record_type")
        rt_names.append(r["record_type"])
    _no_dupes(rt_names, reason="DUP_RECORD_TYPE", label="record_type")

    # 19-22. Required current vocabulary present.
    for cid in versions.REQUIRED_COMPONENT_IDS:
        require(cid in comp_ids, f"required component missing: {cid}",
                RegistryError, registry_status=_SCHEMA,
                reason="REQUIRED_COMPONENT_MISSING")
    for wt in versions.REQUIRED_WORKFLOW_TYPES:
        require(wt in wt_names, f"required workflow_type missing: {wt}",
                RegistryError, registry_status=_SCHEMA,
                reason="REQUIRED_WORKFLOW_MISSING")
    for at in versions.REQUIRED_ACTION_TYPES:
        require(at in at_names, f"required action_type missing: {at}",
                RegistryError, registry_status=_SCHEMA,
                reason="REQUIRED_ACTION_MISSING")
    for st in versions.REQUIRED_STATUSES:
        require(st in all_status_names, f"required status missing: {st}",
                RegistryError, registry_status=_SCHEMA,
                reason="REQUIRED_STATUS_MISSING")
    for pred in versions.REQUIRED_PREDICATES:
        require(pred in pred_names, f"required predicate missing: {pred}",
                RegistryError, registry_status=_SCHEMA,
                reason="REQUIRED_PREDICATE_MISSING")

    counts = {
        "component_count": len(components),
        "workflow_type_count": len(workflow_types),
        "action_type_count": len(action_types),
        "status_count": len(statuses),
        "claim_predicate_count": len(predicates),
        "case_record_type_count": len(record_types),
    }
    # 23. Structurally valid.
    return VerifyResult(versions.REGISTRY_VERIFIED, reg, counts)


def verify_registry(path) -> VerifyResult:
    """Load (rules 1-3) + verify (rules 4-23) a registry file."""
    reg = load_registry(path)
    return verify_registry_obj(reg)
