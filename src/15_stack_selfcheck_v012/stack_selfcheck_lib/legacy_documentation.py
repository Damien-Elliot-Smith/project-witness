"""Legacy documentation compatibility for Stack Selfcheck v0.1.1.

Four early frozen components were sealed before the later documentation
convention. This module resolves an explicit, opt-in, recorded legacy
documentation allowance for exactly those component IDs, and refuses every
unsupported or false claim. No frozen component is modified; the allowance is
declared by the inventory via the `legacy_documentation_profile` field.

A documentation file may be omitted by a component ONLY when all of the
following hold:

  1. the component declares `legacy_documentation_profile`;
  2. the declared profile is exactly LEGACY_DOCUMENTATION_PROFILE;
  3. the component_id is one of the recognised legacy IDs; and
  4. the specific omitted file is in that component's allowance set.

Any other missing required documentation still fails, exactly as in v0.1.
"""

from . import versions
from .errors import CheckError, FAILED_DOCUMENTATION_BOUNDARY


def declared_profile(comp):
    """Return the raw declared legacy profile string, or None if absent."""
    return comp.get("legacy_documentation_profile")


def resolve_allowance(comp):
    """Validate any declared legacy documentation profile and return the set of
    documentation files this component may omit.

    Returns a frozenset of allowed-omission filenames. The set is empty when no
    legacy profile is declared (the normal case): such a component must carry
    the full documentation set.

    Raises CheckError(FAILED_DOCUMENTATION_BOUNDARY) when:
      * the declared profile string is not the recognised profile
        (a false legacy profile claim); or
      * the component_id is not a recognised legacy component
        (an unknown component claiming legacy status).
    """
    profile = declared_profile(comp)
    if profile is None:
        return frozenset()

    cid = comp["component_id"]

    # A declared profile must be exactly the recognised one. A different or
    # fabricated profile string is a false legacy-profile claim.
    if profile != versions.LEGACY_DOCUMENTATION_PROFILE:
        raise CheckError(
            FAILED_DOCUMENTATION_BOUNDARY,
            "%s declares unrecognised legacy_documentation_profile: %r"
            % (cid, profile))

    # Only the recognised legacy component IDs may claim the legacy profile.
    if cid not in versions.LEGACY_DOCUMENTATION_ALLOWANCES:
        raise CheckError(
            FAILED_DOCUMENTATION_BOUNDARY,
            "%s is not a recognised legacy component and may not claim the "
            "legacy documentation profile" % cid)

    return versions.LEGACY_DOCUMENTATION_ALLOWANCES[cid]


def allowance_record(comp, omitted):
    """Build the honest legacy-allowance record for the report.

    `omitted` is the sorted list of allowed documentation files this component
    actually omitted. The record is always emitted when a legacy profile is
    declared, so a declared-but-unused allowance is recorded truthfully with
    `legacy_documentation_allowance_used` set to False and an empty
    `missing_docs_allowed` list. Missing documentation is never silently
    passed.
    """
    return {
        "component_id": comp["component_id"],
        "legacy_documentation_profile": versions.LEGACY_DOCUMENTATION_PROFILE,
        "legacy_documentation_allowance_used": bool(omitted),
        "missing_docs_allowed": list(omitted),
        "reason": versions.LEGACY_DOCUMENTATION_REASON,
    }
