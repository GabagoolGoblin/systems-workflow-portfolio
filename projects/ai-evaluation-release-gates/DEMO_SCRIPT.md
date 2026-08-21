# Demo script

Suggested review time: five minutes. Everything shown is synthetic, static, local, and non-authoritative.

## 1. Establish the contract

Open `index.html` and point to the permanent boundary. On **Brief**, show twelve cases, four dimensions, eight exact-grader cases, four human-rubric cases, and the `PENDING`/`HOLD`/`ROLLBACK` vocabulary.

## 2. Compare exact and qualitative evidence

On **Blind review**, select `DEV-003` and run the exact contract: one response adds an undeclared JSON key and fails. Select `DEV-002`, record separate A/B scores, and note that stored human inputs use blind labels rather than candidate IDs.

## 3. Reveal the holdout deliberately

Filter to holdouts. Before reveal, the base bundle contains IDs, slices, veto flags, and hashes—but no task briefs, outputs, grader details, or candidate bindings. Trigger reveal; the browser loads a second local file and recomputes the complete-payload hash before exposing details.

## 4. Trace a hard veto

Select `HOLD-103`, then use **Failure atlas** and **Regression matrix** to connect the safe-escalation failure to a hard veto.

## 5. Close on authority

On **Release gate**, load the reference review for `HOLD` and the regression drill for `ROLLBACK`. Export local JSON and explain that its hashes detect content drift; they do not identify or authorize a reviewer. No production decision exists inside the lab.
