# aletheia_evidence/versions.py
# Version constants and the honest status vocabulary for Aletheia Evidence
# Bundle v0.1. This component proves preservation/hash integrity only — never
# truth of file contents.

ALETHEIA_EVIDENCE_BUNDLE_VERSION = "0.1.0"

# v0.1 size limit for a single evidence file.
MAX_EVIDENCE_BYTES = 10 * 1024 * 1024  # 10 MB

# Fixed bundle layout.
EVIDENCE_DIRNAME = "evidence"
BUNDLED_FILE_NAME = "evidence_001.bin"  # the copied evidence is always this name
MANIFEST_NAME = "evidence_manifest.json"
CHECKSUMS_NAME = "evidence_checksums.txt"

# bundle_status: did we successfully assemble a bundle?
BUNDLE_STATUS_BUNDLED = "BUNDLED"

# evidence_status: the honest integrity verdict. None of these mean "true".
EVIDENCE_VERIFIED_PRESENT = "VERIFIED_PRESENT"
EVIDENCE_FAILED_MISSING_FILE = "FAILED_MISSING_FILE"
EVIDENCE_FAILED_HASH_MISMATCH = "FAILED_HASH_MISMATCH"
EVIDENCE_FAILED_MANIFEST_INVALID = "FAILED_MANIFEST_INVALID"
EVIDENCE_FAILED_CHECKSUMS_INVALID = "FAILED_CHECKSUMS_INVALID"
EVIDENCE_FAILED_NON_CANONICAL_MANIFEST = "FAILED_NON_CANONICAL_MANIFEST"

EVIDENCE_FAILURE_STATUSES = frozenset({
    EVIDENCE_FAILED_MISSING_FILE,
    EVIDENCE_FAILED_HASH_MISMATCH,
    EVIDENCE_FAILED_MANIFEST_INVALID,
    EVIDENCE_FAILED_CHECKSUMS_INVALID,
    EVIDENCE_FAILED_NON_CANONICAL_MANIFEST,
})

KNOWN_LIMITATIONS = [
    "This bundle proves file preservation and hash consistency only.",
    "It does not prove the file contents are true.",
    "It does not sign or externally anchor the bundle.",
    "Whole-bundle fabrication remains possible without signing.",
]
