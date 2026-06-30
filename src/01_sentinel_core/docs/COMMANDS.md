# Commands

Sentinel ships a thin operator CLI in `sentinel.py`. It never parses natural
language: each command assembles an exact structured request or operates on a
run file. No shell, no LLM.

```
python3 sentinel.py --version
python3 sentinel.py <command> [options]
```

## create

Process one `CREATE_DIRECTORY` request. Creates the run file if it does not
exist, otherwise appends to an open run (refuses a closed one).

```
python3 sentinel.py create \
    --run RUN_FILE \
    --run-id RUN_ID \
    --request-id REQ_ID \
    --target-path REL_OR_ABS_PATH \
    [--allowed-root ROOT_DIR] \
    [--dry-run]
```

- `--allowed-root` configures the **run**, not the request. It is required when
  the run file does not yet exist (it is recorded, absolute, in the manifest).
  When appending to an existing run it must be omitted — or, if supplied, it
  must canonicalise (realpath) to the same directory as the manifest root,
  otherwise the command refuses. The manifest root is authoritative; a request
  can never choose its own boundary.
- `--dry-run` evaluates and records a `DRY_RUN` receipt without creating
  anything.
- Prints the resulting receipt summary and reason code. For an allowed create
  this is the RESULT receipt of the INTENT->RESULT pair (v0.2); `inspect` shows
  both stages.

Example:

```
python3 sentinel.py create --run run.json --run-id demo \
    --request-id REQ-001 --target-path demo/output --allowed-root ./workspace
```

## create-from-file

Process a request supplied as a JSON file (must match the action schema).

```
python3 sentinel.py create-from-file --run RUN_FILE --run-id RUN_ID \
    --request-file REQUEST.json
```

## close

Close an open run. Emits the final `ALLOW_SESSION_CLOSE` receipt and writes the
run seal. Refuses an already-closed run.

```
python3 sentinel.py close --run RUN_FILE
```

## replay

Re-derive a saved run through a fresh kernel and report per-receipt matches.
Exit code is `0` on PASS, `1` on FAIL.

```
python3 sentinel.py replay --run RUN_FILE [--allow-open]
```

- Without `--allow-open`, replay runs in **closed/audit** mode and requires a
  valid run seal (rejecting a deleted final receipt or missing seal).
- With `--allow-open`, replay accepts an unsealed (still-open) run, for
  debugging a run in progress.

## inspect

Print a human-readable summary of a run file (run id, allowed_root, version,
receipt count, closed flag, and a one-line view of each receipt).

```
python3 sentinel.py inspect --run RUN_FILE
```

## Self-check

Not part of the CLI, but the key operational command:

```
python3 selfcheck.py        # run ALL gates; non-zero exit on any failure
python3 -O selfcheck.py     # same with assertions stripped (must still pass)
python3 selfcheck.py --skip-unit-gates   # lightweight: skip the two gates that
                                         # launch the unit-test suite
```

`--skip-unit-gates` exists to break a recursion: the unit-test suite has a test
that runs selfcheck, and selfcheck's `unit_tests` / `unit_tests_-O` gates launch
the unit-test suite. The in-suite test uses `--skip-unit-gates`, so plain
`python3 -m unittest discover -s tests` never triggers a nested full selfcheck.
The full `python3 selfcheck.py` remains the release gate and is run directly,
not from inside test discovery. Every `subprocess.run` in tests and selfcheck
carries an explicit `timeout`, so any hang fails closed instead of blocking.
