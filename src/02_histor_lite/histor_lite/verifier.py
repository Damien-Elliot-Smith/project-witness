# histor_lite/verifier.py
# The boundary to the frozen Sentinel verifier.
#
# Histor-lite does NOT reimplement Sentinel semantics. It locates the frozen
# Sentinel package, imports its replay verifier in-process, and asks it for a
# verdict. Any failure to locate, import, or run the verifier is surfaced as a
# typed error so the caller can refuse the import rather than crash.
#
# We invoke in-process (not via subprocess) so that we read the exact verdict
# string and full report directly, with no stdout parsing and no subprocess
# pipe to leave open. A verifier exception is caught and converted to
# VerifierUnavailable, satisfying "if Sentinel replay cannot be run: refuse".

import os
import sys

from histor_lite.errors import require, VerifierUnavailable


class SentinelVerdict:
    """A normalised result from the frozen Sentinel verifier."""
    __slots__ = ("verdict", "ok", "report")

    def __init__(self, verdict, ok, report):
        self.verdict = verdict
        self.ok = ok
        self.report = report


def _replay_module_path(sentinel_root: str) -> str:
    return os.path.join(sentinel_root, "sentinel_core", "replay.py")


def verifier_available(sentinel_root: str) -> bool:
    """True if sentinel_root looks like a usable frozen Sentinel extraction."""
    return (os.path.isdir(sentinel_root)
            and os.path.isdir(os.path.join(sentinel_root, "sentinel_core"))
            and os.path.isfile(_replay_module_path(sentinel_root)))


def run_sentinel_replay(sentinel_root: str, run_path: str) -> SentinelVerdict:
    """Run the frozen Sentinel verifier on run_path and return a SentinelVerdict.

    Raises VerifierUnavailable if the verifier cannot be located, imported, or
    executed (a verifier crash is treated as "cannot be run", never swallowed
    into a fake pass).
    """
    require(os.path.isdir(sentinel_root),
            f"Sentinel root does not exist: {sentinel_root!r}", VerifierUnavailable)
    require(os.path.isfile(_replay_module_path(sentinel_root)),
            f"Sentinel verifier module not found under {sentinel_root!r} "
            f"(expected sentinel_core/replay.py)", VerifierUnavailable)

    root = os.path.abspath(sentinel_root)
    inserted = False
    if root not in sys.path:
        sys.path.insert(0, root)
        inserted = True
    # Python caches imported modules. If a `sentinel_core` from a DIFFERENT root
    # was imported earlier in this process, `from sentinel_core...` would reuse
    # it instead of loading the verifier at THIS root. Drop any cached
    # sentinel_core* modules so the import below resolves against `root`.
    _evicted = [name for name in list(sys.modules)
                if name == "sentinel_core" or name.startswith("sentinel_core.")]
    for name in _evicted:
        del sys.modules[name]
    try:
        # Import the frozen verifier. Imports are cached; we do not reload, so a
        # single Sentinel root per process is assumed (true for the CLI).
        try:
            from sentinel_core.replay import replay_from_path
        except Exception as e:  # noqa: BLE001 - any import failure => unavailable
            raise VerifierUnavailable(
                f"Could not import the frozen Sentinel verifier: "
                f"{type(e).__name__}: {e}")

        try:
            result = replay_from_path(run_path)
        except Exception as e:  # noqa: BLE001 - a verifier crash => unavailable
            raise VerifierUnavailable(
                f"Sentinel verifier raised while replaying {run_path!r}: "
                f"{type(e).__name__}: {e}")

        # The frozen ReplayResult exposes .verdict/.ok/.report. Read defensively.
        verdict = getattr(result, "verdict", None)
        ok = getattr(result, "ok", None)
        report = getattr(result, "report", "")
        require(isinstance(verdict, str) and verdict != "",
                "Sentinel verifier returned no verdict string", VerifierUnavailable)
        require(isinstance(ok, bool),
                "Sentinel verifier returned a non-boolean ok flag", VerifierUnavailable)
        return SentinelVerdict(verdict=verdict, ok=ok, report=str(report))
    finally:
        if inserted and root in sys.path:
            sys.path.remove(root)
