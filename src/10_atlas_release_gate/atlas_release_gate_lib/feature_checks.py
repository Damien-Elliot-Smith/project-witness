"""Forbidden-feature and sentence scanning for Atlas release documentation.

A forbidden-feature violation requires an *affirmative support claim*: a sentence
that (a) is not an explicit negation / refusal / out-of-scope disclaimer, (b)
contains an affirmative-support cue (supports, integrates, connects, runs, uses,
provides, signs, anchors, ...), and (c) mentions a forbidden feature.

This distinguishes real claims ("Atlas integrates with Coordinator", "Atlas
supports signing") from honest registry / descriptive / limitation / refusal
text ("workflow types", "Coordinator and Companion are listed as components",
"does not run workflows", "refuses WRITE_FILE / DELETE_FILE / ...",
"ontology expansion is out of scope") which carries no affirmative cue.
"""

import re

# Plain negation markers, used both for the feature exemption and (separately)
# for the verifier's truth scan via _is_negated.
_NEGATION_MARKERS = (
    "does not", "do not", "doesn't", "don't", "did not", "didn't",
    "cannot", "can not", "can't", "will not", "won't",
    "is not", "are not", "was not", "were not",
    "not ", "n't", "without", "never", "no ",
    "read-only", "read only",
)

# Sentences that clearly disclaim, refuse, or place a feature out of scope are
# exempt from the affirmative-claim scan.
_EXEMPT_MARKERS = _NEGATION_MARKERS + (
    "refus",          # refuse / refuses / refused / refusal
    "forbidden",
    "out of scope", "out-of-scope",
    "out of roadmap", "out-of-roadmap",
    "not supported", "unsupported",
)

# Affirmative-support cues. A violation requires one of these to co-occur with a
# forbidden feature in a non-exempt sentence.
_AFFIRMATIVE_CUE = re.compile(
    r"\b("
    r"support|supports|supporting|"
    r"integrate|integrates|integrating|integration|"
    r"connect|connects|connecting|"
    r"run|runs|running|"
    r"use|uses|using|"
    r"provide|provides|providing|"
    r"enable|enables|enabling|"
    r"perform|performs|performing|"
    r"execute|executes|executing|"
    r"implement|implements|implementing|"
    r"offer|offers|offering|"
    r"sign|signs|"          # affirmative verb form (the noun "signing" is not a cue)
    r"anchor|anchors"       # affirmative verb form (the noun "anchoring" is not a cue)
    r")\b")

_FORBIDDEN_FEATURES = (
    ("coordinator_integration", re.compile(r"\bcoordinator\b")),
    ("companion_integration", re.compile(r"\bcompanion\b")),
    ("workflow_execution", re.compile(r"\bworkflows?\b")),
    ("natural_language", re.compile(r"natural[\s-]?language")),
    ("llm", re.compile(r"\bllm\b")),
    ("signing", re.compile(r"\bsign(?:s|ing|ed|ature|atures)?\b")),
    ("external_anchoring", re.compile(r"\banchor(?:s|ing|ed|age)?\b")),
    ("plugin_system", re.compile(r"\bplug-?ins?\b")),
    ("schema_migration", re.compile(r"schema\s+migration")),
    ("ontology_expansion", re.compile(r"ontolog(?:y|ies)\s+expansion")),
    ("write_file", re.compile(r"\bwrite_file\b")),
    ("delete_file", re.compile(r"\bdelete_file\b")),
    ("shell_command", re.compile(r"\bshell_command\b")),
    ("network_call", re.compile(r"\bnetwork_call\b")),
)

_SENTENCE_SPLIT = re.compile(r"[.\n;:!?]+")


def _sentences(text):
    norm = text.replace("\r", "\n")
    return [s.strip() for s in _SENTENCE_SPLIT.split(norm) if s.strip()]


def _is_negated(sentence_lower):
    """Negation test used by the verifier's truth scan."""
    return any(marker in sentence_lower for marker in _NEGATION_MARKERS)


def _is_exempt(sentence_lower):
    """A sentence is exempt if it disclaims, refuses, or scopes-out a feature."""
    return any(marker in sentence_lower for marker in _EXEMPT_MARKERS)


def scan_forbidden_features(text):
    """Return a list of (feature_name, sentence) affirmative-support violations.

    Only affirmative claims are reported; honest registry / descriptive /
    limitation / refusal text is allowed because it carries no affirmative cue
    (and explicit disclaimers are additionally exempt).
    """
    violations = []
    for sentence in _sentences(text):
        low = sentence.lower()
        if _is_exempt(low):
            continue
        if not _AFFIRMATIVE_CUE.search(low):
            continue
        for name, pattern in _FORBIDDEN_FEATURES:
            if pattern.search(low):
                violations.append((name, sentence))
    return violations
