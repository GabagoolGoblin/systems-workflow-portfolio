# Customer Launch Readiness

> INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION

First Value Launch Lab is an offline implementation-delivery workspace for translating discovery into owned milestones, handling UAT exceptions, preparing enablement and handoff, and recording a bounded human acceptance event.

## Run in 60 seconds

Open `index.html` in a modern browser, or run:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8765/`. The application makes no automatic network request, has no account, and keeps state only in memory.

## Five-minute walkthrough

1. Open **Discovery** and turn a synthetic note into a recorded decision.
2. Advance `RD-02` from attention to review-ready, then use the separate reviewer action.
3. Inspect `EX-17` under **UAT + exceptions** and keep reproduction evidence visible through review.
4. Record the missing receiving-owner acknowledgement under **Enablement**.
5. Run the nine acceptance checks, record the explicit human decision, and export the user-triggered local JSON audit.

## Implemented evidence

- Six interactive implementation views and three reproducible scenarios.
- Separate prepared, review-ready, accepted, and go-live-accepted states.
- Named owners, exit criteria, exception reproduction, training practice, and handoff evidence.
- Nine visible acceptance checks with a final human gate.
- HTML escaping, content-security policy, keyboard shortcuts, reduced motion, and in-memory-only state.
- Deterministic unit, privacy, and browser-interaction checks.

## Verify

```bash
make test
make scan
make browser
```

The runtime is plain HTML, CSS, and JavaScript. Playwright is verification-only.

## Limitations

Every customer, person, record, metric, date, artifact, and program event is invented. The demo depicts no vendor product or internal workflow. “Acceptance” changes only the synthetic browser session; it is not a deployment, customer instruction, production-readiness finding, or authorization to go live.

See [CLAIMS_AND_BOUNDARIES.md](CLAIMS_AND_BOUNDARIES.md) and [PROVENANCE.md](PROVENANCE.md). Owner-created material is governed by the common root `LICENSE`; this project README grants no separate rights.
