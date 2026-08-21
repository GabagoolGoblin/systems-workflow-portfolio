# Data provenance

## Repository rule

Every bundled operational fixture, visible person or organization, identifier, price, event, timestamp, prompt, output, score, and decision was created for these demonstrations except the explicitly bounded Open Food Facts text identity fields below. No employer, customer, vendor tenant, applicant, or production-system extract is represented.

Selected hero images are local renders of checked-in synthetic interfaces. Three featured screenshots were captured from the public demo interfaces at 1440×960 and reviewed at native resolution. No hero contains a remote font, third-party logo, product screenshot, or external image asset.

## Open Food Facts snapshot

`projects/public-product-validation/data/open_food_facts_snapshot.json` retains six frozen GET response records limited to barcode/product identity text, retrieval times, requested fields, source URLs, and attribution. Product images are excluded. ODbL/DbCL paths and terms are listed in `THIRD_PARTY_NOTICES.md` and the project `DATA_LICENSE.md`.

The release snapshot is not an exact raw capture. `data/DATA_REDACTION_RECEIPT.json` binds the original capture hash, release hash, exact removal of `/user_agent`, and canonical hashes proving the retained public response/product fields are semantically identical. The omitted field was locally added request-contact metadata, not an API response field.

Every displayed price, site, operator submission, workflow result, and decision in that project is synthetic and not sourced from Open Food Facts.

## Transformations

Generated JSON/JavaScript/HTML evidence is derived from checked-in fixtures or the bounded public snapshot. `tools/release/verify_generated.py` rebuilds applicable outputs inside temporary copies and compares exact bytes. Screenshots are reviewed artifacts, not claimed as cross-environment byte-reproducible builds.
