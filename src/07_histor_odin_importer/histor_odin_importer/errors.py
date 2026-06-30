# histor_odin_importer/errors.py
# Typed errors and a require() guard (never a bare assert; -O strips asserts).


class HistorOdinError(Exception):
    """Base class for all importer errors."""


class ValidationError(HistorOdinError):
    """Input / ID validation failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class ComponentPathError(HistorOdinError):
    """A required frozen component root or the ODIN run is missing."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class OdinVerifyError(HistorOdinError):
    """Frozen ODIN verification of the run failed."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class OdinRunError(HistorOdinError):
    """The ODIN run files are missing/invalid or the reasoning status is not
    importable. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class VerifyError(HistorOdinError):
    """Imported-case verification failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


def require(condition, message, error_cls=HistorOdinError, **kwargs):
    """Raise error_cls(message) if condition is falsey. Never a bare assert."""
    if not condition:
        if "reason" in kwargs:
            raise error_cls(kwargs["reason"], message)
        raise error_cls(message)
