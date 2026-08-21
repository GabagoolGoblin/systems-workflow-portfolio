# Open Food Facts data license and attribution

This project contains a small, frozen, text-only data component from Open Food Facts. The repository's license for owner-created code and documentation does **not** relicense these files.

## Covered paths

- `data/open_food_facts_snapshot.json`: six retained API response records: five found products and one not-found control.
- `data/catalog_snapshot.js`: a deterministic browser-oriented transformation of that JSON snapshot.
- `data/DATA_REDACTION_RECEIPT.json`: hashes and exact JSON-pointer evidence for the public contact-metadata omission; it is provenance metadata, not an Open Food Facts response.

## Attribution

Contains information from [Open Food Facts](https://world.openfoodfacts.org/), made available here under the [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Individual database contents are made available under the [Database Contents License (DbCL) 1.0](https://opendatacommons.org/licenses/dbcl/1-0/).

The exact license texts distributed with this repository are:

- [ODbL 1.0](../../third_party/licenses/ODbL-1.0.txt)
- [DbCL 1.0](../../third_party/licenses/DbCL-1.0.txt)

Open Food Facts license guidance: <https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/license-be-on-the-legal-side/>

Every retained record includes its precise API v3 source URL and UTC retrieval time. The captured fields are `code`, `product_name`, `brands`, `quantity`, `categories`, and `countries`. No product image is downloaded, bundled, or displayed.

## Public-release transformations

The public JSON copy is **not the exact raw capture**. It:

- selects the same six retained response records;
- preserves their requested/canonical codes, retrieval times, source URLs, HTTP statuses, warnings, errors, and response fields;
- omits only the locally added `/user_agent` request-contact field rather than substituting a fictitious contact; and
- leaves every other JSON field unchanged, including the development request trace and all retained response records.

`data/DATA_REDACTION_RECEIPT.json` records the original snapshot SHA-256 (`1958632ef813a3ee0e6a6449f5ca74256b53dc2bfce12e5aecae3ec4f984ec2c`), public snapshot SHA-256 (`2bd27bdbb6b89e323ec1083dd01f0962f6c73a8df1da0a172a2c7e3bb0f1c9fb`), removed JSON pointer, and canonical hashes used by deterministic verification.

The JavaScript file renames selected fields for browser use and excludes no retained found-product identity fact. Run `python3 -B scripts/build_catalog_snapshot.py` to verify byte-for-byte derivation.

## Synthetic operations boundary

**Synthetic price (not sourced from Open Food Facts).** Open Food Facts supplied no price, site/menu, operator note, run event, decision, workflow state, or outcome used by the demo. Those values are invented and are not part of the ODbL/DbCL data component.

The frozen facts describe what the API returned at the recorded times. They do not establish current availability, correctness, endorsement, or authority to update any catalog. This notice records provenance and license scope; it is not legal advice.
