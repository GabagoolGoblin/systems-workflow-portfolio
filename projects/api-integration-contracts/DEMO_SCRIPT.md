# Demo script

Suggested review time: five minutes.

## 1. Establish the boundary

Open `index.html` and point to the permanent synthetic/offline/no-production disclosure. State that the fixture, endpoint, HMAC value, token, and outcomes are invented and no transport exists.

## 2. Inspect bounded recovery

Open **Request / response**. Trace the supplied `429`, `429`, `202` attempts. The retry policy selects virtual delays of two and four seconds; the engine reports zero sleeps and zero network calls. A terminal response must be last.

## 3. Route adverse webhook input

Open **Webhook inbox** and filter duplicate/quarantine states. On **Quarantine**, compare signature, replay, schema, and header failures. Recovery requires a fresh delivery through the full contract; the UI cannot edit a failure into approval.

## 4. Exercise the human gate

On **Human gate**, enter the visible token, then separately check the portfolio acknowledgement. Explain that the token is not authentication and the action exists only in the current browser tab with `production_write=false`.

## 5. Close on evidence

Open **Audit receipt**. Show exact input digests, sequence-linked events, chain head, and receipt digest. Distinguish transient browser state from the deterministic base receipt. End with the non-claim: this demonstrates integration control design and test evidence, not a deployed integration.
