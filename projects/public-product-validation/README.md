# Public Product Validation

> INDEPENDENT PORTFOLIO DEMO · PUBLIC PRODUCT IDENTITY DATA · SYNTHETIC PRICING, OPERATOR INPUTS, AND WORKFLOW · NO AFFILIATION · NO PRODUCTION ACTION

An offline catalog-operations demo that accepts adverse operator-shaped text, normalizes UPC/EAN/GTIN candidates, checks GS1 mod-10 digits, corroborates identity against a frozen public snapshot, isolates uncertainty, and requires a person before any in-memory staged decision.

## Run in 60 seconds

Open `index.html` in a modern browser, or run:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8765/`. The application makes no automatic network request. Source links open only after a deliberate click.

## Five-minute walkthrough

1. Parse the nine hostile and malformed synthetic submissions under **Intake & parse**.
2. Inspect leading-zero normalization, invalid check digits, duplicate-price conflicts, and unknown/not-found states in **Validation queue**.
3. Compare operator fields with frozen public identity facts under **Human decision**.
4. Confirm blocked records cannot be staged and every decision remains in browser memory.
5. Review retrieval times, source URLs, data licenses, and the zero-write boundary in **Evidence ledger**.

## Data boundary

Five found records and one not-found control were captured from the Open Food Facts API v3 on 2026-08-20. Only text identity fields are bundled; no product image is included. The public distribution copy is not the exact raw capture: it removes only one locally added request-contact field while leaving every other JSON field and all six retained response records unchanged. The machine-verifiable receipt is `data/DATA_REDACTION_RECEIPT.json`.

**Synthetic price — not sourced from Open Food Facts.** Every price, site/menu, operator note, run event, decision, and workflow result is invented for this demo.

See [DATA_LICENSE.md](DATA_LICENSE.md) for exact paths, attribution, transformation notes, and ODbL/DbCL scope.

## Verify

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
python3 -B scripts/build_catalog_snapshot.py
```

The runtime and tests use the Python standard library plus plain HTML, CSS, and JavaScript.

## Limitations

Open Food Facts is community-contributed corroborating evidence, not an authoritative or continuously current registry. A match is a bounded comparison, not entity-resolution certification. No credential, destination, write adapter, persistent storage, telemetry, or production integration exists.

Owner-created code and documentation are governed by the root `LICENSE`. That license does not relicense the bundled third-party data.
