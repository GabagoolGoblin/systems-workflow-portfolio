# Systems Workflow Portfolio

I build small, inspectable systems that turn ambiguous operational work into explicit contracts, safe state transitions, human review points, and deterministic evidence.

Start with [API Integration Contracts](projects/api-integration-contracts/README.md), [Public Product Validation](projects/public-product-validation/README.md), and [Human-in-the-Loop Control](projects/human-in-the-loop-control/README.md). Static demos open directly in a browser; Python projects use the standard library. Use `make verify` for the complete repository check.

> INDEPENDENT PORTFOLIO DEMOS · SYNTHETIC WORKFLOWS · ATTRIBUTED PUBLIC PRODUCT IDENTITY · NO AFFILIATION · NO PRODUCTION ACTION

The workflows and operational decisions are synthetic. The sole data exception is the attributed, frozen Open Food Facts text identity snapshot in Public Product Validation; its pricing, operator inputs, and workflow remain synthetic.

These projects demonstrate implementation and testing choices. They do not represent employer systems, customer deployments, live integrations, certifications, provider benchmarks, or authority to change a production environment.

[Watch the project video guides](docs/VIDEO_GUIDES.md) for short overviews and focused walkthroughs.

## Featured work

### API Integration Contracts

A deterministic engine and six-screen workspace exercise strict API/webhook contracts, adverse inputs, bounded virtual retries, quarantine, an explicit human gate, and tamper-evident receipts. [Open the demo](projects/api-integration-contracts/index.html).

### Public Product Validation

An offline browser workflow parses adverse operator submissions, normalizes barcodes, validates check digits, compares text identity fields with a frozen Open Food Facts snapshot, and holds every synthetic price or uncertain match for a person. [Open the demo](projects/public-product-validation/index.html).

### Human-in-the-Loop Control

A clean-room Python core, native Tk lab, and code-native browser preview resolve cached identifiers, hold unknowns, stage values, reread results, fail closed on mismatch, and require explicit human approval. [Open the preview](projects/human-in-the-loop-control/preview/index.html).

## Browse all twelve projects

Open [the static portfolio landing](index.html) or use the [project index](docs/PROJECT_INDEX.md). The repository covers:

- integration reliability: API Integration Contracts;
- governance: AI Evaluation Release Gates and Claim–Evidence Linter;
- catalog/data controls: Catalog Lifecycle, Bulk Price Control, Catalog Migration Validator, and Public Product Validation;
- quality engineering: Interface Contract Harness; and
- operational control: Implementation Readiness, Customer Launch Readiness, Support Triage Workbench, and Human-in-the-Loop Control.

The repository declares 378 deterministic tests and 79 separately counted project browser checks. `make verify` confirms these counts against the exact tree.

## Run locally

Static projects have no build step. From the repository root:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8765/`. Static pages use only checked-in runtime assets and make no automatic network requests. Product attribution links are user-initiated.

Python examples require Python 3.11 or 3.12. The native human-in-the-loop screen additionally requires Python's Tk binding and a display. Project READMEs contain focused commands.

## Verify

```bash
make policy
make unit
make generated
make browser
make verify
```

Browser verification uses the separately locked tooling documented in [Dependencies](docs/DEPENDENCIES.md). Verification rebuilds committed examples only in temporary copies and must leave the repository unchanged.

## Evidence and boundaries

- [Claims and boundaries](docs/CLAIMS_AND_BOUNDARIES.md)
- [Data provenance](docs/DATA_PROVENANCE.md)
- [Dependencies](docs/DEPENDENCIES.md)
- [Release process](docs/RELEASE_PROCESS.md)
- [Security policy](SECURITY.md)

Distribution rights are defined only by the root `LICENSE` plus path-level third-party notices. The restrictive root `LICENSE` governs owner-created material, and third-party material keeps its own separate terms.
