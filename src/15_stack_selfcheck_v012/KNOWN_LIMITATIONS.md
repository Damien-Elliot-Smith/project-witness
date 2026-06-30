# Known Limitations — Stack Selfcheck v0.1.2

- one stack inventory only
- optional one Stack Verifier output only
- does not run workflows
- does not call frozen components during the freeze gate
- does not copy evidence contents
- does not prove truth
- does not verify external reality
- does not sign
- does not externally anchor
- does not merge cases
- does not provide search
- does not provide GUI
- does not use LLM
- does not prove the stack works in the real world
- legacy documentation allowances are recorded and never silently passed
- the truth-boundary phrase model is deterministic and does not weaken truth-claim refusal

## Scope

Stack Selfcheck v0.1.2 reads one stack inventory file and, optionally, one Stack
Verifier v0.1 output. It writes one stack selfcheck report, one selfcheck steps
file, and one selfcheck checksum file. It checks inventory schema and required
components, component roots and expected project files, zip sidecars where
provided, documentation boundary statements, the truth boundary, and an optional
Stack Verifier output. It records labels and component metadata only; it never
stores absolute paths in the report and never copies evidence contents.

## Truth-boundary phrase model

The documentation truth-boundary check is deterministic: text is normalized
(markdown emphasis stripped, line-wrapping and list structure flattened,
whitespace collapsed, lowercased), with no LLM and no semantic model. A
truth-boundary statement is recognised by a negated sentence mentioning a
truth-domain token, an explicit structural-only marker, or the absence of any
truth-domain claim. This accepts the honest wording actually present in the
frozen documentation and is robust to markdown emphasis, while still refusing
affirmative truth-like claims and affirmative out-of-scope feature claims. The
phrase model does not relax the refusal of affirmative truth claims; it only
recognises honest disclaimers that the v0.1.1 literal-phrase model missed.

## Legacy documentation allowances

The documentation-boundary check accepts explicitly-declared legacy documentation
allowances for exactly four early frozen components
(`sentinel_core_v022`, `histor_lite_v012`, `case_bundle_v011`,
`atlas_red_blue_pack_v01`), and only for the specific documentation files each
profile permits. These allowances are unchanged from v0.1.1 and are not broadened.
They do not relax the truth boundary, the out-of-scope feature refusal, the
absolute-path refusal, or the Stack Verifier output cross-check.

## Honesty boundary

The report records release-hygiene and inventory facts only. It does not, and the
verifier rejects any attempt to, claim that evidence is true, that ODIN claims are
true, that files are authentic, that sources are trusted, or that the case or
stack proves reality. Stack Selfcheck does not prove the stack works in the real
world; it only confirms that the frozen inventory is present, version-consistent,
checksum-valid where sidecars are provided, and truth-bounded.
