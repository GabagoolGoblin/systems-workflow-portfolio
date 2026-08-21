# Interface contract report: synthetic-operations-interface

**Result:** `MATCHED`

Deterministic fixture contracts only; not full WCAG conformance, legal certification, browser testing, or assistive-technology certification.

## Summary

| Cases | Matched | Regressed | Expected violations | Actual violations |
|---:|---:|---:|---:|---:|
| 3 | 3 | 0 | 11 | 11 |

Fixture bundle SHA-256: `5f6e01efaa8cd0fc916c19b0bbede35f2b23c8b06390bfc7f5838dff7df267eb`

JSON report SHA-256: `e77102dd29f482aa68443f5df4992eafd1e119b590c6724e85184bafac84f021`

## Cases

### accessible-operations-panel — PASS

Fixture: `components/accessible-operations-panel.html`  
Fixture SHA-256: `a8997c00a56c725d2c2027e07be450a78a7a567e0ae988647b9ac6d26f59bb6b`

No violations in the selected contract scope.

### missing-names-panel — PASS

Fixture: `components/missing-names-panel.html`  
Fixture SHA-256: `9908d8ee9108c41ac140dc8a3fe1b2378f24d27e3b6466ee88be79edbdeee293`

| Rule | Node | Location | Message |
|---|---|---:|---|
| `document-language` | `html[1]` | 2:0 | <html> must declare a lang value |
| `image-alternative` | `html[1]/body[1]/main[1]/section[1]/img[1]` | 11:6 | img must declare alt; alt="" is accepted for declared decoration |
| `interactive-name` | `html[1]/body[1]/main[1]/section[1]/a[1]` | 12:6 | interactive element has no accessible name |
| `interactive-name` | `html[1]/body[1]/main[1]/section[1]/form[1]/button[1]` | 15:8 | interactive element has no accessible name |
| `form-control-name` | `html[1]/body[1]/main[1]/section[1]/form[1]/input[1]` | 14:8 | form control has no accessible name |
| `aria-reference-integrity` | `html[1]/body[1]/main[1]/section[1]/form[1]/input[1]` | 14:8 | aria-describedby references missing ids: owner-help |
| `explicit-button-type` | `html[1]/body[1]/main[1]/section[1]/form[1]/button[1]` | 15:8 | button type must be explicitly button, reset, or submit |

### structural-regressions — PASS

Fixture: `components/structural-regressions.html`  
Fixture SHA-256: `49753386ec2cc6de5fba50798796d8fb8236cd4d5db3d9acc278f3a7e4b6d289`

| Rule | Node | Location | Message |
|---|---|---:|---|
| `unique-id` | `html[1]/body[1]/main[1]/section[1]/div[2]` | 13:6 | duplicate id 'deployment' |
| `heading-order` | `html[1]/body[1]/main[1]/section[1]/h4[1]` | 11:6 | heading level jumps from h2 to h4 |
| `table-header-contract` | `html[1]/body[1]/main[1]/section[1]/table[1]` | 14:6 | data table contains td cells but no th cells |
| `table-header-contract` | `html[1]/body[1]/main[1]/section[1]/table[2]/thead[1]/tr[1]/th[1]` | 20:19 | th scope must be row, col, rowgroup, or colgroup |
