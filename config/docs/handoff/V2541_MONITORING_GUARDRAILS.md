# V2.54.1 — Monitoring & Ops Guardrails

**Version:** v2.54.1  
**Date:** 2026-02-17  
**Scope:** Metrics, thresholds, triage playbook

---

## 1. Key Metrics

### 1.1 Error Rate by Endpoint

| Metric | Endpoints | Source | Collection Method |
|--------|-----------|--------|-------------------|
| 401 rate | All `/api/v2.5/workspaces/*/` endpoints | Server logs | `grep "HTTP 401" uvicorn.log \| wc -l` |
| 403 rate | All `/api/v2.5/workspaces/*/` endpoints | Server logs | `grep "HTTP 403" uvicorn.log \| wc -l` |
| 409 rate | `PATCH /patches/{id}`, `PATCH /rfis/{id}`, `PATCH /corrections/{id}` | Server logs | `grep "HTTP 409" uvicorn.log \| wc -l` |
| 500 rate | All endpoints | Server logs | `grep "HTTP 500" uvicorn.log \| wc -l` |

### 1.2 STALE_VERSION Rate

Track optimistic concurrency conflicts as a percentage of total write operations:

```sql
SELECT
  date_trunc('hour', timestamp_iso) AS hour,
  count(*) FILTER (WHERE event_type LIKE '%.updated') AS total_writes,
  count(*) FILTER (WHERE metadata->>'error_code' = 'STALE_VERSION') AS stale_conflicts,
  ROUND(
    100.0 * count(*) FILTER (WHERE metadata->>'error_code' = 'STALE_VERSION')
    / NULLIF(count(*) FILTER (WHERE event_type LIKE '%.updated'), 0),
    2
  ) AS conflict_pct
FROM audit_events
WHERE timestamp_iso > now() - interval '24 hours'
GROUP BY 1 ORDER BY 1;
```

### 1.3 Queue Count Deltas by Role

Verify role-scoped visibility is consistent:

```sql
-- Compare total items visible to each role level
-- Analyst count (own items only for a specific user)
SELECT 'analyst' AS role, count(*) FROM patches
WHERE workspace_id = '<ws_id>' AND author_id = '<analyst_user_id>';

-- Verifier/Admin count (workspace-wide)
SELECT 'admin' AS role, count(*) FROM patches
WHERE workspace_id = '<ws_id>';
```

**Expected:** Admin count >= Verifier count >= Analyst count (for any given analyst)

### 1.4 Drive Dedupe Hit Rate

```sql
SELECT
  date_trunc('day', created_at) AS day,
  count(*) FILTER (WHERE source = 'drive') AS drive_batches,
  count(*) FILTER (WHERE source = 'drive' AND metadata->>'dedupe_hit' = 'true') AS dedupe_hits
FROM batches
WHERE created_at > now() - interval '7 days'
GROUP BY 1 ORDER BY 1;
```

Alternatively, check audit events:

```sql
SELECT count(*) FROM audit_events
WHERE event_type = 'batch.dedupe_hit'
AND timestamp_iso > now() - interval '24 hours';
```

---

## 2. Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| 500 rate (any endpoint) | > 0 in 1h | > 5 in 1h | Investigate immediately; consider flag rollback |
| 403 rate (authenticated users) | > 10 in 1h | > 50 in 1h | Check role assignments; verify `role_scope.py` |
| 409 STALE_VERSION rate | > 5% of writes | > 15% of writes | Check for concurrent edit patterns; review client version refresh |
| Queue load time p95 | > 1s | > 3s | Check DB indexes; verify 012 migration applied |
| Analyst sees others' items | Any occurrence | — | Immediate investigation; security issue |
| Empty queue for admin | Any occurrence when data exists | — | Check DB_READ flag; verify DB connectivity |

---

## 3. Triage Playbook

### 3.1 High 401 Rate

**Likely causes:**
- OAuth token expiry not handled by client
- API key rotation without client update
- Sandbox mode headers not sent correctly

**Steps:**
1. Check which users are hitting 401: `grep "401" server.log | awk '{print $NF}'`
2. Verify user exists: `SELECT id, email FROM users WHERE id = '<user_id>'`
3. Check if token/session is valid in auth middleware
4. If sandbox: verify `X-Sandbox-Mode` header is `"true"` (case-insensitive)

### 3.2 High 403 Rate

**Likely causes:**
- User not assigned to workspace
- Role downgrade without cache clear
- Sandbox role simulation by non-admin

**Steps:**
1. Identify affected user: `SELECT * FROM user_workspace_roles WHERE user_id = '<id>'`
2. Verify workspace membership exists
3. Check if sandbox mode: admin/architect required for role simulation
4. If role was recently changed, verify `feature_flags.clear_cache()` or server restart

### 3.3 STALE_VERSION Spike

**Likely causes:**
- Multiple users editing same item concurrently
- Frontend not refreshing version from server response
- Network retries submitting stale versions

**Steps:**
1. Identify affected items:
   ```sql
   SELECT metadata->>'resource_id', count(*)
   FROM audit_events
   WHERE metadata->>'error_code' = 'STALE_VERSION'
   AND timestamp_iso > now() - interval '1 hour'
   GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
   ```
2. Check if single item is hotspot (concurrent edits)
3. Verify client reads version from PATCH response and uses it for next write
4. If systemic: temporarily set `OPS_VIEW_DB_WRITE=false`

### 3.4 Role Visibility Mismatch

**Symptoms:** Analyst sees workspace-wide data, or verifier sees empty queue

**Steps:**
1. Verify user's DB role:
   ```sql
   SELECT role FROM user_workspace_roles WHERE user_id = '<id>' AND workspace_id = '<ws>';
   ```
2. Test endpoint directly:
   ```bash
   curl -s "http://localhost:5000/api/v2.5/workspaces/<ws>/patches" \
     -H "Authorization: Bearer <user_id>" | python3 -c "
   import sys,json; d=json.load(sys.stdin)
   print('Count:', len(d['data']))
   for i in d['data'][:3]: print('  author:', i.get('author_id'))
   "
   ```
3. Check `resolve_effective_role()` return value via debug logging
4. If sandbox: verify `X-Effective-Role` matches expected simulation

### 3.5 Drive Dedupe Not Working

**Symptoms:** Duplicate batches created from same Drive file

**Steps:**
1. Check if index exists:
   ```sql
   SELECT indexname FROM pg_indexes WHERE indexname = 'idx_batches_drive_dedupe';
   ```
2. Verify metadata fields populated:
   ```sql
   SELECT id, metadata->>'drive_file_id', metadata->>'revision_marker'
   FROM batches WHERE source = 'drive' ORDER BY created_at DESC LIMIT 5;
   ```
3. Check if `deleted_at` is set (soft-deleted batches bypass dedupe)
4. Verify request includes `metadata.drive_file_id` and either `metadata.revision_id` or `metadata.modified_time`

---

## 4. Instrumentation Points

Existing server-side logging provides the primary observability layer. No additional infrastructure is required for P4.

### 4.1 Existing Log Points

| Component | Log Level | What's Logged |
|-----------|-----------|---------------|
| `server/role_scope.py` | DEBUG | Role resolution path (sandbox, DB, fallback) |
| `server/routes/rfis.py` | INFO | Custody transitions, version bumps |
| `server/routes/patches.py` | INFO | Status transitions, version bumps |
| `server/routes/batches.py` | INFO | Drive dedupe hits, batch creation |
| `server/auth.py` | WARNING | Auth failures, token issues |
| Audit events table | — | All state changes with actor, timestamp, metadata |

### 4.2 Recommended Future Instrumentation (Post-P4)

If traffic warrants, consider adding:
- Prometheus counters for HTTP status codes per endpoint
- Histogram for query latency on operations queue
- Alert webhook for critical threshold breaches

These are **not required** for v2.54.1 release — existing logging + audit table is sufficient.

---

## 5. Operational Runbook Summary

| Incident | Severity | Owner | First Response |
|----------|----------|-------|----------------|
| 500 on any v2.5 endpoint | Critical | On-call engineer | Check logs → identify root cause → flag rollback if DB-related |
| Analyst data leak (sees others' items) | Critical | On-call engineer | Verify role_scope → hotfix if needed → no flag rollback (always-on) |
| High 409 rate | Warning | On-call engineer | Check concurrent edit patterns → client-side fix or flag rollback |
| Empty queue for admin | Warning | On-call engineer | Check DB_READ flag → verify DB connectivity → restart if needed |
| Drive dedupe miss | Low | Scheduled review | Verify index exists → check metadata completeness |
