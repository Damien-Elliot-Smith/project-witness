# case_bundle_v02_lib/errors.py
# Typed errors and a require() guard (never a bare assert; -O strips asserts).


class CaseBundleError(Exception):
    """Base class for all Case Bundle v0.2 errors."""


class ValidationError(CaseBundleError):
    """Input / ID validation failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class InputCaseError(CaseBundleError):
    """An input case folder is missing or fails verification. Carries the
    bundle_status that should be reported and a stable reason."""

    def __init__(self, bundle_status, reason, message):
        self.bundle_status = bundle_status
        self.reason = reason
        super().__init__(message)


class CaseIdMismatchError(CaseBundleError):
    """The three input cases do not share a single case_id."""

    def __init__(self, message):
        self.bundle_status = "FAILED_CASE_ID_MISMATCH"
        self.reason = "CASE_ID_MISMATCH"
        super().__init__(message)


class BuildPathError(CaseBundleError):
    """A path problem (missing input dir, non-empty output dir)."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class VerifyError(CaseBundleError):
    """Bundle verification failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


def require(condition, message, error_cls=CaseBundleError, **kwargs):
    """Raise error_cls(message) if condition is falsey. Never a bare assert."""
    if not condition:
        if "bundle_status" in kwargs and "reason" in kwargs:
            raise error_cls(kwargs["bundle_status"], kwargs["reason"], message)
        if "reason" in kwargs:
            raise error_cls(kwargs["reason"], message)
        raise error_cls(message)
