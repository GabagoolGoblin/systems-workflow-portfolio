# Implementation Readiness

> INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION

An offline, capability-first implementation workspace for turning ambiguous readiness work into explicit owners, evidence, gaps, review steps, and bounded acceptance decisions.

## Run in 60 seconds

Open `index.html` directly in a modern browser, or run:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8765/`. The application makes no automatic network request and stores state only in the current tab.

## Five-minute walkthrough

1. Use **Readiness board** to see implementation state and named owners.
2. Open **Gap triage**, select `GAP-07`, and advance its owner action.
3. Confirm that completing the action makes the gap review-ready rather than accepted.
4. Open **Acceptance desk**, run the seven visible prerequisites, and record the separate human acknowledgement.
5. Inspect **Audit trail** and create the user-triggered local JSON receipt.

## Implemented evidence

- Six interactive views and three repeatable query-string scenarios.
- Evidence states for accepted, qualified, conflicting, and missing material.
- Separate action-complete, review-ready, reviewer-accepted, and locally-ready states.
- Seven explicit acceptance checks with a final human gate.
- HTML escaping, keyboard navigation, reduced-motion treatment, and local-only export.
- Deterministic unit, privacy, and browser-interaction checks.

## Verify

```bash
make test
make scan
make smoke
```

The browser smoke uses Playwright only for verification. The runtime itself is plain HTML, CSS, and JavaScript.

## Limitations

The organization, framework, controls, records, people, dates, evidence, and decisions are invented. “Locally ready” means only that the seven demo prerequisites passed. It is not compliance, certification, legal advice, professional assessment, production readiness, or a depiction of any vendor product.

See [CLAIMS_AND_BOUNDARIES.md](CLAIMS_AND_BOUNDARIES.md) and [PROVENANCE.md](PROVENANCE.md). Owner-created material is governed by the root `LICENSE`; this project README grants no separate rights.
