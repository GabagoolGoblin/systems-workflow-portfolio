# Contributing

This employer-viewable portfolio is not accepting external contributions.
Issues are disabled, pull requests are not reviewed, and no outside account
has write access. Any intake template retained in the tree is dormant
scaffolding, not an invitation or review commitment.

The requirements below apply to the maintainer's own local changes. They do
not change the repository license.

## Required boundaries

- Use synthetic data unless a public source, retrieval record, transformation, and license scope are added and reviewed.
- Never add credentials, employer/customer records, private screenshots, application material, or production identifiers.
- Do not add company logos, copied product interfaces, or claims about proprietary product behavior.
- Preserve each project's explicit limitations and non-claims.
- Add or update tests for behavior changes.
- Rebuild generated examples in a temporary copy and prove byte equality; verification must not rewrite tracked files.
- Review UI and screenshot changes at full resolution, including the persistent disclosure.

## Local checks

```bash
make policy
make unit
make generated
make browser
```

Do not commit caches, local output, logs, browser reports, or generated operational data.

The repository does not accept pull requests.
