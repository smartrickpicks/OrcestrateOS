-- V25-102: Core Tables Migration
-- Creates all 18 tables per API v2.5 canonical spec Section 6

-- 1. workspaces
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'sandbox' CHECK (mode IN ('sandbox', 'production')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 2. users (auth-managed, not CRUD-exposed)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. user_workspace_roles
CREATE TABLE IF NOT EXISTS user_workspace_roles (
    user_id TEXT NOT NULL REFERENCES users(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    role TEXT NOT NULL CHECK (role IN ('analyst', 'verifier', 'admin', 'architect')),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by TEXT REFERENCES users(id),
    PRIMARY KEY (user_id, workspace_id)
);
CREATE INDEX IF NOT EXISTS idx_uwr_workspace ON user_workspace_roles(workspace_id);

-- 4. batches
CREATE TABLE IF NOT EXISTS batches (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    name TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'upload' CHECK (source IN ('upload', 'merge', 'import')),
    batch_fingerprint TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    record_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_batches_workspace ON batches(workspace_id);
CREATE INDEX IF NOT EXISTS idx_batches_fingerprint ON batches(batch_fingerprint);

-- 5. accounts
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL REFERENCES batches(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    account_name TEXT NOT NULL,
    billing_country TEXT,
    billing_city TEXT,
    account_fingerprint TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_accounts_workspace ON accounts(workspace_id, batch_id);
CREATE INDEX IF NOT EXISTS idx_accounts_fingerprint ON accounts(account_fingerprint);

-- 6. contracts
CREATE TABLE IF NOT EXISTS contracts (
    id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL REFERENCES batches(id),
    account_id TEXT REFERENCES accounts(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    contract_fingerprint TEXT,
    contract_id_source TEXT CHECK (contract_id_source IN ('extracted', 'url_hash', 'fallback_sig')),
    file_url TEXT,
    file_name TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    health_score INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_contracts_workspace ON contracts(workspace_id, batch_id);
CREATE INDEX IF NOT EXISTS idx_contracts_fingerprint ON contracts(contract_fingerprint);

-- 7. documents
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL REFERENCES contracts(id),
    batch_id TEXT NOT NULL REFERENCES batches(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    document_fingerprint TEXT,
    file_url TEXT,
    file_name TEXT,
    section_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_documents_workspace ON documents(workspace_id, contract_id);
CREATE INDEX IF NOT EXISTS idx_documents_fingerprint ON documents(document_fingerprint);

-- 8. patches
CREATE TABLE IF NOT EXISTS patches (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    batch_id TEXT REFERENCES batches(id),
    record_id TEXT,
    field_key TEXT,
    author_id TEXT NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'Draft' CHECK (status IN (
        'Draft', 'Submitted', 'Needs_Clarification', 'Verifier_Responded',
        'Verifier_Approved', 'Admin_Approved', 'Admin_Hold',
        'Applied', 'Rejected', 'Cancelled',
        'Sent_to_Kiwi', 'Kiwi_Returned'
    )),
    intent TEXT,
    when_clause JSONB,
    then_clause JSONB,
    because_clause TEXT,
    evidence_pack_id TEXT,
    submitted_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    file_name TEXT,
    file_url TEXT,
    before_value TEXT,
    after_value TEXT,
    history JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_patches_workspace ON patches(workspace_id);
CREATE INDEX IF NOT EXISTS idx_patches_status ON patches(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_patches_author ON patches(workspace_id, author_id);

-- 9. evidence_packs
CREATE TABLE IF NOT EXISTS evidence_packs (
    id TEXT PRIMARY KEY,
    patch_id TEXT NOT NULL REFERENCES patches(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    author_id TEXT NOT NULL REFERENCES users(id),
    blocks JSONB DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'incomplete' CHECK (status IN ('incomplete', 'complete')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_evidence_packs_workspace ON evidence_packs(workspace_id, patch_id);

-- 10. annotations
CREATE TABLE IF NOT EXISTS annotations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    author_id TEXT NOT NULL REFERENCES users(id),
    target_type TEXT NOT NULL CHECK (target_type IN ('field', 'record', 'contract', 'document')),
    target_id TEXT NOT NULL,
    content TEXT NOT NULL,
    annotation_type TEXT NOT NULL DEFAULT 'note' CHECK (annotation_type IN ('note', 'flag', 'question')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_annotations_workspace ON annotations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_annotations_target ON annotations(workspace_id, target_type, target_id);

-- 11. annotation_links
CREATE TABLE IF NOT EXISTS annotation_links (
    id TEXT PRIMARY KEY,
    annotation_id TEXT NOT NULL REFERENCES annotations(id),
    linked_type TEXT NOT NULL CHECK (linked_type IN ('patch', 'rfi', 'evidence_pack', 'selection_capture')),
    linked_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_annotation_links_annotation ON annotation_links(annotation_id);

-- 12. rfis
CREATE TABLE IF NOT EXISTS rfis (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    patch_id TEXT REFERENCES patches(id),
    author_id TEXT NOT NULL REFERENCES users(id),
    target_record_id TEXT NOT NULL,
    target_field_key TEXT,
    question TEXT NOT NULL,
    response TEXT,
    responder_id TEXT REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'responded', 'closed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_rfis_workspace ON rfis(workspace_id);
CREATE INDEX IF NOT EXISTS idx_rfis_patch ON rfis(workspace_id, patch_id);

-- 13. triage_items
CREATE TABLE IF NOT EXISTS triage_items (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    batch_id TEXT NOT NULL REFERENCES batches(id),
    record_id TEXT NOT NULL,
    field_key TEXT,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('blocker', 'warning', 'info')),
    source TEXT NOT NULL CHECK (source IN ('qa_rule', 'preflight', 'system_pass', 'manual')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_review', 'resolved', 'dismissed')),
    resolved_by TEXT REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_triage_items_workspace ON triage_items(workspace_id, batch_id);

-- 14. signals
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    batch_id TEXT NOT NULL REFERENCES batches(id),
    record_id TEXT NOT NULL,
    field_key TEXT,
    signal_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('blocker', 'warning', 'info')),
    rule_id TEXT,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_signals_workspace ON signals(workspace_id, batch_id);

-- 15. selection_captures
CREATE TABLE IF NOT EXISTS selection_captures (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    author_id TEXT NOT NULL REFERENCES users(id),
    document_id TEXT NOT NULL REFERENCES documents(id),
    field_id TEXT,
    rfi_id TEXT REFERENCES rfis(id),
    page_number INTEGER,
    coordinates JSONB,
    selected_text TEXT,
    purpose TEXT NOT NULL CHECK (purpose IN ('evidence', 'annotation', 'rfi_anchor')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_selection_captures_workspace ON selection_captures(workspace_id, document_id);

-- 16. audit_events (append-only)
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    event_type TEXT NOT NULL,
    actor_id TEXT,
    actor_role TEXT,
    timestamp_iso TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dataset_id TEXT,
    batch_id TEXT,
    record_id TEXT,
    field_key TEXT,
    patch_id TEXT,
    before_value TEXT,
    after_value TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_audit_events_workspace ON audit_events(workspace_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(workspace_id, event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor ON audit_events(workspace_id, actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(workspace_id, timestamp_iso);

-- Append-only rule: prevent UPDATE and DELETE on audit_events
CREATE OR REPLACE FUNCTION audit_events_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_events is append-only: UPDATE and DELETE are forbidden';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_events_no_update ON audit_events;
CREATE TRIGGER trg_audit_events_no_update
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION audit_events_immutable();

-- 17. api_keys
CREATE TABLE IF NOT EXISTS api_keys (
    key_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    key_hash TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by TEXT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_api_keys_workspace ON api_keys(workspace_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);

-- 18. idempotency_keys
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key_hash TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    endpoint TEXT NOT NULL,
    response JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours')
);
CREATE INDEX IF NOT EXISTS idx_idempotency_workspace ON idempotency_keys(workspace_id);
CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency_keys(expires_at);
