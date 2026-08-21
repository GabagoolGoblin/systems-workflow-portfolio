# Project index

| Project | Capability | Entry point | Evidence | Explicit non-claim |
| --- | --- | --- | --- | --- |
| [API Integration Contracts](../projects/api-integration-contracts/README.md) | Request/webhook contracts, retry, quarantine, human gate | [Static demo](../projects/api-integration-contracts/index.html) | 48 tests; 12 browser checks | No live API, credential, or production integration |
| [Public Product Validation](../projects/public-product-validation/README.md) | Adverse input, barcode validation, public identity corroboration, human gate | [Static demo](../projects/public-product-validation/index.html) | 19 tests; 12 browser checks | Public identity is not authoritative; prices are synthetic; no writes |
| [Human-in-the-Loop Control](../projects/human-in-the-loop-control/README.md) | Cache resolution, unknown hold, reread, mismatch stop, explicit approval | [Browser preview](../projects/human-in-the-loop-control/preview/index.html) | 15 tests; 15 browser checks | Invented local state; no account, service, persistence, or authority |
| [AI Evaluation Release Gates](../projects/ai-evaluation-release-gates/README.md) | Exact grading, blind review, holdout, fail-closed gate | [Static demo](../projects/ai-evaluation-release-gates/index.html) | 60 tests; 19 browser checks | No inference, provider evaluation, or deployment authority |
| [Implementation Readiness](../projects/implementation-readiness/README.md) | Gap/action/evidence state and acceptance prerequisites | [Static demo](../projects/implementation-readiness/index.html) | 13 tests; 10 browser checks | No vendor behavior, assessment, certification, or production action |
| [Customer Launch Readiness](../projects/customer-launch-readiness/README.md) | Decisions, readiness, exception evidence, handoffs, acceptance | [Static demo](../projects/customer-launch-readiness/index.html) | 14 tests; 11 browser checks | No customer data, authorized go-live, or deployment |
| [Support Triage Workbench](../projects/support-triage-workbench/README.md) | Strict intake, deterministic routing, holds, redaction, approval, audit | CLI | 21 tests | No ticketing adapter, send action, or external persistence |
| [Catalog Migration Validator](../projects/catalog-migration-validator/README.md) | Mapping, quarantine, reconciliation, atomic local apply | CLI | 40 tests | No operational adapter or production migration |
| [Claim–Evidence Linter](../projects/claim-evidence-linter/README.md) | Typed evidence contracts and deterministic verdicts | CLI | 52 tests | Does not establish truth or semantic entailment |
| [Interface Contract Harness](../projects/interface-contract-harness/README.md) | Bounded HTML regression contracts | [Static report](../projects/interface-contract-harness/demo/index.html) | 41 tests | Not WCAG conformance or assistive-technology testing |
| [Catalog Lifecycle](../projects/catalog-lifecycle/README.md) | Operational state, held values, human review | [Static demo](../projects/catalog-lifecycle/index.html) | 12 tests | No integration or production automation |
| [Bulk Price Control](../projects/bulk-price-control/README.md) | Preview, stage, exact confirmation, verified local commit | CLI | 43 tests | No POS, database, or cloud connector |

Counts above describe this repository. Exact exported-tree evidence is produced by release verification; deterministic tests remain separate from browser checks.
