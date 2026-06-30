"""Status codes and error types for Atlas Release Gate v0.1."""

# --- Release gate statuses (the only allowed values) ---
RELEASE_GATE_PASSED = "RELEASE_GATE_PASSED"
FAILED_ATLAS_ROOT_MISSING = "FAILED_ATLAS_ROOT_MISSING"
FAILED_REQUIRED_FILE_MISSING = "FAILED_REQUIRED_FILE_MISSING"
FAILED_REGISTRY_VERIFY = "FAILED_REGISTRY_VERIFY"
FAILED_EXPORT_VERIFY = "FAILED_EXPORT_VERIFY"
FAILED_DOCUMENTATION_CHECK = "FAILED_DOCUMENTATION_CHECK"
FAILED_HONESTY_CHECK = "FAILED_HONESTY_CHECK"
FAILED_FORBIDDEN_FEATURE_CHECK = "FAILED_FORBIDDEN_FEATURE_CHECK"
FAILED_CHECKSUMS_INVALID = "FAILED_CHECKSUMS_INVALID"

ALL_GATE_STATUSES = frozenset({
    RELEASE_GATE_PASSED,
    FAILED_ATLAS_ROOT_MISSING,
    FAILED_REQUIRED_FILE_MISSING,
    FAILED_REGISTRY_VERIFY,
    FAILED_EXPORT_VERIFY,
    FAILED_DOCUMENTATION_CHECK,
    FAILED_HONESTY_CHECK,
    FAILED_FORBIDDEN_FEATURE_CHECK,
    FAILED_CHECKSUMS_INVALID,
})

# --- Component sub-statuses ---
REGISTRY_VERIFIED = "REGISTRY_VERIFIED"
REGISTRY_NOT_VERIFIED = "REGISTRY_NOT_VERIFIED"
EXPORT_VERIFIED = "EXPORT_VERIFIED"
EXPORT_NOT_VERIFIED = "EXPORT_NOT_VERIFIED"

# --- Step statuses ---
STEP_COMPLETED = "COMPLETED"
STEP_FAILED = "FAILED"
STEP_SKIPPED = "SKIPPED_AFTER_FAILURE"

ALL_STEP_STATUSES = frozenset({STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED})


class ReleaseGateError(Exception):
    """Raised for internal release-gate failures."""

    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code = code
        self.message = message


class VerifyError(Exception):
    """Raised when release-gate output verification fails."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message
