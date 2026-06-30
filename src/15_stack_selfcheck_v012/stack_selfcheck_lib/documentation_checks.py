"""Documentation boundary checks and affirmative out-of-scope claim refusal.

v0.1.2 — truth-boundary phrase-model compatibility repair.

The boundary-presence check (does the documentation honestly state its
boundaries?) and the affirmative-claim refusal both operate on deterministically
normalized text: markdown emphasis is stripped, whitespace collapsed, and text
lowercased. No LLM, no semantic model.

A required boundary is satisfied by a *negated* sentence that mentions the
concept's tokens (so honest disclaimers phrased many different ways are all
accepted), or by an explicit structural/read-only marker. The truth boundary is
additionally satisfied *vacuously* when the documentation contains no
truth-domain token at all: a component that never claims to prove truth does not
need a truth-boundary disclaimer. Affirmative truth-like claims and affirmative
out-of-scope feature claims are still refused.
"""

import os
import re

from . import versions
from .errors import CheckError, FAILED_DOCUMENTATION_BOUNDARY, FAILED_TRUTH_CLAIM

# Affirmative truth-like claims (refused unless the sentence is negated). The
# truth/authentic/trusted assertions are anchored to a truth-DOMAIN subject so a
# benign technical statement such as "the ok flag is true" is not a violation,
# while "evidence contents are true" or "files are authentic" still are.
_TRUTH_SUBJECT = (r"(?:evidence|content|contents|claim|claims|statement|statements|"
                  r"file|files|source|sources|record|records|case|stack|registry|"
                  r"reasoning|result|results|output|outputs|finding|findings|"
                  r"document|documents|origin|data)")
_TRUTH_PATTERNS = (
    re.compile(_TRUTH_SUBJECT + r"[^.?!]{0,40}?\b(?:is|are|was|were)\s+true\b"),
    re.compile(r"\b(?:is|are|was|were)\s+true\b[^.?!]{0,12}?\b" + _TRUTH_SUBJECT),
    re.compile(_TRUTH_SUBJECT + r"[^.?!]{0,40}?\b(?:is|are|was|were)\s+authentic\b"),
    re.compile(_TRUTH_SUBJECT + r"[^.?!]{0,40}?\b(?:is|are|was|were)\s+trusted\b"),
    re.compile(r"\bproves?\s+reality\b"),
    re.compile(r"\bproves?\s+truth\b"),
    re.compile(r"\bproves?\s+(?:that\s+)?(?:the\s+)?" + _TRUTH_SUBJECT
               + r"[^.?!]{0,40}?\b(?:is|are)\s+true\b"),
    re.compile(r"\bevidence\s+is\s+true\b"),
    re.compile(r"\bclaims?\s+are\s+true\b"),
    re.compile(r"\bproves?\s+the\s+stack\s+works\b"),
    re.compile(r"\bauthenticates?\s+(?:the\s+)?(?:origin|source|file|evidence)\b"),
)
# Affirmative out-of-scope feature claims (only tripped when NOT negated). LLM
# and natural-language claims require an affirmative capability verb, consistent
# with the other feature patterns, so a bare "LLM reasoning" bullet under an
# "Out of scope" heading is not a violation while "uses an LLM" is.
_FEATURE_PATTERNS = (
    re.compile(r"\bsupports?\s+signing\b"),
    re.compile(r"\bsigns?\s+(?:the\s+)?outputs?\b"),
    re.compile(r"\bprovides?\s+signing\b"),
    re.compile(r"\bsupports?\s+(?:external\s+)?anchoring\b"),
    re.compile(r"\bexternally\s+anchors?\b"),
    re.compile(r"\b(?:uses?|using|performs?|runs?|does|applies|provides?|"
               r"powered\s+by|backed\s+by|relies?\s+on)\s+(?:an?\s+|any\s+)?"
               r"(?:llm|large\s+language\s+model)\b"),
    re.compile(r"\bllm[\s-]based\b"),
    re.compile(r"\b(?:uses?|using|performs?|provides?)\s+(?:an?\s+)?"
               r"natural[\s-]language\s+(?:interpretation|reasoning|processing)\b"),
    re.compile(r"\bpowered\s+by\s+natural[\s-]language\b"),
    re.compile(r"\bprovides?\s+a\s+gui\b"),
    re.compile(r"\bhas\s+a\s+gui\b"),
    re.compile(r"\bgui\s+is\s+supported\b"),
    re.compile(r"\bsupports?\s+concurrency\b"),
    re.compile(r"\bsupports?\s+queues?\b"),
    re.compile(r"\buses?\s+a\s+queue\b"),
)

# Negation / refusal markers. A sentence containing any of these is treated as a
# limitation, not an affirmative claim. Markdown emphasis is stripped first, so
# "does **not** prove truth" normalizes to "does not prove truth" and matches.
_NEGATION = ("does not", "do not", "not ", "no ", "never", "without", "n't",
             "cannot", "can't", "neither", "nor ", "refuses", "refuse ",
             "rejects", "reject ", "makes no", "make no", "nothing", "none ",
             "out of scope", "out-of-scope", "no claim", "makes no claim")

_SENT = re.compile(r"[.!?]+")

# Deterministic markdown-emphasis stripping: remove emphasis/heading/quote/
# code/list markers; turn underscores (emphasis or snake_case) into spaces.
# Newlines are flattened to spaces BEFORE sentence splitting because these docs
# are hard-wrapped at ~80 columns and use "what it does not do:" headings over
# bulleted lists — a raw newline split would separate a negation from the token
# it governs and turn an honest disclaimer into a false affirmative. Sentence
# enders (. ! ?) are preserved so real sentences still split.
_STRIP = str.maketrans({"*": "", "`": "", "#": "", ">": "", "_": " ",
                        "~": "", "[": " ", "]": " ", "(": " ", ")": " ",
                        "\n": " ", "\r": " ", "\t": " ", "|": " ",
                        ":": " ", ";": " "})


def _strip_markdown(text):
    return text.translate(_STRIP).lower()


def _sentences(text):
    out = []
    for raw in _SENT.split(_strip_markdown(text)):
        sentence = " ".join(raw.split())
        if sentence:
            out.append(sentence)
    return out


def _read_doc(root, name):
    path = os.path.join(root, name)
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _docs_text(comp):
    root = comp["root_path"]
    return (_read_doc(root, "README.md") + "\n"
            + _read_doc(root, "KNOWN_LIMITATIONS.md"))


# ---------------------------------------------------------------------------
# Boundary concepts. Each is a deterministic token set. A boundary is "present"
# when a negated sentence mentions one of its tokens (an honest disclaimer), or
# an explicit marker is present. The truth boundary also accepts the vacuous
# case (no truth-domain token anywhere).
# ---------------------------------------------------------------------------
_TRUTH_TOKENS = ("prove truth", "proves truth", "prove reality", "proves reality",
                 "prove the stack works", "true", "authentic", "trusted",
                 "external reality", "authenticate")
_TRUTH_MARKERS = ("structural verification only", "structural reasoning",
                  "records structure", "records hashes", "records statuses",
                  "structure, hashes", "hashes, and statuses",
                  "structural integrity only")

_WORKFLOW_TOKENS = ("run workflow", "runs workflow", "run workflows",
                    "running workflows", "execute workflow", "executes workflow",
                    "execute the workflow", "run a workflow", "workflow")
_EVIDENCE_TOKENS = ("copy evidence", "copies evidence", "copy the evidence",
                    "copying evidence", "evidence contents", "evidence file contents")
_ATLAS_NEG_TOKENS = ("modify atlas", "modifies atlas", "add atlas", "adds atlas",
                     "add terms to atlas", "add new atlas", "connect atlas",
                     "connects atlas", "modify the registry", "modifies the registry",
                     "add new registry", "add registry terms", "write to atlas",
                     "writes to atlas")
_ATLAS_MARKERS = ("atlas is read-only", "atlas read-only", "read-only registry",
                  "registry is read-only", "read-only atlas",
                  "atlas is read only", "read only registry")


def _is_negated(sentence):
    return any(marker in sentence for marker in _NEGATION)


def _has_negated_token(sentences, tokens):
    for sentence in sentences:
        if any(token in sentence for token in tokens) and _is_negated(sentence):
            return True
    return False


def _joined(sentences):
    return " ".join(sentences)


def _truth_boundary_present(sentences):
    joined = _joined(sentences)
    if _has_negated_token(sentences, _TRUTH_TOKENS):
        return True
    if any(marker in joined for marker in _TRUTH_MARKERS):
        return True
    # Vacuous: the documentation makes no truth-domain claim at all, so there is
    # nothing to disclaim. (An affirmative truth claim would instead be refused
    # by check_truth_boundary below.)
    if not any(token in joined for token in _TRUTH_TOKENS):
        return True
    return False


def _atlas_boundary_present(sentences):
    joined = _joined(sentences)
    if any(marker in joined for marker in _ATLAS_MARKERS):
        return True
    if _has_negated_token(sentences, _ATLAS_NEG_TOKENS):
        return True
    return False


def check_boundaries(comp):
    """Confirm required boundary statements are present, accepting any honest
    deterministic-equivalent wording."""
    sentences = _sentences(_docs_text(comp))
    cid = comp["component_id"]

    if not _truth_boundary_present(sentences):
        raise CheckError(FAILED_DOCUMENTATION_BOUNDARY,
                         "%s missing truth boundary statement" % cid)
    if comp.get("read_only") and not _has_negated_token(sentences, _WORKFLOW_TOKENS):
        raise CheckError(FAILED_DOCUMENTATION_BOUNDARY,
                         "%s missing boundary: does not run workflows" % cid)
    if comp.get("evidence_component") and not _has_negated_token(sentences, _EVIDENCE_TOKENS):
        raise CheckError(FAILED_DOCUMENTATION_BOUNDARY,
                         "%s missing boundary: does not copy evidence contents" % cid)
    if comp.get("atlas_connected") and not _atlas_boundary_present(sentences):
        raise CheckError(FAILED_DOCUMENTATION_BOUNDARY,
                         "%s missing boundary: atlas is read-only" % cid)


def check_truth_boundary(comp):
    """Refuse affirmative truth-like claims and affirmative out-of-scope feature
    claims. Sentences containing a negation/refusal marker are limitations and
    are skipped. Markdown emphasis is stripped first so negated statements such
    as 'does **not** prove evidence contents are true' are correctly skipped."""
    cid = comp["component_id"]
    for sentence in _sentences(_docs_text(comp)):
        if _is_negated(sentence):
            continue
        for pat in _TRUTH_PATTERNS:
            if pat.search(sentence):
                raise CheckError(FAILED_TRUTH_CLAIM,
                                 "%s truth-like claim: %r" % (cid, sentence))
        for pat in _FEATURE_PATTERNS:
            if pat.search(sentence):
                raise CheckError(FAILED_DOCUMENTATION_BOUNDARY,
                                 "%s out-of-scope claim: %r" % (cid, sentence))
