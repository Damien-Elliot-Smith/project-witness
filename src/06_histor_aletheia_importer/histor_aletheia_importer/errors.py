# histor_aletheia_importer/errors.py
# Typed errors and a require() guard (never a bare assert; -O strips asserts).


class HistorImportError(Exception):
    """Base class for all importer errors."""


class ValidationError(HistorImportError):
    """Input / ID validation failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class ComponentPathError(HistorImportError):
    """A required frozen component root or the bundle is missing."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class AletheiaVerifyError(HistorImportError):
    """Frozen Aletheia verification of the bundle failed."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class ManifestError(HistorImportError):
    """The Aletheia manifest is missing/invalid or not VERIFIED_PRESENT."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class VerifyError(HistorImportError):
    """Imported-case verification failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


def require(condition, message, error_cls=HistorImportError, **kwargs):
    """Raise error_cls(message) if condition is falsey. Never a bare assert."""
    if not condition:
        if "reason" in kwargs:
            raise error_cls(kwargs["reason"], message)
        raise error_cls(message)
