# Windows Notes

Honest notes for reviewers who want to inspect or attempt to run the Project
Witness working stack on Windows. Plain and technical. No hype.

This is roadmap **Move 53**. It is a **notes / readiness** document, **not** a full
native Windows port. See the boundary statement below.

---

## Tested-environment boundary (read first)

Native Windows execution has **not** been directly tested. The environments that
have actually been run and verified are Termux (Android) and Linux-style POSIX
shells. Nothing in this document should be read as a guarantee that the stack runs
natively on Windows. Windows native support is **not claimed** here because it has
not been tested. If and when it is tested directly, this document will be updated
to say so explicitly.

Until then, treat Windows as: **safe to inspect; recommended to run via WSL2.**

## What Windows users can inspect safely

Regardless of whether you run anything, you can safely inspect the package on
Windows:

- Read the Markdown documents (`START_HERE.md`, `REVIEWER_QUICKSTART.md`,
  `LINUX_DESKTOP_RUN_INSTRUCTIONS.md`, `MOVE_INDEX.md`, `STACK_STATUS.md`, this file).
- Read the component source under `src/` in any text editor or IDE.
- Verify the download checksum (see below).
- List the zip contents without extracting.

None of this executes any code.

## Recommended path: WSL2 + Ubuntu

The reliable way to actually run and verify the stack on a Windows machine is the
Windows Subsystem for Linux (**WSL2**):

1. Install WSL2 with an Ubuntu distribution (Microsoft documents the current
   `wsl --install` procedure).
2. Open the Ubuntu (WSL2) shell.
3. Inside WSL2, follow `LINUX_DESKTOP_RUN_INSTRUCTIONS.md` exactly. WSL2 provides
   the POSIX shell, `python3`, `unzip`, and `sha256sum` that those instructions
   assume, so the stack behaves as it does on Linux.

This is the recommended route precisely because it uses the already-verified
Linux/POSIX path rather than an untested native one.

## Verify the checksum on Windows

You do not need WSL2 to check the download integrity. In PowerShell:

```powershell
Get-FileHash .\Project_Witness_WORKING_STACK_v04_MOVE_53.zip -Algorithm SHA256
```

Compare the printed hash against the value in
`Project_Witness_WORKING_STACK_v04_MOVE_53.zip.sha256`. Or with Command Prompt:

```bat
certutil -hashfile Project_Witness_WORKING_STACK_v04_MOVE_53.zip SHA256
```

The hashes must match exactly (case-insensitive). If they do not, do not proceed.

## If you attempt a native Windows run (untested)

This is not a supported or verified path. If you try it anyway, you would likely
need:

- **Python 3** (3.8+) on `PATH`.
- **PowerShell** or **Command Prompt**.
- A way to extract the zip (Explorer's built-in extract, or `Expand-Archive` in
  PowerShell).
- Checksum verification via `Get-FileHash` or `certutil` (above).

The helper scripts in `tools/` are POSIX shell (`.sh`) and are written for `sh`.
They are not Windows batch or PowerShell scripts and will not run under Command
Prompt or PowerShell directly. Under a native attempt you would be invoking the
underlying Python entry points yourself, which is exactly why WSL2 is recommended
instead.

## Likely issues to watch for (native attempt)

- **Line endings.** If any shell script or text input is converted to Windows
  CRLF line endings (for example by a Git checkout with autocrlf, or by an
  editor), POSIX `sh` may misparse `.sh` scripts. Keep LF endings. Running inside
  WSL2 avoids this.
- **Path separators.** The stack and its instructions use forward-slash POSIX
  paths. Native Windows backslash paths and drive letters are a common source of
  breakage in an untested native run.
- **Shell availability.** There is no POSIX `sh` in stock Windows; the `tools/*.sh`
  wrappers assume one. WSL2 (or Git Bash, also untested here) provides it.
- **Temp directories and permissions.** The live demo writes to a temporary
  directory; behaviour of `mktemp`-style paths differs outside a POSIX shell.

## Network and packages

- **No network is required.** The stack is fully offline.
- **No external Python packages are required** unless proven otherwise. It is
  standard-library Python only. If any command reports a missing third-party
  module, stop and report it — that would be a defect, not an expected step.

## Known PASS markers (from the existing validator, via WSL2/Linux)

When run via the verified path (WSL2 or Linux), the expected markers are:

| Command | Expected marker |
|---|---|
| `sh tools/validate_handoff.sh` | `HANDOFF_VALIDATION: PASS` |
| `sh tools/run_all_tests.sh` | `RESULT: PASS — ALL_COMPONENT_TESTS_PASSED` (18/18, 1234 tests) |
| `sh tools/run_independent_verify.sh` | `PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED` / `verify_ok = true` |
| `sh tools/run_local_v1_verify.sh` | `LOCAL_V1_CANDIDATE_VERIFIED` / `verify_ok = true` |
| `sh tools/run_termux_verify.sh` | `TERMUX_RUN_INSTRUCTIONS_VERIFIED` / `verify_ok = true` |
| `sh tools/run_demo.sh` | `COMPANION_COMPLETED` … `verify_ok: true` |

## What failure means

- **Checksum mismatch** — the download is incomplete or altered; do not run it.
- **A test or verifier FAIL** — the relevant output is printed and the command
  exits non-zero; do not treat the stack as verified. Read the output.
- **A `.sh` script "not recognized" / parse error on native Windows** — expected:
  these are POSIX shell scripts. Use WSL2.
- **A missing third-party module error** — not expected; report it.

## Expected limitations

- No GUI, no app, no network service, no cloud, no signing, no external anchoring.
- This stack verifies structured provenance relationships under tested local
  conditions only. It does not prove external truth, authenticate real-world
  identity, or establish source trust.
- It is not production-ready. It is a Local v1 **Candidate**, not a final Local v1
  Release. The roadmap is complete **through Move 53** (this document); Moves
  54–70 remain future work. The 70-step roadmap is not complete.
