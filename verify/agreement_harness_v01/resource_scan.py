"""Structural resource-management scanner (verification-only).

Flags resource acquisitions that are NOT context-managed:
  - unclosed reads:  the read-then-discard form, and json.load fed a bare
    open() call
  - bare archive construction that is not governed by ``with``

The call tokens this scanner hunts for are ASSEMBLED AT RUNTIME, so this
file's own source never contains the literal patterns. Without that, every
scan of the harness tree (which includes this file) would self-report a
false offender. The tokens are still applied literally to the files being
scanned, so a real leak in any scanned file is still caught.
"""

import re

# The read pattern uses escaped parentheses, so the literal regex text in
# THIS file does not itself match the compiled pattern (verified by the
# harness-tree self-test scanning this module and finding zero offenders).
_READ_RE = re.compile(r"open\([^)]*\)\.read\(\)|json\.load\(open\(")

# Assembled so the contiguous call token never appears literally here.
_ARCHIVE_TOKEN = "Zip" + "File("


def scan(src):
    """Return a sorted list of 'line:reason' offenders for one source blob."""
    offenders = []
    for m in _READ_RE.finditer(src):
        offenders.append("%d:unclosed-read" % (src[:m.start()].count("\n") + 1))
    start = 0
    while True:
        idx = src.find(_ARCHIVE_TOKEN, start)
        if idx < 0:
            break
        start = idx + len(_ARCHIVE_TOKEN)
        line_start = src.rfind("\n", 0, idx) + 1
        before = src[line_start:idx]
        # Safe only if a `with` governs this construction on the same line.
        if "with " not in before:
            offenders.append("%d:bare-archive" % (src[:idx].count("\n") + 1))
    return sorted(offenders)


def scan_path(path):
    with open(path) as handle:
        return scan(handle.read())
