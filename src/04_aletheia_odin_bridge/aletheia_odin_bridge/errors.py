# aletheia_odin_bridge/errors.py
# Typed errors and a require() guard (never a bare assert; -O strips asserts).


class BridgeError(Exception):
    """Base class for all bridge errors."""


class ComponentPathError(BridgeError):
    """A required frozen component path or the bundle is missing."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class AletheiaVerifyError(BridgeError):
    """Frozen Aletheia verification of the bundle failed."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class ManifestError(BridgeError):
    """The Aletheia manifest is missing/invalid or not VERIFIED_PRESENT."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class OdinValidateError(BridgeError):
    """Frozen ODIN validation of the generated claims failed."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class VerifyError(BridgeError):
    """Bridge output verification failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


def require(condition, message, error_cls=BridgeError, **kwargs):
    """Raise error_cls(message) if condition is falsey. Never a bare assert."""
    if not condition:
        if "reason" in kwargs:
            raise error_cls(kwargs["reason"], message)
        raise error_cls(message)
