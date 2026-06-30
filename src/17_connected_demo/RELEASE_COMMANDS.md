# Release Commands — Project Witness Connected Demo v0.1

Run each from a clean extraction of `connected_demo_v01/`.

    python3 -m compileall -q .
    python3 -m unittest discover -s tests -v
    python3 -O -m unittest discover -s tests -v
    python3 connected_demo.py selfcheck
    sha256sum -c connected_demo_v01.sha256
