# odin_reasoner/claims.py
# Strict structural validation of a claim set. No inference here — only schema.

from odin_reasoner.errors import require, ValidationError
from odin_reasoner.validation import validate_id, is_valid_sha256
from odin_reasoner import versions

_CLAIM_SET_FIELDS = ("odin_claim_set_version", "case_id", "claims")
_CLAIM_FIELDS = ("claim_id", "subject", "predicate", "object", "polarity",
                 "support")
_SUPPORT_FIELDS = ("support_id", "source_component", "source_id",
                   "source_sha256")


def _is_allowed_object(value) -> bool:
    # Allowed: string, boolean, integer, null. NO floats.
    # bool is a subclass of int, so check it explicitly and allow it.
    if value is None or isinstance(value, str) or isinstance(value, bool):
        return True
    if isinstance(value, int):  # excludes bool already handled, excludes float
        return True
    return False


def validate_claim_set(data) -> dict:
    """Validate a loaded claim-set dict. Raises ValidationError on any problem;
    returns the same dict on success."""
    require(isinstance(data, dict), "claim set must be a JSON object",
            ValidationError, reason="CLAIM_SET_NOT_OBJECT")
    keys = set(data.keys())
    expected = set(_CLAIM_SET_FIELDS)
    require(keys == expected,
            f"claim set fields mismatch: missing={sorted(expected - keys)}, "
            f"unknown={sorted(keys - expected)}",
            ValidationError, reason="CLAIM_SET_FIELDS")
    require(data["odin_claim_set_version"] == versions.ODIN_CLAIM_SET_VERSION,
            f"unexpected odin_claim_set_version "
            f"{data['odin_claim_set_version']!r}",
            ValidationError, reason="CLAIM_SET_VERSION")
    validate_id(data["case_id"], label="case_id")

    claims = data["claims"]
    require(isinstance(claims, list) and len(claims) > 0,
            "claims must be a non-empty list",
            ValidationError, reason="CLAIMS_EMPTY")

    seen_ids = set()
    for idx, claim in enumerate(claims):
        _validate_claim(claim, idx, seen_ids)
    return data


def _validate_claim(claim, idx, seen_ids):
    require(isinstance(claim, dict), f"claim #{idx} must be an object",
            ValidationError, reason="CLAIM_NOT_OBJECT")
    keys = set(claim.keys())
    expected = set(_CLAIM_FIELDS)
    require(keys == expected,
            f"claim #{idx} fields mismatch: missing={sorted(expected - keys)}, "
            f"unknown={sorted(keys - expected)}",
            ValidationError, reason="CLAIM_FIELDS")

    validate_id(claim["claim_id"], label="claim_id")
    require(claim["claim_id"] not in seen_ids,
            f"duplicate claim_id {claim['claim_id']!r}",
            ValidationError, reason="DUPLICATE_CLAIM_ID")
    seen_ids.add(claim["claim_id"])

    for f in ("subject", "predicate"):
        require(isinstance(claim[f], str) and claim[f] != "",
                f"claim {claim['claim_id']!r} field {f} must be a non-empty "
                f"string", ValidationError, reason="CLAIM_FIELD_TYPE")

    require(_is_allowed_object(claim["object"]),
            f"claim {claim['claim_id']!r} object must be string/bool/int/null "
            f"(no floats): {claim['object']!r}",
            ValidationError, reason="CLAIM_OBJECT_TYPE")

    require(claim["polarity"] in versions.POLARITIES,
            f"claim {claim['claim_id']!r} polarity must be one of "
            f"{sorted(versions.POLARITIES)}: {claim['polarity']!r}",
            ValidationError, reason="CLAIM_POLARITY")

    support = claim["support"]
    require(isinstance(support, list) and len(support) > 0,
            f"claim {claim['claim_id']!r} support must be a non-empty list",
            ValidationError, reason="SUPPORT_EMPTY")
    seen_support = set()
    for s_idx, item in enumerate(support):
        _validate_support(item, claim["claim_id"], s_idx, seen_support)


def _validate_support(item, claim_id, s_idx, seen_support):
    require(isinstance(item, dict),
            f"claim {claim_id!r} support #{s_idx} must be an object",
            ValidationError, reason="SUPPORT_NOT_OBJECT")
    keys = set(item.keys())
    expected = set(_SUPPORT_FIELDS)
    require(keys == expected,
            f"claim {claim_id!r} support #{s_idx} fields mismatch: "
            f"missing={sorted(expected - keys)}, "
            f"unknown={sorted(keys - expected)}",
            ValidationError, reason="SUPPORT_FIELDS")
    validate_id(item["support_id"], label="support_id")
    require(item["support_id"] not in seen_support,
            f"duplicate support_id {item['support_id']!r} in claim {claim_id!r}",
            ValidationError, reason="DUPLICATE_SUPPORT_ID")
    seen_support.add(item["support_id"])
    require(isinstance(item["source_component"], str)
            and item["source_component"] != "",
            f"support {item['support_id']!r} source_component must be a "
            f"non-empty string", ValidationError, reason="SUPPORT_FIELD_TYPE")
    validate_id(item["source_id"], label="source_id")
    require(is_valid_sha256(item["source_sha256"]),
            f"support {item['support_id']!r} source_sha256 is not a valid "
            f"sha256", ValidationError, reason="SUPPORT_SHA256")
