# Claims and boundaries

## Supported

- Implemented a local guarded bulk-price workflow with preview, stage, exact confirmation, verified commit, rollback, and audit evidence.
- Enforced strict schema, policy, money, identity, and batch-size rules using standard-library Python.
- Added atomic replacement, same-snapshot digest binding, documented lock order, and concurrency/tamper tests.
- Verified this project with 43 tests.

## Not supported

- A point-of-sale integration, live menu update, customer deployment, remote transaction, or production operating history.
- Authentication, authorization, distributed locking, durable queueing, backup, disaster recovery, or an immutable audit ledger.
- Protection from processes that ignore the advisory lock or from every crash/storage failure mode.
