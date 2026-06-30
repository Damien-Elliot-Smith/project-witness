# Known Limitations — One-Command Demo Script v0.1

- This script only runs and verifies the frozen Connected Demo.
- It does not prove evidence contents are true.
- It does not prove ODIN claims are true.
- It does not verify external reality.
- It does not sign or externally anchor outputs.
- Whole-folder fabrication remains possible under unkeyed hashes.

## Scope

The wrapper is a thin convenience layer over the frozen Connected Demo v0.1. It
adds no new verification of its own beyond checking that the Connected Demo ran,
verified, reached all seven required statuses, and reported a valid structural
truth boundary. Everything the Connected Demo does not prove, the wrapper does not
prove either. It checks structure, hashes, and statuses; it does not prove the
real world is true, does not prove a source is trustworthy, and does not prove
files are authentic beyond the hashes the demo checks. Because the hashes are
unkeyed, whole-folder fabrication remains possible: a fake but internally
consistent folder could still pass structural checks. Closing that gap needs
signing or external anchoring, which this wrapper does not add.
