# White-Label Deployment Checklist

Use this checklist when preparing OrcestrateOS for a new client or white-label deployment.

## Branding

- [ ] Replace logo assets in `assets/brand/` with client branding
- [ ] Update application name in UI configuration
- [ ] Update favicon and meta tags
- [ ] Verify no "OrcestrateOS" or internal branding leaks into client-facing UI
- [ ] Review email templates for branding references

## Configuration

- [ ] Create client-specific config patch file (`config/config_pack.<client>.patch.json`)
- [ ] Set all environment variables for the new deployment
- [ ] Configure OAuth redirect URLs for the client's domain
- [ ] Update CORS allowed origins

## Data Isolation

- [ ] Separate Supabase project (or schema) for client data
- [ ] Separate Google Drive root folder
- [ ] Verify no cross-client data leakage in API responses
- [ ] Confirm audit logs are client-scoped

## Security

- [ ] Generate unique `JWT_SECRET` for this deployment
- [ ] Configure client-specific OAuth credentials
- [ ] Review API rate limits for client usage patterns
- [ ] Ensure no shared secrets across deployments

## Documentation

- [ ] Internal deployment runbook created
- [ ] Client-facing docs stripped of internal references
- [ ] Document classification reviewed per `PUBLIC_PRIVATE_DOCS_MATRIX.md`
- [ ] Support escalation path documented

## Testing

- [ ] Full smoke test on client deployment
- [ ] Verify all client-specific config overrides work
- [ ] Test OAuth flow end-to-end on client domain
- [ ] Verify PDF generation and export with client branding

## Go-Live

- [ ] DNS configured and SSL certificates provisioned
- [ ] Monitoring set up for client environment
- [ ] Backup schedule confirmed
- [ ] Rollback plan documented
