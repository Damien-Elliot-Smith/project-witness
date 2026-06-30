# Known limitations — ODIN Claim Reasoner v0.1

ODIN Claim Reasoner v0.1 is a deliberately narrow prototype. The following
limitations are explicit and accepted for this milestone.

## L1 — Structured claims only
ODIN reasons only over already-structured claims with the fixed schema. It does not
build claims from anything except (optionally) an Aletheia integrity manifest.

## L2 — Direct contradiction detection only
The only inference is direct structural contradiction: same subject + predicate
with a different object, or same object with opposite polarity. Nothing else.

## L3 — No natural language
No natural-language parsing, generation, or interpretation of any kind.

## L4 — No LLM
No language model is involved anywhere.

## L5 — No ontology expansion
No subclass/equivalence/transitive reasoning, no schema inference, no entailment
beyond the two direct contradiction rules.

## L6 — No probabilistic reasoning
Claims are treated as exact structured records. No confidence scores, weights, or
probabilities.

## L7 — No action gating
ODIN does not gate or trigger any action. It only reports.

## L8 — No signing
Nothing in the output is cryptographically signed.

## L9 — No external anchoring
No hash is anchored to an external log, timestamp authority, or notary.

## L10 — Does not prove truth
A `CONSISTENT` result means the claim set is structurally consistent;
`CONTRADICTION_DETECTED` means a direct structural contradiction exists. Neither
asserts that any claim's content is true, accurate, or real. ODIN proves structure,
not truth.

## L11 — Not a full theorem prover
No general logical inference, no quantifiers, no rule chaining. This is a mini
deterministic reasoner, not full ODIN.

## L12 — Not connected to the full workflow yet
ODIN v0.1 stands alone. It is not wired into Companion, Coordinator, Histor, or
Case Bundle. Integrity is hash-based within the output folder only, and (like the
rest of the stack) whole-output fabrication remains possible without signing.

## L13 — Not production reasoning or evidence custody
This is a prototype. It must not be relied on as a production reasoning engine or
as a chain-of-custody / evidence-truth system.
