# Run Format — Project Witness Connected Demo v0.1

`run` produces, under the output folder:

    companion_output/            (Companion v0.3.1 output, drives Coordinator v0.3.2)
    manifest_output/             (Unified Case Manifest v0.1 output)
    stack_verifier_output/       (Stack Verifier v0.1 output)
    stack_selfcheck_output/      (Stack Selfcheck v0.1.2 output)
    connected_demo_report.json   (canonical; the seven statuses)
    connected_demo_checksums.txt (sha256 of the report)

`connected_demo_report.json` records `demo_status`, `observed_statuses` (the six
required terminal statuses), the per-stage results, and the required-status map.
It contains no absolute evidence paths and makes no truth claim.
