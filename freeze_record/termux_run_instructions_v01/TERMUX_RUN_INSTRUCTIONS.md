# Project Witness — Termux Run Instructions

```text
Move: 51
Artifact: TERMUX_RUN_INSTRUCTIONS.md
Baseline: local_v1_candidate_v01.zip / Project_Witness_Runnable_Stack_Handoff_v01.zip
Status: Move 51 only. Does not modify frozen artifacts. Does not claim final Local v1 Release.
```

## What this is

Step-by-step instructions to run the Project Witness Local v1 Candidate verification
stack on an Android device using Termux.

No internet is required after the initial Termux setup.
No root is required.
No Python packages beyond the standard library are required.

---

## Step 1 — Install Termux

Install Termux from **F-Droid**, not the Google Play Store.
The Play Store version is outdated and will cause package errors.

F-Droid: https://f-droid.org/en/packages/com.termux/

After installing, open Termux and run:

```bash
pkg update && pkg upgrade -y
```

Accept any prompts. This may take a few minutes.

---

## Step 2 — Install Python

```bash
pkg install python -y
```

Verify:

```bash
python3 --version
```

Expected: `Python 3.11.x` or higher (exact version will vary).

---

## Step 3 — Install zip tools (for unpacking)

```bash
pkg install unzip -y
```

---

## Step 4 — Transfer the handoff package to your device

You need `Project_Witness_Runnable_Stack_Handoff_v01.zip` on your device.

**Option A — USB / file manager:**
Copy the zip to your device storage, then move it into Termux's home directory:

```bash
cp /sdcard/Download/Project_Witness_Runnable_Stack_Handoff_v01.zip ~/
```

**Option B — Direct download (if you have a URL):**

```bash
pkg install wget -y
wget -O ~/Project_Witness_Runnable_Stack_Handoff_v01.zip <YOUR_URL>
```

---

## Step 5 — Verify the zip before extracting

```bash
cd ~
sha256sum Project_Witness_Runnable_Stack_Handoff_v01.zip
```

Expected SHA256:

```text
a84fabe6b7f70254c45986457b569917149d0a3c7310465f15f8b31e2596cfa4
```

If it does not match, do not proceed. The file is corrupt or wrong.

---

## Step 6 — Extract

```bash
unzip Project_Witness_Runnable_Stack_Handoff_v01.zip -d ~/project_witness/
```

---

## Step 7 — Run

```bash
cd ~/project_witness/Project_Witness_Runnable_Stack_Handoff_v01
python3 RUN_STACK.py
```

---

## Expected output

A successful run ends with:

```text
PROJECT_WITNESS_RUNNABLE_STACK_VERIFIED
verify_ok = true
Report written to run_output/verification_report.json
```

The full verification report is at:

```text
run_output/verification_report.json
```

---

## If something goes wrong

**"python3: command not found"**
Run `pkg install python -y` and try again.

**"unzip: command not found"**
Run `pkg install unzip -y` and try again.

**SHA256 mismatch on the handoff zip**
The downloaded file is corrupt or wrong. Re-transfer and verify again.

**"VERIFY_FAIL:" in the output**
Open `run_output/verification_report.json`. The `failure` field names the exact
step that failed. Do not modify frozen artifacts to fix it — report the failure.

**Permission errors on /sdcard/**
Termux requires storage permission. Run:

```bash
termux-setup-storage
```

Then re-copy the file.

---

## What this run proves

A passing run proves that:

- the handoff zip arrived intact (SHA256 matches)
- the included `local_v1_candidate_v01.zip` is internally consistent
- the Local v1 Candidate verifier passes on your device
- the embedded Local Demo Pack verifier passes on your device

It does not prove external truth, source trust, production readiness,
signing, anchoring, or tamper-proofing beyond the hash chain.

---

## Cleanup after review

```bash
rm -rf ~/project_witness/Project_Witness_Runnable_Stack_Handoff_v01/run_workspace/
```

The `run_workspace/` folder contains extracted working files and can be safely deleted.
`run_output/` contains your verification report and can be kept for reference.

---

## Version note

These instructions target the Local v1 Candidate (Move 50).
They do not apply to any future release.
Move 52 (Linux Desktop Run Instructions) is separate.
