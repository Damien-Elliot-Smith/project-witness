"""Shared, authoritative test fixtures.

One deterministic no-Cargo environment builder, used by self_tests.py,
gate_unit_tests.py, and the integration tests, so the implementation cannot
drift between copies (a duplicated copy retaining the old inherited-PATH
enumeration is exactly what broke v23 on Android's non-listable /product/bin).

It resolves ONLY an explicit allowlist of commands and NEVER enumerates any
inherited PATH directory: on Android, /system/bin, /product/bin, and vendor
directories may exist but not be listable by the Termux app process, so listing
PATH directories is not portable. Command resolution uses shutil.which, which
stats specific files rather than listing whole directories.
"""

import os
import shutil
import tempfile

# Commands tools/check_rust_workspace.sh needs. cargo/rustc/rustup are
# DELIBERATELY excluded so the no-toolchain path is genuinely proven.
WORKSPACE_REQUIRED_CMDS = ("sh", "python3", "awk", "grep", "sed", "sort",
                           "uniq", "head", "tail", "tr", "dirname")
EXCLUDED_TOOLCHAIN = ("cargo", "rustc", "rustup")


def build_isolated_bin_without_cargo(required=WORKSPACE_REQUIRED_CMDS):
    """Build a temp bin/ containing ONLY the allowlisted commands, as symlinks
    to their resolved real paths. cargo/rustc/rustup are absent. No directory is
    enumerated. Returns (tmpdir, bindir, missing) where ``missing`` names, by
    command, anything that could not be resolved so the caller can report it.
    """
    tmp = tempfile.mkdtemp(prefix="nocargo_")
    bindir = os.path.join(tmp, "bin")
    os.mkdir(bindir)
    missing = []
    for name in required:
        src = shutil.which(name)
        if not src or not os.access(src, os.X_OK):
            missing.append(name)
            continue
        # link to the resolved real path; on a multicall host the applet
        # identity is preserved by the symlink's own basename (argv[0]).
        os.symlink(os.path.realpath(src), os.path.join(bindir, name))
    return tmp, bindir, missing
