# V2.54 Role Model Update

**Version:** 2.54  
**Date:** 2026-02-17  
**Status:** LOCKED — Clarity Phase  
**Scope:** Position roles vs. capability roles; verifier position role; lead analyst capability model  

---

## 1. Current Role Model

### 1.1 Position Roles (Existing)

The current system uses a flat position-based role hierarchy defined in:
- **Schema:** `user_workspace_roles.role` CHECK constraint (migration 001, L30)
- **Enforcement:** `ROLE_HIERARCHY` dict (patches.py L51)

| Position Role | Hierarchy Level | Description |
|---------------|----------------|-------------|
| `analyst` | 0 | Creates patches, responds to RFIs, submits corrections. Cannot approve. |
| `verifier` | 1 | Reviews and approves/rejects patches. Manages RFI custody. Cannot promote to Applied. |
| `admin` | 2 | Final approval authority. Promotes patches to Applied. Manages workspace settings. |
| `architect` | 3 | System-level access. Schema and rule management. |

**Hierarchy rule:** A role at level N can perform all actions permitted at levels 0..N. An admin can do everything a verifier can do, and a verifier can do everything an analyst can do.

### 1.2 Assignment Model

- One user gets exactly ONE position role per workspace (PK: `user_id, workspace_id`)
- Granted by another user (`granted_by` FK)
- No expiration mechanism currently exists
- Role check: `_check_role(user_id, workspace_id, min_role, conn)` in patches.py L74–86

### 1.3 Current Enforcement Points

| Enforcement | File | Line | Mechanism |
|-------------|------|------|-----------|
| Patch status transition | patches.py | L26–48 | Transition matrix with `min_role`, `author_only`, `self_approval_check` |
| Role hierarchy check | patches.py | L51, L74–86 | `ROLE_HIERARCHY` dict + `_check_role()` function |
| Self-approval block | patches.py | L358–365 | Server-enforced: author cannot approve own patch |
| RFI custody transition | rfis.py | L20–26 | Custody transition matrix with role allowances |
| Correction approval | corrections.py | L280–291 | Role check for `verifier` or higher |
| Workspace membership | (all routes) | (various) | `_check_role()` returns error if no role in workspace |

---

## 2. Position Roles vs. Capability Roles

### 2.1 Concept

The V2.54 role model distinguishes two orthogonal axes:

**Position roles** answer: "What is this person's job title/level in this workspace?"
- Determines the hierarchy level for governance actions
- Exactly one per user per workspace
- Examples: analyst, verifier, admin, architect

**Capability roles** answer: "What extra powers does this person have beyond their position?"
- Grants specific abilities that are NOT inherent to the position
- Zero or more per user per workspace
- Examples: `CAN_ASSIGN_WORK`, `CAN_MANAGE_GLOSSARY`, `CAN_EXPORT_DRIVE`

### 2.2 Why This Distinction Matters

The current system has an implicit assumption: "analyst" is a homogeneous role. But in practice, some analysts are "lead analysts" who:
- Assign work items to other analysts
- Manage batch intake and triage
- Set up contract configurations
- But do NOT have verifier-level approval authority

Without capability roles, the only way to give a lead analyst work assignment powers is to promote them to `verifier` — which also gives them approval authority they shouldn't have.

---

## 3. Proposed Model

### 3.1 Position Roles (No Changes to Existing)

| Position Role | Level | Unchanged Governance Powers |
|---------------|-------|-----------------------------|
| `analyst` | 0 | Create patches, respond to RFIs, submit corrections, cancel own patches |
| `verifier` | 1 | All analyst powers + approve/reject patches, manage RFI custody, approve/reject corrections |
| `admin` | 2 | All verifier powers + final approval, promote to Applied, manage workspace settings, manage members |
| `architect` | 3 | All admin powers + schema management, rule configuration, system settings |

### 3.2 Capability Grants (New Layer)

| Capability | Code | Description | Typical Position |
|------------|------|-------------|-----------------|
| `CAN_ASSIGN_WORK` | `cap:assign_work` | Assign triage items, batches, and RFIs to specific analysts | Lead Analyst |
| `CAN_MANAGE_GLOSSARY` | `cap:manage_glossary` | Create/edit/delete glossary terms and aliases | Lead Analyst, Admin |
| `CAN_EXPORT_DRIVE` | `cap:export_drive` | Trigger Google Drive XLSX exports | Analyst (with permission), Admin |
| `CAN_BULK_IMPORT` | `cap:bulk_import` | Import CSV/XLSX workbooks into batches | Lead Analyst, Admin |
| `CAN_VIEW_AUDIT` | `cap:view_audit` | Access full audit event log | Verifier, Admin |
| `CAN_MANAGE_API_KEYS` | `cap:manage_api_keys` | Create/revoke API keys for service ingestion | Admin |

### 3.3 Lead Analyst Model

A "Lead Analyst" is NOT a new position role. It is an analyst with one or more capability grants:

```
Position: analyst (level 0)
Capabilities: [CAN_ASSIGN_WORK, CAN_BULK_IMPORT, CAN_MANAGE_GLOSSARY]
```

This means:
- They CANNOT approve patches (that requires `verifier` position)
- They CAN assign work to other analysts
- They CAN import workbooks and manage the glossary
- They are displayed in the UI with a "Lead" badge for clarity

### 3.4 Verifier Position Role (Clarification)

The `verifier` position role is specifically designed for the Operations View workflow:

**Core responsibilities:**
1. Review patches in `Submitted` and `Verifier_Responded` status
2. Approve (transition to `Verifier_Approved`) or reject patches
3. Manage RFI custody: accept, return to analyst, resolve, or dismiss
4. Approve or reject corrections in `pending_verifier` status
5. Add annotations (notes, flags, questions) to records and patches

**Constraints:**
- Cannot self-approve (server-enforced via `self_approval_check`)
- Cannot promote patches beyond `Verifier_Approved` (requires admin)
- Cannot manage workspace settings or members (requires admin)

**Operations View scope:**
- Verifier sees a multi-batch queue of all items awaiting their action
- Queue is filtered by `custody_owner_role = 'verifier'` for RFIs, `status IN (Submitted, Verifier_Responded)` for patches, and `status = 'pending_verifier'` for corrections

---

## 4. Schema Design (Proposed)

### 4.1 New Table: `user_capabilities`

```sql
CREATE TABLE IF NOT EXISTS user_capabilities (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    capability TEXT NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by TEXT REFERENCES users(id),
    revoked_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT uq_user_cap UNIQUE (user_id, workspace_id, capability)
);
CREATE INDEX IF NOT EXISTS idx_user_cap_workspace ON user_capabilities(workspace_id);
CREATE INDEX IF NOT EXISTS idx_user_cap_user ON user_capabilities(user_id, workspace_id);
```

### 4.2 Capability Check Function

```python
def _check_capability(user_id, workspace_id, capability, conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM user_capabilities "
            "WHERE user_id = %s AND workspace_id = %s AND capability = %s "
            "AND revoked_at IS NULL",
            (user_id, workspace_id, capability)
        )
        return cur.fetchone() is not None
```

### 4.3 Role Display Logic

The UI should display position badges with capability indicators:

| Position | Capabilities | Display |
|----------|-------------|---------|
| analyst | (none) | `Analyst` |
| analyst | CAN_ASSIGN_WORK | `Lead Analyst` |
| analyst | CAN_ASSIGN_WORK + CAN_BULK_IMPORT | `Lead Analyst` |
| verifier | (none) | `Verifier` |
| admin | (inherits all) | `Admin` |

---

## 5. Migration Path

### 5.1 Phase 1: Position Roles Only (Current V2.5)

No changes required. The existing `user_workspace_roles` table and `ROLE_HIERARCHY` dict continue to work exactly as they do today.

### 5.2 Phase 2: Capability Grants (Future V2.6+)

1. Add migration `012_user_capabilities.sql` with the `user_capabilities` table
2. Add `_check_capability()` utility function
3. Retrofit endpoints that need capability checks (e.g., glossary management, Drive export)
4. Add admin UI for granting/revoking capabilities

### 5.3 Backward Compatibility

- No changes to the `user_workspace_roles` table
- No changes to the `ROLE_HIERARCHY` dict
- No changes to existing transition matrices
- Capability checks are purely additive — they gate NEW functionality, not existing flows
- If `user_capabilities` table doesn't exist, all capability checks default to position-role-based fallback (admin gets all capabilities, verifier gets CAN_VIEW_AUDIT, analyst gets none)

---

## 6. Operations View RBAC

### 6.1 Endpoint Access Control

| Endpoint | Min Position Role | Capability Required |
|----------|-------------------|---------------------|
| `GET /workspaces/{ws}/verifier/queue` | `verifier` | None |
| `PATCH /patches/{id}` (approve/reject) | `verifier` | None |
| `PATCH /rfis/{id}` (custody transition) | Depends on transition direction | None |
| `PATCH /corrections/{id}` (approve/reject) | `verifier` | None |
| `POST /workspaces/{ws}/annotations` | `analyst` | None |
| `GET /batches/{bat}/health` | `analyst` | None |
| Assign work to analyst | `analyst` | `CAN_ASSIGN_WORK` |
| Import workbook | `analyst` | `CAN_BULK_IMPORT` |
| Export to Drive | `analyst` | `CAN_EXPORT_DRIVE` |

### 6.2 Self-Approval Invariant

The no-self-approval rule is enforced at the server level (patches.py L358–365) and MUST remain server-enforced. The UI also checks (`vrApprove` L44336–44339 in index.html), but the client check is a convenience — the server is the authority.

---

*End of V2.54 Role Model Update*
