# Provenance

This is an independently authored clean-room portfolio implementation of a general catalog-validation problem. The interface, parser, workflow, state transitions, synthetic operator submissions, prices, sites, notes, event times, decisions, synthetic operator-record uses of identifiers, and results were created for the demo. Exact frozen public identity fields—including retained UPC/EAN/GTIN values—are the exception described below.

No employer or customer code, screenshot, database row, ticket, credential, schema, branded interface, private product corpus, or product image is included. Real product identity fields are limited to the attributed frozen Open Food Facts snapshot described in [DATA_LICENSE.md](DATA_LICENSE.md).

For public packaging, exactly one locally added request-contact field was removed at JSON pointer `/user_agent`. The resulting file is not described as the exact raw capture. `data/DATA_REDACTION_RECEIPT.json` binds the original and public SHA-256 digests, the one removal operation, the canonical hash of every remaining field, and the retained-record hash. No replacement or fictitious contact was inserted.

Owner-created material is governed by the common root `LICENSE`, and its approved provenance is recorded in `release-decisions.json`. The third-party data paths remain under their stated ODbL/DbCL terms.
