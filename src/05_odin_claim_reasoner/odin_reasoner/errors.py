# odin_reasoner/errors.py
# Typed errors and a require() guard (never a bare assert; -O strips asserts).


class OdinError(Exception):
    """Base class for all ODIN errors."""


class ValidationError(OdinError):
    """Claim-set / input validation failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class ImportError_(OdinError):
    """Aletheia import failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class VerifyError(OdinError):
    """ODIN output verification failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


def require(condition, message, error_cls=OdinError, **kwargs):
    """Raise error_cls(message) if condition is falsey. Never a bare assert."""
    if not condition:
        if "reason" in kwargs:
            raise error_cls(kwargs["reason"], message)
        raise error_cls(message)
