# Document Classification Matrix

All documentation in this repository must be classified into one of three tiers.

## Classification Tiers

| Tier | Label | Location | Who can see it |
|------|-------|----------|----------------|
| 1 | **Public** | `docs/` (this repo) | Anyone — open source, marketing, onboarding |
| 2 | **Internal** | `docs/` with `<!-- classification: internal -->` header | Team members only — architecture decisions, runbooks |
| 3 | **Restricted** | Private repo or encrypted vault | Owner only — credentials, client data, audit logs |

## Current Document Classification

| Document | Tier | Notes |
|----------|------|-------|
| `docs/contract_health_overview.md` | Public | Feature documentation |
| `docs/contract_health_calibration.md` | Public | Technical specification |
| `CONTRIBUTING.md` | Public | Contributor guide |
| `SECURITY.md` | Public | Security reporting policy |
| `docs/handoff/*` | **Restricted** | Must move to private repo |
| `EDDIE_LOOK_HERE_DO_THIS.txt` | **Restricted** | Internal task notes — excluded from git |

## Rules

1. **Default to Internal** — if unsure, classify as Internal until reviewed
2. **No secrets in any tier** — credentials go in environment variables, never in docs
3. **Review on PR** — every PR that adds or modifies docs must confirm classification in the PR checklist
4. **Quarterly audit** — review all `docs/` files against this matrix every quarter
