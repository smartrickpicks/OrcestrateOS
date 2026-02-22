# No Hardcoded Secrets Policy

## Rule

**No secret, credential, API key, or token may be committed to this repository — in any file, on any branch.**

## What counts as a secret

- JWT signing keys (`JWT_SECRET`)
- Database connection strings with credentials
- Supabase service role keys (`SUPABASE_SERVICE_ROLE_KEY`)
- Google OAuth client secrets (`GOOGLE_CLIENT_SECRET`)
- API keys for any third-party service
- Private keys, certificates, or signing material
- Any value that, if leaked, would grant unauthorized access

## Where secrets belong

| Context | Storage |
|---------|---------|
| Local development | `.env` file (git-ignored) |
| Replit | Replit Secrets (Settings > Secrets) |
| Production | Deployment environment variables |
| Documentation | `.env.example` with placeholder values only |

## What to do if a secret is committed

1. **Assume it is compromised** — even if the branch was private or quickly deleted
2. **Rotate immediately** — generate a new secret and deploy it
3. **Revoke the old secret** — disable it in the provider's dashboard
4. **Audit** — check logs for unauthorized usage during the exposure window
5. **Prevent recurrence** — verify `.gitignore` and pre-commit hooks are in place

## Enforcement

- The PR checklist includes a "No hardcoded secrets" checkbox
- CODEOWNERS requires review for changes to `.replit`, `.env*`, and config files
- Consider adding a pre-commit secret scanner (e.g., `gitleaks`, `detect-secrets`) as a future enhancement

## Known historical violations

| File | Secret | Status |
|------|--------|--------|
| `.replit` line 63 | `JWT_SECRET` (plaintext) | Replaced with placeholder — **rotate the key** |
| `.replit` line 64 | `DRIVE_ROOT_FOLDER_ID` | Replaced with placeholder |
