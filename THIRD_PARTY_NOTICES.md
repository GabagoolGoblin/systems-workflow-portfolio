# Third-party notices

## Open Food Facts text identity data

The following paths contain or describe a frozen, text-only selection of Open Food Facts database contents:

- `projects/public-product-validation/data/open_food_facts_snapshot.json`
- `projects/public-product-validation/data/catalog_snapshot.js`
- `projects/public-product-validation/data/DATA_REDACTION_RECEIPT.json`
- `projects/public-product-validation/DATA_LICENSE.md`

Source: Open Food Facts. The database is offered under the Open Database License 1.0 (ODbL); individual database contents are offered under the Database Contents License 1.0 (DbCL). Exact license texts are distributed at:

- `third_party/licenses/ODbL-1.0.txt`
- `third_party/licenses/DbCL-1.0.txt`

The public snapshot retains retrieval times, requested fields, and source URLs. It omits only locally added request-contact metadata, as bound by the redaction receipt; it is not represented as an exact raw capture. Product images are excluded. Open Food Facts supplied no prices: every price, operator submission, site, workflow result, and decision is explicitly synthetic.

## Verification-only dependencies

The repository records but does not vendor verification-only Python packages in `requirements-ci.lock`. Those packages and pinned GitHub Actions remain governed by their upstream terms. Installing the lock or running CI obtains them from their respective distribution services; dependency source is not copied into this repository.

The root license never overrides the third-party data terms above.
