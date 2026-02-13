-- Migration 005: Evidence Inspector v2.51
-- Adds: anchors, corrections, reader_node_cache, ocr_escalations tables
-- Modifies: rfis (adds custody_status column)
-- Rollback: DROP TABLE anchors, corrections, reader_node_cache, ocr_escalations;
--           ALTER TABLE rfis DROP COLUMN IF EXISTS custody_status;

-- 1. Add custody_status to existing rfis table (additive, nullable)
ALTER TABLE rfis ADD COLUMN IF NOT EXISTS custody_status TEXT;

-- Backfill custody_status from existing status values
UPDATE rfis SET custody_status = CASE
    WHEN status = 'open' THEN 'open'
    WHEN status = 'responded' THEN 'awaiting_verifier'
    WHEN status = 'closed' THEN 'resolved'
    ELSE 'open'
END
WHERE custody_status IS NULL;

-- 2. Anchors table — document-level text anchors with fingerprint dedup
CREATE TABLE IF NOT EXISTS anchors (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    anchor_fingerprint TEXT NOT NULL,
    node_id TEXT,
    char_start INTEGER,
    char_end INTEGER,
    selected_text TEXT,
    field_id TEXT,
    field_key TEXT,
    page_number INTEGER,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT anchors_fingerprint_unique UNIQUE (anchor_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_anchors_document_id ON anchors(document_id);
CREATE INDEX IF NOT EXISTS idx_anchors_workspace_id ON anchors(workspace_id);
CREATE INDEX IF NOT EXISTS idx_anchors_field_id ON anchors(field_id);

-- 3. Corrections table — field-level corrections linked to anchors/RFIs
CREATE TABLE IF NOT EXISTS corrections (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    anchor_id TEXT REFERENCES anchors(id),
    rfi_id TEXT REFERENCES rfis(id),
    field_id TEXT,
    field_key TEXT,
    original_value TEXT,
    corrected_value TEXT,
    correction_type TEXT NOT NULL DEFAULT 'non_trivial',
    status TEXT NOT NULL DEFAULT 'pending_verifier',
    decided_by TEXT,
    decided_at TIMESTAMPTZ,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_corrections_document_id ON corrections(document_id);
CREATE INDEX IF NOT EXISTS idx_corrections_workspace_id ON corrections(workspace_id);
CREATE INDEX IF NOT EXISTS idx_corrections_status ON corrections(status);
CREATE INDEX IF NOT EXISTS idx_corrections_anchor_id ON corrections(anchor_id);

-- 4. Reader node cache — cached text extraction results per document
CREATE TABLE IF NOT EXISTS reader_node_cache (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    source_pdf_hash TEXT NOT NULL,
    ocr_version TEXT NOT NULL DEFAULT 'v1',
    quality_flag TEXT NOT NULL DEFAULT 'ok',
    nodes JSONB NOT NULL DEFAULT '[]'::jsonb,
    page_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT reader_cache_key UNIQUE (document_id, source_pdf_hash, ocr_version)
);

CREATE INDEX IF NOT EXISTS idx_reader_cache_document_id ON reader_node_cache(document_id);

-- 5. OCR escalations — mock/stub table for future OCR pipeline
CREATE TABLE IF NOT EXISTS ocr_escalations (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    escalation_type TEXT NOT NULL DEFAULT 'ocr_reprocess',
    status TEXT NOT NULL DEFAULT 'pending',
    requested_by TEXT,
    resolved_by TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_ocr_escalations_document_id ON ocr_escalations(document_id);
CREATE INDEX IF NOT EXISTS idx_ocr_escalations_workspace_id ON ocr_escalations(workspace_id);
