# sentinel_core/errors.py
# All Sentinel exceptions. No bare assert is used for runtime invariants, so
# that correctness does not depend on assertions being enabled (python -O
# strips assert statements). Use require() instead.


class SentinelError(Exception):
    """Base class for all Sentinel errors."""


class InvariantViolation(SentinelError):
    """A declared invariant was violated."""


class SchemaError(SentinelError):
    """An action request failed schema validation."""


class PolicyError(SentinelError):
    """A path-policy evaluation failed in an unexpected way."""


class PersistenceFailure(SentinelError):
    """Receipt persistence failed; no state was committed."""


class SessionClosedError(SentinelError):
    """The session is closed; no further requests may be processed."""


class ManifestError(SentinelError):
    """Run manifest is missing, malformed or internally inconsistent."""


class ReceiptError(SentinelError):
    """Receipt construction or validation failed."""


class ChainVerificationError(SentinelError):
    """Receipt chain failed structural verification."""


class ReplayError(SentinelError):
    """Replay encountered an unrecoverable error."""


class ReplayIncompatible(SentinelError):
    """Run file uses a version the current implementation cannot replay."""


class PathTraversalError(SentinelError):
    """A supplied path would escape the permitted root."""


def require(condition: bool, message: str, exc_class=InvariantViolation) -> None:
    """Raise exc_class(message) if condition is False.

    This is the only invariant-enforcement primitive in the deterministic
    core. Unlike assert, it is never optimised away under python -O.
    """
    if not condition:
        raise exc_class(message)
