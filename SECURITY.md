# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in OrcestrateOS, please report it responsibly.

**Contact:** Open a private security advisory via GitHub's "Report a vulnerability" feature on this repository, or email the repository owner directly.

**Do NOT** open a public issue for security vulnerabilities.

### What to include

- Description of the vulnerability
- Steps to reproduce
- Affected files or modules
- Potential impact

### Response timeline

- **Acknowledgment:** Within 48 hours
- **Assessment:** Within 1 week
- **Fix deployed:** As soon as practical, depending on severity

## Secret Rotation Procedure

1. **Identify** the exposed secret (JWT key, API key, service role key, etc.)
2. **Revoke** the old secret immediately in the provider dashboard (Supabase, Google Cloud, etc.)
3. **Generate** a new secret using a cryptographically secure method
4. **Update** the runtime environment (Replit Secrets, deployment env vars) with the new value
5. **Verify** the application works with the new secret
6. **Audit** git history — if the secret was ever committed, consider it compromised regardless of branch

### Secrets that must NEVER be committed

- `JWT_SECRET`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GOOGLE_CLIENT_SECRET`
- Any `.env` file (except `.env.example` with placeholders only)

## Supported Versions

| Version | Supported |
| ------- | --------- |
| main    | Yes       |
| Other   | No        |
