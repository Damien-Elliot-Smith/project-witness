# atlas_registry_lib/errors.py
# Typed errors and a require() guard (never a bare assert; -O strips asserts).


class AtlasError(Exception):
    """Base class for all Atlas Registry v0.1 errors."""


class RegistryError(AtlasError):
    """Registry verification failed. Carries the registry_status to report and a
    stable reason."""

    def __init__(self, registry_status, reason, message):
        self.registry_status = registry_status
        self.reason = reason
        super().__init__(message)


class ExportError(AtlasError):
    """Export / export-verify failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class BuildPathError(AtlasError):
    """A path problem (non-empty output dir, etc.)."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


def require(condition, message, error_cls=AtlasError, **kwargs):
    """Raise error_cls(message) if condition is falsey. Never a bare assert."""
    if not condition:
        if {"registry_status", "reason"} <= set(kwargs):
            raise error_cls(kwargs["registry_status"], kwargs["reason"], message)
        if "reason" in kwargs:
            raise error_cls(kwargs["reason"], message)
        raise error_cls(message)
