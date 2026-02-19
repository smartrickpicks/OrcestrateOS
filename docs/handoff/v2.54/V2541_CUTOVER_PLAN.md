# V2.54.1 — Cutover Plan (Flag Sequencing)

**Version:** v2.54.1  
**Date:** 2026-02-17  
**Status:** Ready for staged rollout

---

## 1. Rollout Strategy

Progressive enablement via two feature flags. Each stage has explicit entry criteria, exit criteria, and abort conditions.

```
Baseline (current)     Stage A (Read)          Stage B (Read+Write)
DB_READ=false    ───►  DB_READ=true     ───►   DB_READ=true
DB_WRITE=false         DB_WRITE=false          DB_WRITE=true
```

**Minimum soak time between stages:** 24 hours (or 1 full business cycle)

---

## 2. Stage A — DB Read Enabled

### 2.1 Configuration

```env
OPS_VIEW_DB_READ=true
OPS_VIEW_DB_WRITE=false
```

### 2.2 Entry Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| A1 | Migrations 012 + 013 applied successfully | SQL verification queries (see Release Runbook §6) |
| A2 | Server restarted with flags set | Check process env or `/api/v2.5/feature-flags` |
| A3 | Database contains valid operations data | `SELECT count(*) FROM patches WHERE workspace_id = ?` returns > 0 |
| A4 | At least one admin user exists in workspace | `SELECT * FROM user_workspace_roles WHERE role = 'admin'` |

### 2.3 Smoke Procedure

Run these checks within 15 minutes of enabling Stage A:

```bash
WS="<workspace_id>"
ADMIN_TOKEN="<admin_user_id>"
ANALYST_TOKEN="<analyst_user_id>"

# 1. Queue loads from DB (admin sees full workspace)
curl -s "http://localhost:5000/api/v2.5/workspaces/$WS/operations/queue" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('Queue total:', d['data']['counts']['total'])
assert d['data']['counts']['total'] > 0, 'FAIL: empty queue'
print('PASS')
"

# 2. Role-scoped: analyst sees own only
curl -s "http://localhost:5000/api/v2.5/workspaces/$WS/patches" \
  -H "Authorization: Bearer $ANALYST_TOKEN" | python3 -c "
import sys,json; d=json.load(sys.stdin)
items = d.get('data', [])
own = all(i['author_id'] == '<analyst_user_id>' for i in items)
print(f'Analyst patches: {len(items)}, all_own: {own}')
assert own, 'FAIL: analyst sees others items'
print('PASS')
"

# 3. No 500 errors in last 5 minutes
# Check server logs for ERROR level entries

# 4. Response times normal (< 500ms for queue endpoint)
curl -s -w "\ntime_total: %{time_total}\n" \
  "http://localhost:5000/api/v2.5/workspaces/$WS/operations/queue" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -o /dev/null
```

### 2.4 Exit Criteria (to proceed to Stage B)

| # | Criterion | Threshold |
|---|-----------|-----------|
| E1 | Zero 500-level errors on queue/list endpoints | 0 in 24h |
| E2 | Queue data matches expected workspace counts | ±5% of known items |
| E3 | Role-scoped filtering verified for all roles | Analyst, Verifier, Admin |
| E4 | No user-reported data visibility anomalies | 0 reports |
| E5 | Response time p95 < 500ms on queue endpoint | Measured over soak period |

### 2.5 Abort Criteria

| Condition | Action |
|-----------|--------|
| Any 500 on `/operations/queue` | Set `OPS_VIEW_DB_READ=false`, restart |
| Queue returns empty for admin | Set `OPS_VIEW_DB_READ=false`, investigate DB connectivity |
| Analyst sees other users' items | Investigate `role_scope.py`, no flag change needed |
| Response time p95 > 2s | Set `OPS_VIEW_DB_READ=false`, investigate query performance |

---

## 3. Stage B — DB Read + Write Enabled

### 3.1 Configuration

```env
OPS_VIEW_DB_READ=true
OPS_VIEW_DB_WRITE=true
```

### 3.2 Entry Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| B1 | Stage A exit criteria all met | Review soak period metrics |
| B2 | Minimum 24h soak at Stage A | Timestamp check |
| B3 | No open incidents from Stage A | Incident tracker clear |
| B4 | Backup/checkpoint taken | Replit checkpoint or DB snapshot |

### 3.3 Smoke Procedure

Run these checks within 15 minutes of enabling Stage B:

```bash
WS="<workspace_id>"
ANALYST_TOKEN="<analyst_user_id>"
VERIFIER_TOKEN="<verifier_user_id>"

# 1. Create and transition a test patch
PAT=$(curl -s -X POST "http://localhost:5000/api/v2.5/workspaces/$WS/patches" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ANALYST_TOKEN" \
  -d '{"record_id": "rec_smoke_b", "field_key": "title", "intent": "stage B smoke"}')
PAT_ID=$(echo "$PAT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
PAT_VER=$(echo "$PAT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['version'])")
echo "Created patch: $PAT_ID v$PAT_VER"

# Submit it (DB write path)
curl -s -X PATCH "http://localhost:5000/api/v2.5/patches/$PAT_ID" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ANALYST_TOKEN" \
  -d "{\"status\": \"Submitted\", \"version\": $PAT_VER}" | python3 -c "
import sys,json; d=json.load(sys.stdin)
assert d['data']['version'] > $PAT_VER, 'FAIL: version not bumped'
print('PASS: Patch submitted, version bumped')
"

# 2. Create and transition a test RFI (custody matrix)
RFI=$(curl -s -X POST "http://localhost:5000/api/v2.5/workspaces/$WS/rfis" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ANALYST_TOKEN" \
  -d '{"question": "Stage B smoke?", "target_record_id": "rec_smoke_b"}')
RFI_ID=$(echo "$RFI" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
RFI_VER=$(echo "$RFI" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['version'])")

# Analyst: open -> awaiting_verifier
curl -s -X PATCH "http://localhost:5000/api/v2.5/rfis/$RFI_ID" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ANALYST_TOKEN" \
  -d "{\"custody_status\": \"awaiting_verifier\", \"version\": $RFI_VER}" | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('PASS: RFI sent to verifier, v=%d' % d['data']['version'])
"

# 3. Verify 409 on stale version (optimistic concurrency)
curl -s -w "\n%{http_code}" -X PATCH "http://localhost:5000/api/v2.5/rfis/$RFI_ID" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $VERIFIER_TOKEN" \
  -d '{"custody_status": "resolved", "version": 1}' | tail -1 | python3 -c "
import sys; code=sys.stdin.read().strip()
assert code == '409', f'FAIL: expected 409, got {code}'
print('PASS: Stale version correctly rejected (409)')
"

# 4. Verify audit trail
python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"SELECT count(*) FROM audit_events WHERE timestamp_iso > now() - interval '10 minutes'\")
count = cur.fetchone()[0]
conn.close()
assert count > 0, 'FAIL: no recent audit events'
print(f'PASS: {count} audit events in last 10 minutes')
"
```

### 3.4 Exit Criteria (production stable)

| # | Criterion | Threshold |
|---|-----------|-----------|
| F1 | Zero 500-level errors on write endpoints | 0 in 48h |
| F2 | 409 STALE_VERSION rate < 5% of writes | Measured over soak period |
| F3 | All custody transitions produce audit events | Spot-check 10 transitions |
| F4 | No local/DB state divergence reports | 0 reports in 48h |
| F5 | Drive dedupe correctly prevents duplicate batches | Test with same file+revision |

### 3.5 Abort Criteria

| Condition | Action |
|-----------|--------|
| Any 500 on write endpoints | Set `OPS_VIEW_DB_WRITE=false`, restart, investigate |
| 409 rate > 10% of writes | Set `OPS_VIEW_DB_WRITE=false`, check for version sync issues |
| Local/DB state divergence detected | Set `OPS_VIEW_DB_WRITE=false`, reconcile manually |
| Audit events missing for transitions | Investigate audit_events table, check logging |

---

## 4. Rollback Quick Reference

| Scenario | Action | Recovery Time |
|----------|--------|---------------|
| Stage A issues | `OPS_VIEW_DB_READ=false` + restart | < 2 minutes |
| Stage B issues | `OPS_VIEW_DB_WRITE=false` + restart | < 2 minutes |
| Full rollback | Both flags `false` + restart | < 2 minutes |
| Schema rollback | See Release Runbook §3.1/3.2 rollback SQL | < 10 minutes |

**Key principle:** Flag rollback restores pre-v2.54.1 behavior without schema changes. Migrations 012/013 are additive and safe to leave in place.

---

## 5. Communication Plan

| When | Who | What |
|------|-----|------|
| Before Stage A | Ops team | Notify: "Enabling DB read for operations queue. No user-facing changes expected." |
| Stage A +24h | Ops team | Status update: soak metrics summary |
| Before Stage B | Ops team + stakeholders | Notify: "Enabling DB writes. Status transitions will persist to database." |
| Stage B +48h | All | Release announcement: v2.54.1 fully enabled |
| If rollback | Ops team + stakeholders | Incident notification with scope and ETA |
