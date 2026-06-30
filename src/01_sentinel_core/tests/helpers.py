# tests/helpers.py
# Shared helpers for Sentinel tests.

import os
import tempfile

from sentinel_core.action_schema import ACTION_SCHEMA_VERSION
from sentinel_core.journal import Journal
from sentinel_core.kernel import Kernel
from sentinel_core.manifest import build_manifest
from sentinel_core.persistence import AtomicFileBackend
from sentinel_core.receipts import ReceiptChain


def make_request(request_id, target_path, dry_run=False,
                 action_type="CREATE_DIRECTORY", schema_version=ACTION_SCHEMA_VERSION):
    # v1.1.0: requests carry NO allowed_root. The boundary comes from the run
    # manifest only.
    return {
        "request_id": request_id,
        "action_type": action_type,
        "target_path": target_path,
        "dry_run": dry_run,
        "preconditions": ["target_absent", "parent_exists", "inside_allowed_root"],
        "postconditions": ["target_exists", "target_is_directory"],
        "schema_version": schema_version,
    }


def new_kernel(run_id, allowed_root, runs_dir):
    run_path = os.path.join(runs_dir, f"{run_id}.json")
    chain = ReceiptChain(run_id=run_id)
    run_data = build_manifest(run_id, allowed_root)
    journal = Journal(AtomicFileBackend(run_path), chain, run_data)
    return Kernel(journal), run_path


def temp_root():
    return tempfile.mkdtemp(prefix="sentinel_root_")


def temp_runs():
    return tempfile.mkdtemp(prefix="sentinel_runs_")
