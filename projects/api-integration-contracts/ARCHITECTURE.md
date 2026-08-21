# Architecture

> Independent portfolio demonstration. Synthetic inputs only. Offline. No production action.

```text
strict local contract + run fixture
          │
          ├─ webhook deliveries
          │    header → signature → replay → idempotency → schema
          │                         └─ ready / duplicate / quarantine
          │
          └─ supplied API attempts
               request contract → 429 / 429 / 202 contracts
               → virtual delays [2, 4] → human-eligible state
                               │
                               ▼
                    canonical hash-linked events
                               │
                               ▼
                    deterministic JSON receipt
                         ├─ CLI verify/simulated action
                         └─ generated browser snapshot
                                      ▼
                              six static UI screens
```

## Trust boundaries

1. File loading rejects symlinks, oversized/non-UTF-8 input, duplicate keys, non-finite values, excessive depth/nodes, unknown fields, and mismatched expected states.
2. Webhook fixtures bind timestamp plus exact raw body bytes with HMAC-SHA256. The key is intentionally public test material, not secrecy.
3. Idempotency keys enter the in-memory accepted set only after signature, timestamp, and payload checks pass.
4. API attempts are fixture objects, not HTTP responses. Correlation, schema, sequence, terminality, attempt count, and virtual retry caps fail closed.
5. Human eligibility is not authority. The CLI emits a simulated receipt; the browser records only transient local state.
6. The receipt binds canonical events and exact input digests. SHA-256 detects drift but supplies no author identity, signature, trusted time, or immutable storage.
7. Browser values flow through `textContent`; the runtime has no fetch, socket, form, storage, unsafe-HTML, credential, or production connector.

## Determinism

The evaluator uses a fixed synthetic clock and canonical UTF-8 JSON. The tracked base receipt and browser snapshot rebuild from exact fixtures. Verification performs all rebuilds in a temporary copy and compares bytes.
