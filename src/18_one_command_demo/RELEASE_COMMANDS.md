# Release Commands — One-Command Demo Script v0.1

Run each from a clean extraction of `one_command_demo_script_v01/`.

    python3 -m compileall -q .
    python3 -m unittest discover -s tests -v
    python3 -O -m unittest discover -s tests -v
    python3 one_command_demo.py selfcheck
    python3 -O one_command_demo.py selfcheck
    python3 -W error::ResourceWarning -m unittest discover -s tests -v
    sha256sum -c one_command_demo_script_v01.sha256
    python3 verify_release_manifest.py

The default unit tests use fake Connected Demo outputs and spawn no subprocesses;
they do not require the real frozen components.
