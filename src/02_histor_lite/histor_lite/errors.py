# histor_lite/errors.py
# Typed errors and a require() guard. We never use bare `assert` in runtime code
# (it is stripped under `python -O`); require() raises a typed error instead.


class HistorLiteError(Exception):
    """Base class for all Histor-lite errors."""


class VerifierUnavailable(HistorLiteError):
    """The frozen Sentinel verifier could not be located or invoked."""


class ImportRefused(HistorLiteError):
    """A Sentinel run was not accepted for import (refused verdict, missing or
    malformed run, or verifier failure). Carries a machine-stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class CaseError(HistorLiteError):
    """A case output folder is missing, malformed, or fails integrity checks."""


def require(condition, message, error_cls=HistorLiteError):
    """Raise error_cls(message) if condition is falsey. Never a bare assert."""
    if not condition:
        raise error_cls(message)
