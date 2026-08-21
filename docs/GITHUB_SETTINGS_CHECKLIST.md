# GitHub settings checklist

Complete these settings only after the owner approves the release and remote creation.

- [ ] Create the repository with default branch `main` and the approved visibility.
- [ ] Add the approved public Git account to `.github/CODEOWNERS`; grant no outside account write access.
- [ ] Protect `main`; require the verification workflow and conversation resolution.
- [ ] Disallow force pushes and branch deletion on `main`.
- [ ] Enable secret scanning and push protection when supported by the account tier.
- [ ] Enable private vulnerability reporting and use Security Advisories for vulnerability intake.
- [ ] Keep Pages and release automation disabled until separately approved.
- [ ] Disable Issues.
- [ ] Pull requests cannot be disabled on a public GitHub repository; protect `main`, grant no outside write access, and close unsolicited pull requests without review.
- [ ] Use GitHub platform report/block controls for conduct abuse.
- [ ] Record a separate post-remote settings receipt proving the intended settings; this pre-remote checklist is not evidence that they are active.
- [ ] Disable wiki and discussions unless they will be maintained.
- [ ] Use only the approved public Git author name and approved noreply or public email.
- [ ] Review the initial tracked path list, commit/tree hashes, and clean-clone receipt before any push.

The issue and pull-request templates are dormant scaffolding. Their presence in
the source tree does not imply that either repository feature is enabled.
