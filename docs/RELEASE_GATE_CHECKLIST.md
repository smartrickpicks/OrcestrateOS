# Release Gate Checklist

Before any release to production, all of the following gates must pass.

## Pre-Release Gates

### Code Quality
- [ ] All PRs merged to `main` via approved pull request
- [ ] No open PRs with "blocking" label
- [ ] No `TODO(release)` or `FIXME(release)` comments in codebase

### Testing
- [ ] Smoke tests pass (`bash scripts/replit_smoke.sh`)
- [ ] Manual QA pass on staging environment
- [ ] No regressions in core workflows (contract generation, evidence viewer, export)

### Security
- [ ] No hardcoded secrets in codebase (see `NO_HARDCODED_SECRETS_POLICY.md`)
- [ ] All secrets rotated since last release (if any were exposed)
- [ ] Dependencies checked for known vulnerabilities
- [ ] `.gitignore` covers all generated and sensitive files

### Documentation
- [ ] `docs/` classification confirmed per `PUBLIC_PRIVATE_DOCS_MATRIX.md`
- [ ] `CHANGELOG.md` updated (if maintained)
- [ ] `.env.example` reflects all required environment variables

### Infrastructure
- [ ] Environment variables set in deployment target
- [ ] Database migrations applied (if applicable)
- [ ] Rollback plan documented

## Post-Release Verification

- [ ] Production smoke test passes
- [ ] Monitoring/alerting confirmed operational
- [ ] Release tagged in git (`release/v<semver>`)

## Release Sign-off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Owner | @smartrickpicks | | [ ] |
