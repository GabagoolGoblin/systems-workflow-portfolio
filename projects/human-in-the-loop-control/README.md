# Human-in-the-Loop Control

> INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION

A clean-room, executable demonstration of fail-closed automation: keep one cached item per barcode, hold a repeated submitted request before lookup, resolve eligible identifiers, stage proposed values, reread them, block on mismatch, and require explicit human approval before updating synthetic in-memory state.

This public carve-out contains only executable Python/Tk code, a synthetic JSON fixture, headless tests, an external-path GUI smoke, and a fresh code-native browser preview. It contains no legacy image, generated-image metadata, application history, or unimplemented architecture claim.

[Watch the showcase and how-to videos](../../docs/VIDEO_GUIDES.md#human-in-the-loop-control).

## Open the browser preview

Open `preview/index.html` directly. It is a small executable HTML/CSS/JavaScript version of the same public state-machine boundary and makes no network request.

## Run the desktop demo

```bash
cd demos/hitl-desktop
python3 -B barcode_cache_demo.py
```

Use the five numbered actions. The later request that repeats a barcode stays held while the first request and other eligible rows advance. Toggle the mismatch option before reread to see the save gate fail closed.

The smaller same-process console demo is also runnable:

```bash
python3 -B automate_hitl.py
python3 -B automate_hitl.py --fail
python3 -B automate_hitl.py --log-path /tmp/hitl-demo.log
```

No log is written by default. An explicit log path must resolve outside the project tree.

## Verify

```bash
python3 -B -m unittest discover -s demos/hitl-desktop -p 'test_*.py' -v
```

The headless suite uses only the Python standard library. The GUI smoke in `smoke_test.py` requires Tk and a display. Its working logs stay in a temporary directory, and `--log-path` may write one summary only to an explicit path outside the project tree.

## Implemented evidence

- Exact synthetic-fixture validation and unique identifier checks.
- A unique barcode cache with a later duplicate request held before lookup.
- Cache hit/miss resolution with unknown rows held instead of guessed.
- Explicit manual mapping for a held identifier.
- Staging blocked until all eligible identifiers are resolved.
- Duplicate request rows excluded from identifier assignment, staging, reread, and approval.
- Reread verification and mismatch-induced batch hold.
- Save blocked until every eligible staged row verifies and a person invokes approval.
- Deterministic tests proving no default or tracked-tree log write.

## Limitations

Every name, identifier, price, state, and result is invented. "Write," "save," and "approve" refer only to local synthetic state. There is no system integration, credential, remote endpoint, durable store, product behavior, deployment, or production authority.

See [CLAIMS_AND_BOUNDARIES.md](CLAIMS_AND_BOUNDARIES.md) and [PROVENANCE.md](PROVENANCE.md). Owner-created material is governed by the common root `LICENSE`, and the clean-room provenance is recorded in `release-decisions.json`.
