# sentinel_core/persistence.py
# Persistence backends and the single permitted filesystem executor.
#
# Two responsibilities live here, kept deliberately separate from decision
# logic:
#   1. Durable, atomic writing of the run file (write temp -> fsync -> replace
#      -> best-effort dir fsync).
#   2. The ONLY place a directory is ever created: execute_create_directory,
#      which calls os.mkdir (no shell, no mkdirs, no overwrite).
#
# Persistence-before-commit is enforced by the journal: it calls backend.write
# and only mutates in-memory chain/session state if the write returned without
# raising. A VolatileTestBackend exists for tests that must prove a write
# failure prevents commit; it is explicitly labelled non-authoritative.

import json
import os
import tempfile
import warnings
from abc import ABC, abstractmethod

from sentinel_core.errors import PersistenceFailure

PERSISTENCE_MODE_ATOMIC = "ATOMIC_REPLACE_FILE_FSYNC_DIRECTORY_FSYNC_BEST_EFFORT"
PERSISTENCE_MODE_VOLATILE = "VOLATILE_TEST_MODE__NOT_AUTHORITATIVE__DO_NOT_RELEASE"


class DirectorySyncWarning(RuntimeWarning):
    """Run file was replaced, but parent-directory fsync was unavailable."""


class PersistenceBackend(ABC):
    @abstractmethod
    def write(self, data: dict) -> None:
        """Durably persist the full run-file data. Raise PersistenceFailure on error."""

    @abstractmethod
    def is_volatile(self) -> bool:
        ...

    @abstractmethod
    def mode_label(self) -> str:
        ...


class AtomicFileBackend(PersistenceBackend):
    def __init__(self, run_path: str):
        self._run_path = run_path
        self._dir = os.path.dirname(os.path.abspath(run_path)) or "."
        os.makedirs(self._dir, exist_ok=True)

    def is_volatile(self) -> bool:
        return False

    def mode_label(self) -> str:
        return PERSISTENCE_MODE_ATOMIC

    def write(self, data: dict) -> None:
        try:
            serialised = json.dumps(data, indent=2, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise PersistenceFailure(f"JSON serialisation failed: {e}") from e

        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=self._dir, prefix=".tmp_run_", suffix=".json")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(serialised)
                    f.flush()
                    os.fsync(f.fileno())
            except OSError as e:
                raise PersistenceFailure(f"Write/fsync failed: {e}") from e

            try:
                os.replace(tmp_path, self._run_path)
                tmp_path = None
            except OSError as e:
                raise PersistenceFailure(f"Atomic replace failed: {e}") from e

            try:
                dir_fd = os.open(self._dir, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except (OSError, AttributeError) as e:
                warnings.warn(
                    f"Run file replaced, but parent-directory fsync was unavailable: {e}",
                    DirectorySyncWarning,
                )
        except PersistenceFailure:
            raise
        except Exception as e:
            raise PersistenceFailure(f"Unexpected persistence error: {e}") from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


class VolatileTestBackend(PersistenceBackend):
    """Non-authoritative in-memory backend for tests. Never writes to disk."""

    def __init__(self):
        self.last_data = None

    def is_volatile(self) -> bool:
        return True

    def mode_label(self) -> str:
        return PERSISTENCE_MODE_VOLATILE

    def write(self, data: dict) -> None:
        self.last_data = data


class FailingTestBackend(PersistenceBackend):
    """Backend whose write always fails, to prove persistence-before-commit."""

    def is_volatile(self) -> bool:
        return True

    def mode_label(self) -> str:
        return PERSISTENCE_MODE_VOLATILE

    def write(self, data: dict) -> None:
        raise PersistenceFailure("Injected persistence failure (test backend)")


class FailAfterNWritesBackend(PersistenceBackend):
    """Durably writes the first n_ok writes, then fails every subsequent write.

    Used to prove the v0.2 RESULT-persistence-failure case: the INTENT write
    (write #1) succeeds and is committed, mkdir runs, then the RESULT write
    (write #2) fails — leaving the run in a RESULT_MISSING_AFTER_INTENT state
    that the loader and replay must detect and fail closed on. Wraps a real
    AtomicFileBackend so the successful writes are genuinely on disk.
    """

    def __init__(self, real_backend, n_ok: int):
        self._real = real_backend
        self._n_ok = n_ok
        self._count = 0

    def is_volatile(self) -> bool:
        return self._real.is_volatile()

    def mode_label(self) -> str:
        return self._real.mode_label()

    def write(self, data: dict) -> None:
        self._count += 1
        if self._count <= self._n_ok:
            self._real.write(data)
            return
        raise PersistenceFailure(
            f"Injected persistence failure on write #{self._count} (test backend)")


def execute_create_directory(resolved_target: str) -> None:
    """Create exactly one directory at resolved_target.

    Uses os.mkdir (single level, never mkdirs), never a shell. os.mkdir raises
    FileExistsError if the target exists, giving us a final fail-closed guard
    against a race between policy check and execution. Errors are surfaced as
    PersistenceFailure so the kernel records a controlled ERROR receipt.
    """
    try:
        os.mkdir(resolved_target)
    except FileExistsError as e:
        raise PersistenceFailure(f"Target already exists at execution time: {e}") from e
    except OSError as e:
        raise PersistenceFailure(f"mkdir failed: {e}") from e
