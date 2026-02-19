# V2.54.1 — Release Runbook

**Version:** v2.54.1  
**Date:** 2026-02-17  
**Status:** Release Candidate

---

## 1. Release Overview

v2.54.1 delivers a role-aware, DB-first governance queue for the Operations View, replacing localStorage-driven workflows with PostgreSQL-backed annotation layer and feature-flagged progressive rollout.

### 1.1 Scope Summary

| Phase | Deliverable | Status |
|-------|-------------|--------|
| P0 | DB write URL fix, strict mode, workspace role enforcement, sandbox rehydration | Complete |
| P1 | `opsDbWriteRfiStatus()` + `opsDbWriteCorrectionStatus()` DB write functions | Complete |
| P2 | Drive batch dedupe (drive_file_id + revision_marker), source validation | Complete |
| P3 | Role-scoped list visibility, RFI custody transition matrix, centralized role resolution | Complete |
| P4 | Release readiness, cutover plan, monitoring guardrails, closeout QA | Complete |

---

## 2. Prerequisites

### 2.1 Environment Requirements

| Item | Requirement | Notes |
|------|------------|-------|
| PostgreSQL | v14+ | Neon-backed via Replit |
| Python | 3.11+ | FastAPI + uvicorn |
| Feature flags | Both `OPS_VIEW_DB_READ` and `OPS_VIEW_DB_WRITE` default to `false` | Safe baseline |
| Google OAuth | Client ID + Secret configured | For authenticated users |
| Existing migrations | 001–011 applied | Foundation for v2.54.1 |

### 2.2 Preflight Checks

Before applying migrations:

1. Verify current migration state:
   ```sql
   SELECT migration_id FROM schema_migrations ORDER BY applied_at DESC LIMIT 5;
   ```
2. Confirm no pending schema locks:
   ```sql
   SELECT pid, state, query FROM pg_stat_activity WHERE state = 'active' AND query LIKE '%ALTER%';
   ```
3. Take database snapshot/checkpoint via Replit UI
4. Verify server is running and healthy:
   ```bash
   curl -s http://localhost:5000/api/v2.5/health | python3 -m json.tool
   ```

---

## 3. Migration Order

Migrations must be applied sequentially. Both are idempotent (use `IF NOT EXISTS`/`IF EXISTS` guards).

### 3.1 Migration 012 — Operations View v2.54

**File:** `server/migrations/012_ops_view_v254.sql`

**Changes:**
- Adds `batch_id` column to `rfis` table (nullable FK to batches)
- Backfills `rfis.batch_id` from linked patches
- Creates performance indexes: `idx_rfis_batch`, `idx_rfis_custody`, `idx_patches_batch`, `idx_patches_record`, `idx_corrections_ws_status`

**Rollback:** Safe to leave indexes in place. To fully revert:
```sql
DROP INDEX IF EXISTS idx_rfis_batch;
DROP INDEX IF EXISTS idx_rfis_custody;
DROP INDEX IF EXISTS idx_patches_batch;
DROP INDEX IF EXISTS idx_patches_record;
DROP INDEX IF EXISTS idx_corrections_ws_status;
ALTER TABLE rfis DROP COLUMN IF EXISTS batch_id;
```

### 3.2 Migration 013 — Drive Batch Source

**File:** `server/migrations/013_drive_batch_source.sql`

**Changes:**
- Expands `batches_source_check` constraint to include `'drive'`
- Creates partial unique index `idx_batches_drive_dedupe` for concurrency-safe deduplication

**Rollback:**
```sql
DROP INDEX IF EXISTS idx_batches_drive_dedupe;
ALTER TABLE batches DROP CONSTRAINT IF EXISTS batches_source_check;
ALTER TABLE batches ADD CONSTRAINT batches_source_check
  CHECK (source = ANY (ARRAY['upload'::text, 'merge'::text, 'import'::text]));
```

---

## 4. Feature Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `OPS_VIEW_DB_READ` | `false` | When `true`, operations queue hydrates from PostgreSQL instead of localStorage |
| `OPS_VIEW_DB_WRITE` | `false` | When `true`, status transitions write to PostgreSQL with strict mode (local update only after DB success) |

**Safe defaults:** Both flags `false` means the system operates exactly as before v2.54.1 — localStorage-only, no DB interaction for the operations queue.

**Flag evaluation:** Cached on first access per process. Restart server to pick up changes. Call `feature_flags.clear_cache()` or restart the uvicorn process.

---

## 5. Rollback Decision Tree

### 5.1 DB Read Issues

**Symptoms:** Operations queue shows empty, 500 errors on `/operations/queue`, stale data after role switch

```
Is OPS_VIEW_DB_READ=true?
├── YES → Set OPS_VIEW_DB_READ=false → Restart server
│         └── Queue falls back to localStorage hydration
│         └── No data loss — DB data preserved for re-enablement
└── NO  → Issue is unrelated to v2.54.1 DB read path
```

**Recovery time:** Immediate (flag toggle + restart)  
**Data impact:** None — DB data is preserved, localStorage resumes as source

### 5.2 DB Write Issues

**Symptoms:** Status transitions fail silently, 500 on PATCH endpoints, local/DB state divergence

```
Is OPS_VIEW_DB_WRITE=true?
├── YES → Set OPS_VIEW_DB_WRITE=false → Restart server
│         └── Writes revert to localStorage-only
│         └── Any DB writes already committed remain in DB
│         └── Strict mode prevents orphaned local state
└── NO  → Issue is unrelated to v2.54.1 DB write path
```

**Recovery time:** Immediate  
**Data impact:** Committed DB writes remain; no automatic reconciliation needed

### 5.3 RBAC Filtering Mismatches

**Symptoms:** Analyst sees items they shouldn't, verifier sees empty queue, role mismatch between queue and list endpoints

```
Are role-scoped endpoints returning wrong data?
├── Check 1: Verify user's workspace role
│   SELECT role FROM user_workspace_roles WHERE user_id = ? AND workspace_id = ?;
├── Check 2: Verify resolve_effective_role() behavior
│   └── Sandbox mode: X-Effective-Role header being sent?
│   └── Real mode: DB role present in user_workspace_roles?
├── Check 3: Query counts match expectations?
│   └── Analyst: only own items (author_id/created_by = user_id)
│   └── Verifier/Admin: workspace-wide
└── If mismatch confirmed:
    └── No flag rollback needed — role filtering is always-on
    └── Fix is code-level in server/role_scope.py
    └── Temporary workaround: assign higher role to affected user
```

### 5.4 Stale-Version Spikes (409 Rate)

**Symptoms:** High rate of 409 STALE_VERSION responses, users unable to update items

```
409 rate > 5% of write operations?
├── YES → Check for concurrent modification patterns
│         └── Multiple users editing same item?
│         └── Frontend not refreshing version after read?
│         └── Temporary: increase client retry logic
│         └── If systemic: Set OPS_VIEW_DB_WRITE=false
└── NO  → Normal optimistic concurrency behavior
```

---

## 6. Post-Migration Verification

After applying migrations, verify:

```sql
-- 012: rfis.batch_id column exists
SELECT column_name FROM information_schema.columns
WHERE table_name = 'rfis' AND column_name = 'batch_id';

-- 012: Indexes created
SELECT indexname FROM pg_indexes
WHERE indexname IN ('idx_rfis_batch', 'idx_rfis_custody', 'idx_patches_batch', 'idx_patches_record', 'idx_corrections_ws_status');

-- 013: Drive source allowed
INSERT INTO batches (id, workspace_id, name, source) VALUES ('test_013', 'ws_test', 'test', 'drive');
DELETE FROM batches WHERE id = 'test_013';

-- 013: Dedupe index exists
SELECT indexname FROM pg_indexes WHERE indexname = 'idx_batches_drive_dedupe';
```

---

## 7. Server Restart Sequence

1. Apply migrations 012, 013 (if not already applied)
2. Set environment flags to desired stage (see Cutover Plan)
3. Restart server: `python -m uvicorn server.pdf_proxy:app --host 0.0.0.0 --port 5000`
4. Verify health endpoint responds
5. Run workspace-scoped smoke test (see Cutover Plan)

---

## 8. Rollback Without Schema Rollback

The v2.54.1 release is designed so that **full behavioral rollback is achievable via feature flags alone**, without reversing database migrations:

- Migrations 012/013 are additive only (new columns, indexes, constraints)
- Setting both `OPS_VIEW_DB_READ=false` and `OPS_VIEW_DB_WRITE=false` returns the system to pre-v2.54.1 behavior
- Role-scoped filtering on list endpoints is always-on but backward-compatible (verifier/admin see the same data as before)
- The only behavioral change that cannot be flag-toggled is analyst visibility restriction on list endpoints — this is considered a security improvement, not a regression
