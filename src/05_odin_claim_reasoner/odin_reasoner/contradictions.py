# odin_reasoner/contradictions.py
# Direct, deterministic contradiction detection for ODIN v0.1.
#
# Two claims with the SAME subject and SAME predicate contradict if EITHER:
#   (a) they have different objects                         -> DIFFERENT_OBJECT
#   (b) same object but opposite polarity                   -> OPPOSITE_POLARITY
#
# No other inference. Detection is order-independent and deterministic: claims are
# grouped by (subject, predicate), and within each group every unordered pair is
# checked in stable claim order, emitting at most one contradiction per pair with
# a fixed rule precedence (different-object before opposite-polarity).

from odin_reasoner import versions


def _object_key(value):
    # A hashable, type-distinguishing key so that 1 and True (and 0 and False)
    # are NOT treated as equal objects. JSON has distinct bool/int here.
    return (type(value).__name__, value)


def find_contradictions(claims):
    """Return a deterministic list of contradiction dicts:
        {"claim_ids": [id_a, id_b], "rule": <RULE_*>}
    `claims` is the validated list of claim dicts (original order preserved)."""
    # Stable grouping by (subject, predicate), keeping original indices.
    groups = {}
    for i, c in enumerate(claims):
        groups.setdefault((c["subject"], c["predicate"]), []).append(i)

    contradictions = []
    # Iterate groups in first-appearance order for determinism.
    for key in sorted(groups, key=lambda k: groups[k][0]):
        idxs = groups[key]
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                ca, cb = claims[idxs[a]], claims[idxs[b]]
                rule = _pair_rule(ca, cb)
                if rule is not None:
                    contradictions.append({
                        "claim_ids": [ca["claim_id"], cb["claim_id"]],
                        "rule": rule,
                    })
    return contradictions


def _pair_rule(ca, cb):
    same_object = _object_key(ca["object"]) == _object_key(cb["object"])
    if not same_object:
        return versions.RULE_DIFFERENT_OBJECT
    if ca["polarity"] != cb["polarity"]:
        return versions.RULE_OPPOSITE_POLARITY
    return None
