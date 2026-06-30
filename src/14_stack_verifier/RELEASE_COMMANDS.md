# Release Commands — Stack Verifier v0.1

The authoritative freeze gate is this explicit list of individual commands. Run
each from a clean extraction of `stack_verifier_v01/`. All must pass.

    python3 -m compileall -q .
    python3 -m unittest discover -s tests -v
    python3 -O -m unittest discover -s tests -v
    python3 selfcheck.py
    python3 -O selfcheck.py
    python3 -W error::ResourceWarning -m unittest discover -s tests
    sha256sum -c stack_verifier_v01.sha256
    python3 verify_release_manifest.py

A Python subprocess orchestrator is deliberately NOT the freeze gate. Any
convenience wrapper that may exist is optional only; the list above is
authoritative.
