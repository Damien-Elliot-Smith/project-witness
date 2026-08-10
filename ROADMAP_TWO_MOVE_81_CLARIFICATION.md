# Roadmap Two — Move 81 Clarification

This is an additive documentation-truth record for Move 81. It records the
authoritative roadmap objective and the current adopted state without
modifying any inherited status document. It does not alter the inherited
roadmap or current-state documents; those remain preserved historical
snapshots.

## Original Roadmap Two wording (verbatim)

> "81 — Full verifier verdict output — Upgrade the Rust verifier to
> produce PASS, FAIL, and INCONCLUSIVE with structured reason codes
> aligned to Witness language."

Source: `Project_Witness_Part_Two_Roadmap_Steps_71_to_130.pdf`, Page 2,
Phase One / Block A (Steps 71–85, "Rust Verification Spine").

## Owner operational clarification

Move 81 upgrades the verification output CONTRACT so that it can represent
the complete PASS / FAIL / INCONCLUSIVE vocabulary using deterministic
structured reason codes. It does not authorise a verifier operation to
emit a verdict that its present capability cannot honestly establish.

Therefore:

- the structured contract supports PASS, FAIL, and INCONCLUSIVE;
- the Python reference lane may emit its currently reachable PASS or FAIL
  outcomes;
- Rust bundle verification retains its adopted honesty boundary;
- Rust `verify` does not gain a reachable PASS path merely to satisfy the
  wording;
- a currently healthy Rust bundle remains INCONCLUSIVE (exit 3);
- archive-safety success remains INCONCLUSIVE (exit 3);
- FAIL remains exit 1;
- usage remains exit 2 and is not a verification verdict;
- the two adopted Python/Rust divergences remain visible.

"Produce PASS" is clarified to mean that PASS is a defined and supported
verdict in the structured output contract, and may be emitted only by an
operation that has an adopted evidential basis for PASS. No synthetic,
self-test, schema-demo, or scoped PASS was created to claim literal
roadmap completion.

## No Rust PASS capability was introduced

Move 81 v01 is an additive structured-verdict output boundary (an adapter)
around the adopted verification lanes. It does not modify `rust/` or the
frozen Python source, does not change any default command output, and does
not add verification capability. The adopted Rust honesty property — no
reachable PASS, exit 0 unreachable in `verify` — is unchanged. If the
adapter ever observes a Rust PASS, it is reported as an impossible
verdict/exit pairing (a measurement error), never as a verdict.

## Adopted baseline this move builds on

- Adopted Move 80 artifact: `project-witness-MOVE_80_candidate_v07.zip`
- Move 80 v07 SHA-256:
  `8c08342efae3b17458e33c6ae54ff42bf79d6759170b46cfbf32ef218d0dd2ad`
- Move 80 adoption transcript: `MOVE_80_V07_TERMUX_GATE.txt`
- Move 80 transcript SHA-256:
  `5d7b285e5b9969294f34747af96d6a6a2fd153614658de4769e5398a2658d11e`

## Why inherited status documents remain unchanged

The inherited status documents — `MOVE_INDEX.md`,
`CURRENT_RELEASE_STATE.md`, and the repeated status marker embedded across
several inherited files — still describe an earlier point in the roadmap
(they name Move 79 as the then-current candidate and predate the adoption
of Move 80). Those documents are checker-guarded parts of the adopted
Move 79 and Move 80 baselines. To preserve adopted baseline immutability
and keep the adopted source/release checks passing byte-for-byte, they are
left unchanged here.

Those older inherited status documents are therefore preserved historical
snapshots, not the current truth authority. This file records the current
truth: Moves 71–80 are adopted, and Move 81 (this clarification and its
structured-verdict output boundary) is the current work, additive and
honesty-preserving as described above.
