# evidence_reasoning_demo/errors.py
# Typed errors and a require() guard (never a bare assert; -O strips asserts).


class DemoError(Exception):
    """Base class for all demo errors."""


class ValidationError(DemoError):
    """Input validation failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class ComponentPathError(DemoError):
    """A required frozen component root is missing."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


class StepError(DemoError):
    """A chain step (component invocation) failed. Carries the demo_status that
    should be reported and the failing step's component/operation."""

    def __init__(self, demo_status, message):
        self.demo_status = demo_status
        super().__init__(message)


class VerifyError(DemoError):
    """Demo output verification failed. Carries a stable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


def require(condition, message, error_cls=DemoError, **kwargs):
    """Raise error_cls(message) if condition is falsey. Never a bare assert."""
    if not condition:
        if "reason" in kwargs:
            raise error_cls(kwargs["reason"], message)
        if "demo_status" in kwargs:
            raise error_cls(kwargs["demo_status"], message)
        raise error_cls(message)
