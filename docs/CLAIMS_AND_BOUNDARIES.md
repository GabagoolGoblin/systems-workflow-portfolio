# Claims and boundaries

## Repository-wide boundary

The repository supports claims that its author designed and implemented the checked-in demonstrations and deterministic tests. It supports discussion of system decomposition, validation, failure routing, human gates, local integrity evidence, and interface design visible in the code.

It does not support claims of paid production tenure, customer deployment, access to private systems, live traffic, production scale, regulatory compliance, accessibility or security certification, provider benchmarking, or action authority.

| Project | Evidence-backed capability | Boundary that must accompany it |
| --- | --- | --- |
| API Integration Contracts | Strict fixtures, HMAC/replay/idempotency ordering, virtual retry, quarantine, explicit review | Public demo secret is not secret; review token is not authentication; no network or persistence |
| Public Product Validation | Adverse-text parsing, barcode/check-digit validation, public identity comparison, conflict routing, human decision | Public records are not authoritative; every price is synthetic; no images or live writes |
| Human-in-the-Loop Control | Identifier cache, unknown hold, staged values, reread, mismatch stop, explicit approval | Clean-room invented records and local state only; no account, service, persistence, or production authority |
| AI Evaluation Release Gates | Precomputed A/B grading, blind labels, explicit reveal, hard vetoes, bounded outcomes | No provider, real prompt, inference, confidential holdout, promotion, or deployment |
| Implementation Readiness | Gap/evidence/action state, acceptance prerequisites, separate reviewer acknowledgment | Generic capability demo; not assessment, certification, vendor behavior, or production readiness |
| Customer Launch Readiness | Discovery decisions, readiness transitions, exception evidence, handoffs, acceptance | Generic invented program; no customer data, authorized go-live, deployment, or production action |
| Support Triage Workbench | Strict intake, deterministic routing, ambiguity/safety holds, redaction, approval, hash-linked audit | No ticketing adapter, sent response, customer workflow, or external persistence |
| Catalog Migration Validator | Strict mappings, quarantine, reconciliation, plan binding, atomic local apply | Narrow schemas only; no live adapter, identity system, retention, or remote transaction |
| Claim–Evidence Linter | Exact spans, typed assertions, deterministic policy states, rebuild verification | Validates a declared contract, not truth, independence, or entailment |
| Interface Contract Harness | Nine documented static HTML contracts and reproducible evidence | Not full WCAG conformance, browser behavior, legal certification, or assistive-technology testing |
| Catalog Lifecycle | Explicit verified/review/held states and local decision trace | Interface simulation only; digests are illustrative; state resets on refresh |
| Bulk Price Control | Write-free preview, staged digest, exact confirmation, atomic local write and rollback | Local synthetic files only; advisory locks do not control outside writers |

Project-level `CLAIMS_AND_BOUNDARIES.md` files are authoritative when a shorter portfolio summary could be read more broadly.
