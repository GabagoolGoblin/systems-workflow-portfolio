# Demo script

## 90-second portfolio path

### 1. Intake & parse (20 seconds)

“The input is deliberately operator-shaped: separators vary, barcodes contain spaces or hyphens, fields can be missing, and one note tries to inject HTML and tell the system to bypass validation. Only a small allowlist of labeled fields is parsed. The complete raw submission stays beside the normalized result.”

Call out the persistent boundary: public product identity is real frozen evidence; every submission, price, site/menu, result, run identifier, and event is synthetic/demo-only. Runtime requests and write connectors are both zero.

### 2. Validation queue (25 seconds)

“The GS1 check digit is the first hard gate. Twelve-digit UPC-A `034000470693` is preserved as raw input and normalized to `0034000470693`; that is also the normalized code returned by the retained Open Food Facts request. The duplicate Alter Eco submissions normalize to the same GTIN but disagree on invented demo price, so both are held. The invalid barcode and hostile note never reach public matching.”

Select different rows to show raw input, canonical barcode, public fields, comparison outcome, and explanation.

### 3. Human decision (25 seconds)

“The proposal and public record are intentionally separated. Open Food Facts supplied identity facts; it supplied no price. A mismatch cannot be approved. An identity-aligned record can be staged only after the reviewer acknowledges that this is a synthetic, in-memory decision. Even then, nothing is written anywhere.”

Try the Häagen-Dazs case first (blocked size mismatch), then the Reese's case (aligned after leading-zero normalization). Tick the acknowledgement and record a demo decision. Point to the receipt's `External writes: 0` statement.

### 4. Evidence ledger (20 seconds)

“The demo retains six exact API responses: five found products and one valid-code/not-found control. Every record carries an ISO UTC retrieval time and its precise request URL. The snapshot names Open Food Facts, ODbL for the database, and DbCL for individual contents. Product images were excluded. A digest and a local manifest make later drift visible.”

End with the limits card: public evidence is not proof of authority, currency, or completeness.

## Expected bundled outcomes

| Synthetic case | Expected demo-only result | Why |
|---|---|---|
| Nutella | Ready | Valid code; supplied brand, name, and 400 g quantity align with the frozen record. Human gate still required. |
| Reese's | Ready | Valid UPC-A; normalized leading zero produces the public EAN-13; supplied identity aligns. |
| Häagen-Dazs | Mismatch | Operator says 4 fl oz; frozen public record says 3 fl. oz. (88 mL). |
| Alter Eco A + B | Conflict | Same normalized GTIN, different synthetic demo prices. |
| Cristaline | Mismatch | Brand and quantity align, but operator name differs from the frozen public product name `isabelle`. |
| Hostile text | Invalid | Check digit fails; markup and bypass language remain escaped plain text. |
| Northstar Foods | Not found | `9999991234567` has a valid check digit; the retained API response was HTTP 404/product not found. |
| Unlabeled sample | Unknown | No readable barcode exists; the demo refuses to guess. |

These are workflow test fixtures, not real operating claims or assertions about current product availability or price.
