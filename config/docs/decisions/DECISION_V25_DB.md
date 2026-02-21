# Decision: V2.5 Canonical Database

**Version:** 2.5
**Date:** 2026-02-12
**Status:** Locked

## Decision

PostgreSQL is the canonical database for Orchestrate OS API v2.5.

## Context

Orchestrate OS currently stores all governance state client-side:
- **localStorage:** Role preferences, UI mode (`viewer_mode_v10`), patch request store (`pr:` prefix keys), artifact store (`fs:` prefix keys)
- **IndexedDB:** Workbook session cache (`SessionDB`), audit events (`orchestrate_audit`), large dataset payloads

API v2.5 requires multi-user persistence, server-side audit emission, and cross-user collaboration. Browser-side storage cannot serve these needs.

## Constraints

1. PostgreSQL (Supabase-compatible) is the single canonical store for all durable collaboration and governance state
2. SQLite or other stores may only be optional local dev fallback and must be clearly marked non-canonical
3. All mutating operations go through the API; the database is not directly accessed by clients
4. Append-only semantics enforced for the `audit_events` table (no UPDATE, no DELETE)

## Schema Compatibility

- Supabase-compatible: standard PostgreSQL with Row Level Security (RLS) support
- UUID and ULID-compatible column types (`TEXT` or `VARCHAR` for prefixed IDs)
- JSONB for flexible metadata fields
- Timestamp columns use `TIMESTAMPTZ` (UTC)

## Migration Strategy

1. **Migration files:** `server/migrations/NNN_description.sql` — ordered, idempotent SQL
2. **Migration runner:** Python utility executed on server startup
3. **Seed fixtures:** Deterministic dev/test data in a separate migration file
4. **Rollback:** Each migration paired with a down migration where safe

## Coexistence During Transition

- Client-side localStorage/IndexedDB continues operating for offline-first UX
- Server is authoritative for all governance state once API is active
- Dual-write period: client writes locally AND to server; server is source of truth
- Feature flags control per-resource server adoption

## Alternatives Considered

| Option | Rejected Because |
|--------|-----------------|
| SQLite | Not suitable for multi-user concurrent access; no Supabase compatibility |
| Firebase/Firestore | Vendor lock-in; non-relational model doesn't fit governance schema |
| MongoDB | Schema flexibility not needed; relational integrity required for governance |
| Continue with localStorage only | Cannot support multi-user, server-side audit, or cross-device access |

## Cross-References

- `docs/decisions/DECISION_STORAGE_POLICY.md` — V2.3 storage policy (localStorage vs IndexedDB)
- `docs/handoff/V25_READINESS_REPORT.md` — V2.5 readiness audit
- `docs/api/API_SPEC_V2_5_CANONICAL.md` — API contract (forthcoming)
