# Catalog Migration Validator

> INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION

An offline standard-library Python demonstration of a controlled catalog migration. It validates two deliberately different schema versions, requires explicit field and category mappings, quarantines invalid source records, reconciles every count, and binds a reviewable plan before a local target write can occur.

## Run in 60 seconds

Requirements: Python 3.11 or 3.12 on a POSIX system; no runtime package install.

```bash
python3 -B -m migration_tool dry-run \
  --source fixtures/source.synthetic.json \
  --target fixtures/target.synthetic.json \
  --mapping fixtures/mapping.synthetic.json
python3 -B -m unittest discover -s tests -v
```

The supplied dry run reconciles five source records into one insert, one update, one unchanged record, and two quarantined exceptions.

## Five-minute walkthrough

1. Compare the source, target, and explicit mapping schemas.
2. Run `dry-run` and trace eligible records, quarantines, operations, and reconciliation.
3. Copy the target into a disposable directory and run `stage` to create new plan, quarantine, and audit artifacts.
4. Review both artifacts and provide the exact plan ID to `apply`.
5. Verify the audit and discuss target-drift, tamper, rollback, and partial-migration tests.

Use `python3 -B -m migration_tool --help` for the full disposable command syntax.

## Implemented

- Strict versioned JSON contracts, duplicate-key/non-finite rejection, identity/currency checks, and referential integrity.
- Five explicit field renames and complete category-to-department mappings.
- Per-record quarantine with stable exception digest.
- Insert/update/unchanged classification, projected target, and exact count reconciliation.
- Content-addressed plan, exact confirmation, POSIX locks, atomic apply, reread verification, rollback, and hash-chained audit.
- 40 tests over schema, mapping, drift, tamper, safe writes, and path aliases.

## Architecture and data flow

`dry-run` computes without writing. `stage` validates again and writes non-overwriting plan/quarantine artifacts plus their digests. `apply` rejects changed targets or artifacts, records start, atomically replaces the local target, rereads and validates the result, and records success only when digests and reconciliation match.

## Verify

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
```

Tests use synthetic data and temporary directories.

## Limitations and non-claims

This is not a production migration adapter. The schema and transforms intentionally omit modifiers, taxes, schedules, localization, media, and multi-currency conversion. Quarantined records can coexist with an otherwise eligible plan; a human must decide whether partial migration is acceptable. Authentication, authorization, encryption, retention, backup, and remote transaction handling are absent.

## Provenance

All names, categories, prices, identifiers, and records are invented. No private export format or operational system is represented. See [PROVENANCE.md](PROVENANCE.md).

## License scope

Owner-created files are governed only by the repository root `LICENSE`. Generated plans, targets, quarantines, and audits are excluded from the release.
