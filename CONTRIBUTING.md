# Contributing to OrcestrateOS

## Branch Naming Convention

```
feature/<module>/<short-description>   # new features
fix/<description>                      # bug fixes
chore/<description>                    # maintenance
docs/<description>                     # docs only
release/v<semver>                      # releases
```

Examples:
- `feature/server/add-batch-export`
- `fix/oauth-token-refresh`
- `chore/update-dependencies`
- `docs/api-endpoint-reference`
- `release/v2.5.7`

## Pull Request Workflow

1. **Create a branch** from `main` using the naming convention above
2. **Make your changes** — keep PRs focused on a single concern
3. **Run tests locally** before pushing
4. **Open a PR** against `main` — the PR template will guide you through the checklist
5. **Request review** from a code owner (see `.github/CODEOWNERS`)
6. **Address feedback** and get at least 1 approval
7. **Merge** via squash-and-merge (preferred) or merge commit

## Development Setup

### Prerequisites

- Node.js 22+
- Python 3.11+
- PostgreSQL 16 (for local development)

### Getting started

```bash
# Clone the repo
git clone https://github.com/smartrickpicks/OrcestrateOS.git
cd OrcestrateOS

# Copy environment template
cp .env.example .env

# Fill in your secrets in .env (see .env.example for required variables)

# Install Node dependencies
cd ui && npm install && cd ..

# Install Python dependencies
pip install -r requirements.txt  # if applicable

# Run smoke tests
bash scripts/replit_smoke.sh
```

## Code Standards

- **No hardcoded secrets** — use environment variables for all credentials
- **No generated files in git** — `out/` directory output should never be committed
- **Document classification** — mark docs as Public, Internal, or Restricted
- **Keep PRs small** — prefer multiple focused PRs over one large changeset

## Questions?

Open an issue on this repository or reach out to @smartrickpicks.
