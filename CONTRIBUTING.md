# Contributing

This employer-viewable portfolio is not accepting external contributions. The
intended public-repository settings disable both Issues and pull requests, and
no outside account receives write access. Any intake template retained in the
tree is dormant scaffolding, not an invitation or review commitment.

The requirements below apply only to an owner-authorized local change. They
grant no additional permission to copy, modify, or redistribute repository
material beyond GitHub's Terms of Service and applicable law.

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

Unsolicited patches are not accepted. If pull-request mechanics are ever
temporarily available before the required settings are applied, unsolicited
pull requests are closed without review.
