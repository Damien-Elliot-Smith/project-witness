# Licence Decision Needed

> **RESOLVED (Move 54, 2026-06-29):** the licence decision has been made. This
> repository is released under the **Apache License 2.0** — see the top-level
> `LICENSE` file. The notes below are retained for history only.

---

This package does **not** yet carry a licence. That is intentional, not an
oversight.

## Why there is no LICENSE file

With no licence, default copyright applies: others have no granted rights to use,
copy, modify, or redistribute this code. For a private handoff to a named
reviewer that is usually fine. For any **public release** (e.g. publishing to a
public repository), a licence must be chosen first. Releasing publicly with no
licence leaves recipients without clear permission and leaves you without clear
terms.

## This is not legal advice

The notes below are practical orientation only, not legal advice. For anything
with real stakes, confirm with a qualified person.

## Options to consider

- **MIT** — short, permissive, easy. Allows broad reuse with attribution. Does
  **not** include an explicit patent grant.
- **Apache 2.0** — permissive, with an explicit patent grant and attribution/NOTICE
  requirements. Often preferred when patent protection or clear contribution terms
  matter. (Related work in this body of projects has previously leaned toward
  Apache 2.0 for exactly these reasons — worth confirming whether the same intent
  applies here.)
- **Proprietary / all-rights-reserved** — keep it closed; share only under direct
  agreement. Appropriate if you are not ready to permit redistribution.

## What to do

1. Decide whether this package is intended for permissive public release at all.
2. If yes, pick a licence (MIT vs Apache 2.0 is the main fork above).
3. Add the corresponding `LICENSE` file at the top level, and a one-line licence
   note to `START_HERE.md` and `HANDOFF_NOTES.md`.
4. If contributions from others are expected, also decide on contribution terms.

No `LICENSE` was added automatically because permissive public-release intent has
not been confirmed for this specific package, and the MIT-vs-Apache-2.0 choice has
real consequences (notably the patent grant) that should be a deliberate decision.


Status exact marker: Roadmap complete through Move 60; Moves 61-70 remain future work.
