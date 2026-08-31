# Bulk Price Control

> INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION

A standard-library Python demonstration of a guarded bulk-price workflow. It keeps preview, staging, human confirmation, local commit, reread verification, rollback, and audit evidence distinct so a valid plan is never mistaken for an authorized or successful write.

[Watch the 16:9 how-to video](../../docs/VIDEO_GUIDES.md#bulk-price-control).

## Run in 60 seconds

Requirements: Python 3.11 or 3.12 on a POSIX system; no runtime package install.

```bash
python3 -B -m price_tool dry-run \
  --catalog fixtures/catalog.synthetic.json \
  --changes fixtures/changes.synthetic.csv
python3 -B -m unittest discover -s tests -v
```

The dry run validates and prints a plan without creating a file or lock sidecar.

## Five-minute walkthrough

1. Inspect the four-item synthetic catalog and three-row change file.
2. Run `dry-run` and review policy checks, reasons, and exact before/after prices.
3. Copy the catalog to a disposable directory and run `stage` to create a non-overwriting manifest and hash-chained audit event.
4. Review the stage and supply its exact stage ID to `commit`.
5. Run `verify-audit`; then discuss rollback and concurrency tests.

See the complete disposable commands in the CLI help: `python3 -B -m price_tool --help`.

## Implemented

- Strict catalog and CSV contracts with duplicate, scope, activity, category, money, reason, and batch-size validation.
- Two-decimal `Decimal` calculations.
- Same-snapshot stage parsing/digesting and exact stage-ID confirmation.
- POSIX advisory locks with documented ordering.
- Atomic catalog replacement, reread/full-catalog verification, rollback, and hash-chained audit events.
- 43 tests including concurrent appends/commits and injected post-write failure.

## Architecture and data flow

`dry-run` is write-free. `stage` binds exact catalog bytes, policy, changes, reasons, and timestamp to a new stage file. `commit` locks the catalog, rejects drift/tamper/reuse, records start, writes atomically, rereads, and records success only after verification. A caught failure restores and verifies the original bytes before recording rollback evidence.

## Verify

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
```

Tests use temporary directories and synthetic fixtures; they do not mutate the checked-in catalog.

## Limitations and non-claims

There is no point-of-sale, database, cloud, ticketing, or production-system connector. Advisory locks coordinate only cooperating local processes. Hash chaining is tamper-evident, not immutable or signed. Process kill and storage failure require external recovery procedures not implemented here.

## Provenance

Every venue, item, SKU, price, and reason is invented. The formats do not claim compatibility with a private export. See [PROVENANCE.md](PROVENANCE.md).

## License scope

Owner-created files are governed only by the repository root `LICENSE`. Generated local stages and audits are not repository content.
