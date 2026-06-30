# aletheia_evidence/errors.py
# Typed errors and a require() guard (never a bare assert; -O strips asserts).


class AletheiaError(Exception):
    """Base class for all Aletheia evidence-bundle errors."""


class ValidationError(AletheiaError):
    """User input / source-file validation failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class BuildError(AletheiaError):
    """Bundle assembly failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class VerifyError(AletheiaError):
    """Bundle verification failed. Carries an evidence_status as the reason."""

    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def require(condition, message, error_cls=AletheiaError, **kwargs):
    """Raise error_cls(message) if condition is falsey. Never a bare assert."""
    if not condition:
        if "reason" in kwargs:
            raise error_cls(kwargs["reason"], message)
        if "status" in kwargs:
            raise error_cls(kwargs["status"], message)
        raise error_cls(message)
