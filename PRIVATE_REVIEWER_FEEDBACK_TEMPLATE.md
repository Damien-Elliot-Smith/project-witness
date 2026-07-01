# Private Reviewer Feedback Template

Use this template after reviewing the Project Witness Local v1 Candidate package.
Plain notes are fine. Exact failures matter more than polished writing.

## Reviewer

- Name / handle:
- Date:
- Operating system:
- Python version:
- Shell used:
- Package reviewed:

## Fresh extraction

- Checksum command run:
- Checksum result:
- Extraction command run:
- Any extraction warnings or path issues:

## Commands run

Record the command and final marker.

| Command | Exit code | Final marker / result |
|---|---:|---|
| `sh tools/validate_handoff.sh` |  |  |
| `sh tools/check_repository_structure.sh` |  |  |
| `sh tools/check_private_reviewer_package.sh` |  |  |
| `sh tools/check_linux_desktop_instructions.sh` |  |  |
| `sh tools/check_windows_notes.sh` |  |  |

## What passed

-

## What failed or confused you

-

## Claims that look too strong

List any sentence that seems to overclaim. Quote the file name and line/context if
possible.

-

## Missing or stale files

-

## Safety / honesty issues

Examples: hidden dependency, network assumption, production claim, source-trust
claim, identity-authentication claim, signing/anchoring implication, unclear
failure mode.

-

## Release blockers

What must be fixed before a cautious public Local v1 release?

-

## Suggested fixes

-

## Final verdict

Choose one and add a short reason:

- `PASS FOR PRIVATE REVIEW ONLY`
- `PASS WITH MINOR DOC FIXES`
- `BLOCKED UNTIL FIXED`
- `UNABLE TO RUN`

Reason:
