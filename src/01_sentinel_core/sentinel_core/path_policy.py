# sentinel_core/path_policy.py
# Deterministic path-safety policy for CREATE_DIRECTORY.
#
# This module decides whether a (allowed_root, target_path) pair is safe to act
# on. It performs read-only filesystem inspection (exists / is_dir / is_symlink)
# but never creates, deletes, moves, or overwrites anything. Execution lives in
# persistence.py. No shell is ever invoked here or anywhere in the core.
#
# The containment model:
#   - allowed_root is resolved to a real absolute path (symlinks resolved).
#   - target is joined onto allowed_root (or taken absolute) and resolved
#     LEXICALLY first to detect ".." escape, then the real parent is resolved
#     to detect symlink escape.
#   - The final target must sit strictly inside the resolved allowed_root.
#
# We deliberately separate "lexical escape" (PATH_TRAVERSAL) from "absolute
# outside root" and "symlink escape" so receipts name the precise failure.

import os

from sentinel_core.reason_codes import (
    BLOCK_EMPTY_PATH,
    BLOCK_ALLOWED_ROOT_MISSING,
    BLOCK_ALLOWED_ROOT_NOT_DIRECTORY,
    BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED,
    BLOCK_PATH_TRAVERSAL,
    BLOCK_OUTSIDE_ALLOWED_ROOT,
    BLOCK_PARENT_MISSING,
    BLOCK_PARENT_NOT_DIRECTORY,
    BLOCK_SYMLINK_RISK,
    BLOCK_TARGET_ALREADY_EXISTS,
)


class PolicyResult:
    """Outcome of a path-policy evaluation.

    ok=True means the request is safe to execute (or dry-run). When ok=False,
    reason_code names the specific block and detail carries diagnostic fields
    that are safe to record in a receipt (no secrets, just resolved paths).
    """

    __slots__ = ("ok", "reason_code", "detail", "resolved_target")

    def __init__(self, ok, reason_code=None, detail=None, resolved_target=None):
        self.ok = ok
        self.reason_code = reason_code
        self.detail = detail or {}
        self.resolved_target = resolved_target


def _within(base: str, candidate: str) -> bool:
    """True if candidate is base itself or strictly contained within base.

    Both arguments must already be normalised absolute paths. Uses os.sep
    boundary comparison to avoid the '/a/bc' vs '/a/b' prefix pitfall.
    """
    if candidate == base:
        return True
    return candidate.startswith(base + os.sep)


def evaluate_create_directory(target_path: str, allowed_root: str) -> PolicyResult:
    """Evaluate whether creating target_path under allowed_root is permitted.

    Read-only. Never mutates the filesystem. Returns a PolicyResult.
    Evaluation order is fixed and deterministic.
    """
    # 1. Empty target.
    if target_path == "":
        return PolicyResult(False, BLOCK_EMPTY_PATH, {"target_path": target_path})

    # 2. allowed_root must exist and be a directory. Resolve it fully (real
    #    path) so later containment checks compare against a canonical base.
    real_root = os.path.realpath(allowed_root)
    if not os.path.exists(real_root):
        return PolicyResult(False, BLOCK_ALLOWED_ROOT_MISSING,
                            {"allowed_root": allowed_root, "resolved_root": real_root})
    if not os.path.isdir(real_root):
        return PolicyResult(False, BLOCK_ALLOWED_ROOT_NOT_DIRECTORY,
                            {"allowed_root": allowed_root, "resolved_root": real_root})

    # 3. Build the candidate target path.
    #    - Absolute target: must already sit inside real_root, else blocked as
    #      an absolute-outside-root request (distinct from lexical traversal).
    #    - Relative target: joined onto real_root.
    if os.path.isabs(target_path):
        lexical_target = os.path.normpath(target_path)
        if not _within(real_root, lexical_target):
            return PolicyResult(False, BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED,
                                {"target_path": target_path, "resolved_root": real_root,
                                 "lexical_target": lexical_target})
    else:
        joined = os.path.join(real_root, target_path)
        lexical_target = os.path.normpath(joined)
        # 4. Lexical traversal check: after normpath, a relative target that
        #    escaped via ".." will no longer be inside real_root.
        if not _within(real_root, lexical_target):
            return PolicyResult(False, BLOCK_PATH_TRAVERSAL,
                                {"target_path": target_path, "resolved_root": real_root,
                                 "lexical_target": lexical_target})

    # 5. Resolve the PARENT via realpath to catch symlink escape. We resolve the
    #    parent (not the target) because the target itself must not yet exist.
    parent_lexical = os.path.dirname(lexical_target)
    real_parent = os.path.realpath(parent_lexical)

    # 6. Parent must exist and be a real directory.
    if not os.path.exists(real_parent):
        return PolicyResult(False, BLOCK_PARENT_MISSING,
                            {"parent": parent_lexical, "resolved_parent": real_parent})
    if not os.path.isdir(real_parent):
        return PolicyResult(False, BLOCK_PARENT_NOT_DIRECTORY,
                            {"parent": parent_lexical, "resolved_parent": real_parent})

    # 7. Symlink escape: the realpath-resolved parent must still be inside the
    #    realpath-resolved root. If a symlink in the chain pointed outside,
    #    real_parent now lies outside real_root and we fail closed.
    if not _within(real_root, real_parent):
        return PolicyResult(False, BLOCK_SYMLINK_RISK,
                            {"resolved_parent": real_parent, "resolved_root": real_root})

    # 8. Final resolved target = real_parent + basename. Confirm containment.
    basename = os.path.basename(lexical_target)
    resolved_target = os.path.join(real_parent, basename)
    if not _within(real_root, resolved_target):
        return PolicyResult(False, BLOCK_OUTSIDE_ALLOWED_ROOT,
                            {"resolved_target": resolved_target, "resolved_root": real_root})

    # 9. Target must not already exist (no overwrite). os.path.lexists catches
    #    dangling symlinks too, so a pre-placed symlink at the target name is
    #    treated as "already exists" rather than silently followed.
    if os.path.lexists(resolved_target):
        return PolicyResult(False, BLOCK_TARGET_ALREADY_EXISTS,
                            {"resolved_target": resolved_target})

    return PolicyResult(True, None,
                        {"resolved_root": real_root, "resolved_parent": real_parent,
                         "resolved_target": resolved_target},
                        resolved_target=resolved_target)


def evaluate_create_text_file(target_path: str, allowed_root: str,
                              allowed_path_prefix: str) -> PolicyResult:
    """Evaluate whether creating a TEXT FILE at target_path is permitted.

    Move 62. Path-leaf safety for a new file is IDENTICAL to a new directory
    (target must be absent, parent must exist and be a real directory, and the
    resolved target must sit strictly inside the manifest-authoritative
    allowed_root with no lexical traversal, no absolute escape, and no symlink
    escape). We therefore reuse evaluate_create_directory verbatim for those
    checks — it is read-only and creates nothing — then add the CREATE_TEXT_FILE
    prefix rule on top.

    allowed_path_prefix is interpreted RELATIVE to the manifest allowed_root
    (exactly like target_path), NOT as an absolute path. This is deliberate:
      * it keeps the request root-independent, so a saved run replays into a
        sandbox unchanged (the v1.1.0 property that removed request-carried
        absolute roots), and
      * it makes the prefix a NARROW-ONLY sub-area of the authoritative root —
        it can never widen the boundary.
    Use "." for "the whole allowed_root". An absolute prefix, or one that uses
    traversal to escape the root, fails closed as BLOCK_OUTSIDE_ALLOWED_ROOT.
    The resolved target must then sit inside the resolved prefix.
    """
    base = evaluate_create_directory(target_path, allowed_root)
    if not base.ok:
        return base

    real_root = os.path.realpath(allowed_root)
    resolved_target = base.resolved_target

    # An absolute prefix would name a root of its own; refuse it (fail closed)
    # rather than let a request widen or repoint the boundary.
    if os.path.isabs(allowed_path_prefix):
        return PolicyResult(False, BLOCK_OUTSIDE_ALLOWED_ROOT,
                            {"reason": "allowed_path_prefix must be relative to allowed_root",
                             "allowed_path_prefix": allowed_path_prefix, "resolved_root": real_root})

    prefix_lexical = os.path.normpath(os.path.join(real_root, allowed_path_prefix))
    if not _within(real_root, prefix_lexical):
        return PolicyResult(False, BLOCK_OUTSIDE_ALLOWED_ROOT,
                            {"reason": "allowed_path_prefix escapes allowed_root (traversal)",
                             "lexical_prefix": prefix_lexical, "resolved_root": real_root})

    real_prefix = os.path.realpath(prefix_lexical)
    # A symlinked prefix must still resolve inside the root.
    if not _within(real_root, real_prefix):
        return PolicyResult(False, BLOCK_OUTSIDE_ALLOWED_ROOT,
                            {"reason": "allowed_path_prefix escapes allowed_root (symlink)",
                             "resolved_prefix": real_prefix, "resolved_root": real_root})
    # The target must sit inside the declared (root-contained) prefix.
    if not _within(real_prefix, resolved_target):
        return PolicyResult(False, BLOCK_OUTSIDE_ALLOWED_ROOT,
                            {"reason": "target outside allowed_path_prefix",
                             "resolved_target": resolved_target, "resolved_prefix": real_prefix})

    detail = dict(base.detail)
    detail["resolved_prefix"] = real_prefix
    return PolicyResult(True, None, detail, resolved_target=resolved_target)
