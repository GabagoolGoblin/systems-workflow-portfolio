# Support Triage Workbench

> INDEPENDENT PORTFOLIO DEMO · SYNTHETIC SUPPORT RECORDS · NO AFFILIATION · NO SEND ACTION

An offline, standard-library demonstration of safe support-intake automation: strict input contracts, deterministic routing, ambiguity holds, evidence-preserving response outlines, explicit approval, and a hash-linked local audit.

## Run in 60 seconds

```bash
mkdir -p out
python3 -B workbench.py triage fixtures/synthetic_tickets.json \
  --audit out/demo.audit.jsonl \
  --output out/triage.json
python3 -B workbench.py verify-audit out/demo.audit.jsonl
```

Add `--approve-eligible` only to model an explicit operator approval. Held records remain blocked. No path sends a message or changes an external system.

## Five-minute walkthrough

1. Inspect the strict `synthetic-ticket-batch/v1` fixture and unknown-field rejection.
2. Run triage and review deterministic severity, category, and ownership.
3. Compare complete tickets with completeness, ambiguity, safety, and duplicate holds.
4. Inspect high-confidence redaction and response outlines that never claim a resolution.
5. Verify the append-only JSONL audit, then tamper with a temporary copy to observe fail-closed verification.

## Implemented evidence

- Strict versioned schema and explicitly synthetic identifiers.
- Deterministic severity, category, and generic ownership lanes.
- Batch-local duplicate detection and structured sensitive-value redaction.
- Open questions and holds instead of guessed facts.
- Separate pending, blocked, and explicitly human-approved states.
- Append-only, hash-linked local audit with verification before append.
- Standard-library CLI, 17 core tests, and a deterministic publication scanner.

## Verify

```bash
python3 -B -m unittest discover -s tests -v
python3 -B tools/publication_scan.py
```

## Limitations

Every ticket, person, site, identifier, observation, time, and value is invented. The workbench has no network client, account, credential, ticketing adapter, send action, or external persistence. A rendered reply is local JSON, not a sent message. The rules are demo logic, not an organization's operating model or a measured production result.

See [CLAIMS_AND_BOUNDARIES.md](CLAIMS_AND_BOUNDARIES.md) and [PROVENANCE.md](PROVENANCE.md). All owner-created material is governed by the common root `LICENSE`.
