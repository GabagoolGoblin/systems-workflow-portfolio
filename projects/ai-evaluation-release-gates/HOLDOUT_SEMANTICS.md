# Holdout semantics

## Exact meaning

In this demonstration, a holdout is excluded from development scoring/selection and hash-bound until an explicit local reveal/evaluation step. It is not secret, encrypted, access-controlled, or cryptographically confidential. Anyone with the static repository files can inspect it.

## Browser split

`data/demo_snapshot.js` contains eight full development cases; four holdout IDs, slices, veto flags, and per-case hashes; the expected digest of the complete reveal payload; and policy/rubric boundaries. It excludes holdout task briefs, outputs, grader details, and candidate bindings.

`data/holdout_snapshot.js` contains four full invented holdout cases, candidate bindings for all twelve cases, label-keyed reference adjudications, and the deterministic reference `HOLD` receipt.

The HTML does not preload the second file. An explicit action loads it, canonicalizes the full payload, recomputes SHA-256, checks the base binding/count/case hashes, and only then exposes the details. A changed detail or binding with an old declared hash fails closed. Concurrent dependent actions join one reveal promise.

## What hashes establish

The hashes establish content consistency between the deterministic build and the local reveal. They do not establish origin, confidentiality, reviewer identity, business approval, fitness for production, or authority to deploy.
