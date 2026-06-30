# Run Format — One-Command Demo Script v0.1

## Output folder (success)

Exactly these top-level entries, and no others:

    one_command_demo_report.json
    one_command_demo_steps.json
    one_command_demo_checksums.txt
    connected_demo_output/

`connected_demo_output/` is the real, unmodified output of the frozen Connected
Demo v0.1.

## one_command_demo_report.json

Canonical JSON (sorted keys, tight separators, no trailing newline). On success:

    {
      "one_command_demo_script_version": "0.1.0",
      "wrapper_status": "ONE_COMMAND_DEMO_COMPLETED",
      "connected_demo_status": "DEMO_COMPLETED",
      "companion_status": "COMPANION_COMPLETED",
      "coordinator_workflow_status": "WORKFLOW_COMPLETED",
      "atlas_validation_status": "ATLAS_VALIDATED",
      "source_status": "SOURCE_VERIFIED",
      "stack_verification_status": "STACK_VERIFIED",
      "stack_selfcheck_status": "STACK_SELFCHECK_PASSED",
      "truth_boundary_valid": true,
      "known_limitations": [ ... ]
    }

Allowed `wrapper_status` values:

    ONE_COMMAND_DEMO_COMPLETED
    FAILED_CONFIG_INVALID
    FAILED_CONNECTED_DEMO_RUN
    FAILED_CONNECTED_DEMO_VERIFY
    FAILED_REQUIRED_STATUS_MISSING
    FAILED_TRUTH_BOUNDARY
    FAILED_CHECKSUMS_INVALID

The report stores statuses and limitations only. It never stores absolute paths
and never makes a truth claim.

## one_command_demo_steps.json

Fixed order:

    step_001 VALIDATE_CONFIG
    step_002 CHECK_CONNECTED_DEMO_ROOT
    step_003 RUN_CONNECTED_DEMO
    step_004 VERIFY_CONNECTED_DEMO
    step_005 READ_CONNECTED_DEMO_REPORT
    step_006 CHECK_REQUIRED_STATUSES
    step_007 WRITE_ONE_COMMAND_REPORT
    step_008 VERIFY_ONE_COMMAND_OUTPUT

Each step status is one of `COMPLETED`, `FAILED`, `SKIPPED_AFTER_FAILURE`. If a
step fails, every later step is `SKIPPED_AFTER_FAILURE`.

## one_command_demo_checksums.txt

Exactly two lines, each `<lowercase-sha256>  <name>`:

    <digest>  one_command_demo_report.json
    <digest>  one_command_demo_steps.json

Required keys must appear exactly once. Duplicate, missing, or unknown keys fail;
a malformed or uppercase digest fails; a hash mismatch fails. Lowercase SHA-256
only.
