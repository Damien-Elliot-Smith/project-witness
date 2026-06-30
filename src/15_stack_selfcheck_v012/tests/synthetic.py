"""Synthetic component folders, inventory files, and Stack Verifier output for
tests and selfcheck. Standard library only; no real frozen components, no
subprocesses."""

import hashlib
import json
import os
import zipfile

from stack_selfcheck_lib import versions as _versions

# (component_id, version, type, read_only, evidence_component, atlas_connected)
_SPECS = (
    ("sentinel_core_v022", "0.2.2", "SENTINEL", False, False, False),
    ("histor_lite_v012", "0.1.2", "HISTOR", False, False, False),
    ("case_bundle_v011", "0.1.1", "CASE_BUNDLE", False, False, False),
    ("coordinator_workflow_v018", "0.1.8", "COORDINATOR", False, False, False),
    ("companion_cli_v01", "0.1.0", "COMPANION", False, False, False),
    ("aletheia_evidence_bundle_v01", "0.1.0", "ALETHEIA", False, False, False),
    ("odin_claim_reasoner_v01", "0.1.0", "ODIN", False, False, False),
    ("aletheia_odin_bridge_v01", "0.1.0", "BRIDGE", False, False, False),
    ("evidence_reasoning_demo_v01", "0.1.0", "DEMO", True, False, False),
    ("histor_lite_aletheia_importer_v01", "0.1.0", "IMPORTER", False, False, False),
    ("histor_lite_odin_importer_v01", "0.1.0", "IMPORTER", False, False, False),
    ("case_bundle_v02", "0.2.0", "CASE_BUNDLE", False, False, False),
    ("coordinator_workflow_v02", "0.2.0", "COORDINATOR", False, False, False),
    ("companion_cli_v02", "0.2.0", "COMPANION", False, False, False),
    ("atlas_registry_v01", "0.1.0", "REGISTRY", True, False, True),
    ("atlas_release_gate_v01", "0.1.0", "GATE", True, False, True),
    ("atlas_red_blue_pack_v01", "0.1.0", "REVIEW_PACK", True, False, True),
    ("coordinator_workflow_v03", "0.3.0", "COORDINATOR", False, False, True),
    ("companion_cli_v03", "0.3.0", "COMPANION", False, False, True),
    ("unified_case_manifest_v01", "0.1.0", "MANIFEST", True, True, False),
    ("stack_verifier_v01", "0.1.0", "VERIFIER", True, True, False),
    ("stack_selfcheck_v01", "0.1.0", "SELFCHECK", True, True, False),
)


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def _doc_text(cid, read_only, evidence_component, atlas_connected):
    lines = ["# %s" % cid, "", "This component does not prove truth."]
    if read_only:
        lines.append("It does not run workflows.")
    if evidence_component:
        lines.append("It does not copy evidence contents.")
    if atlas_connected:
        lines.append("Atlas is read-only.")
    lines += [
        "It does not sign or externally anchor outputs.",
        "It does not use an LLM and does not use natural language.",
        "No GUI. No queues or concurrency.",
    ]
    return "\n".join(lines) + "\n"


def build_component_folder(root, cid, version, read_only=False,
                           evidence_component=False, atlas_connected=False,
                           cli_file="selfcheck.py", omit=()):
    os.makedirs(root, exist_ok=True)
    doc = _doc_text(cid, read_only, evidence_component, atlas_connected)
    files = {
        "README.md": doc,
        "KNOWN_LIMITATIONS.md": doc,
        "RELEASE_COMMANDS.md": "python3 selfcheck.py\n",
    }
    if cli_file:
        files[cli_file] = "# %s cli stub\n" % cid
    for name, content in files.items():
        if name in omit:
            continue
        _write(os.path.join(root, name), content)
    return root


def make_zip_and_sidecar(folder, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _dirs, names in os.walk(folder):
            for n in names:
                full = os.path.join(dirpath, n)
                zf.write(full, os.path.relpath(full, os.path.dirname(folder)))
    digest = _sha(zip_path)
    sidecar = zip_path + ".sha256"
    _write(sidecar, "%s  %s\n" % (digest, os.path.basename(zip_path)))
    return zip_path, sidecar


def build_inventory(work, with_zips=True, overrides=None, omit_doc=None,
                    stack_name=None, omit_docs=None, legacy_profiles=None):
    """Build all 22 synthetic components and a canonical inventory file.
    `overrides` maps component_id -> dict of inventory-field overrides.
    `omit_docs` maps component_id -> iterable of documentation filenames to omit
    from that component's folder (generalises the single `omit_doc`).
    `legacy_profiles` maps component_id -> legacy_documentation_profile string to
    declare on that component's inventory entry.
    """
    overrides = overrides or {}
    omit_docs = {k: tuple(v) for k, v in (omit_docs or {}).items()}
    legacy_profiles = legacy_profiles or {}
    comps = []
    for cid, version, ctype, read_only, ev, atlas in _SPECS:
        root = os.path.join(work, "components", cid)
        omit = omit_docs.get(cid, ())
        if omit_doc and omit_doc[0] == cid:
            omit = tuple(set(omit) | {omit_doc[1]})
        build_component_folder(root, cid, version, read_only, ev, atlas, omit=omit)
        entry = {
            "component_id": cid, "expected_version": version,
            "component_type": ctype, "root_path": root, "required": True,
            "read_only": read_only, "evidence_component": ev,
            "atlas_connected": atlas, "cli_file": "selfcheck.py",
        }
        if cid in legacy_profiles:
            entry["legacy_documentation_profile"] = legacy_profiles[cid]
        if with_zips and cid != "stack_selfcheck_v01":
            zip_path = os.path.join(work, "zips", cid + ".zip")
            os.makedirs(os.path.dirname(zip_path), exist_ok=True)
            zp, sc = make_zip_and_sidecar(root, zip_path)
            entry["zip_path"] = zp
            entry["sha256_path"] = sc
        else:
            entry["sidecar_optional"] = True
        if cid in overrides:
            entry.update(overrides[cid])
        comps.append(entry)
    inventory = {
        "stack_inventory_version": "0.1.0",
        "stack_name": stack_name or _versions.STACK_NAME,
        "components": comps,
        "known_limitations": [
            "Stack Selfcheck v0.1 checks stack inventory and release hygiene only.",
            "It does not run workflows.", "It does not prove truth."],
    }
    inv_path = os.path.join(work, "stack_inventory.json")
    _write(inv_path, _canon(inventory))
    return inv_path


def build_stack_verifier_output(run, stack_verification_status="STACK_VERIFIED",
                                truth_boundary_valid=True, atlas_vocabulary_valid=True):
    os.makedirs(run, exist_ok=True)
    report = {
        "stack_verifier_version": "0.1.0", "source_type": "companion_v03_output",
        "stack_verification_status": stack_verification_status,
        "source_status": "SOURCE_VERIFIED", "manifest_status": "NOT_PROVIDED",
        "case_id": "case_abc0000000000000", "evidence_id": "evidence_001",
        "truth_boundary_valid": truth_boundary_valid,
        "atlas_vocabulary_valid": atlas_vocabulary_valid,
        "checked_artifacts": [], "known_limitations": ["does not prove truth"],
    }
    steps = {"stack_verification_steps_version": "0.1.0",
             "steps": [{"step_id": "step_001", "operation": "X", "status": "COMPLETED"}]}
    _write(os.path.join(run, "stack_verification_report.json"), _canon(report))
    _write(os.path.join(run, "stack_verification_steps.json"), _canon(steps))
    keys = ("stack_verification_report.json", "stack_verification_steps.json")
    lines = ["%s  %s" % (_sha(os.path.join(run, k)), k) for k in keys]
    _write(os.path.join(run, "stack_verification_checksums.txt"),
           ("\n".join(lines) + "\n").encode("utf-8"))
    return run
