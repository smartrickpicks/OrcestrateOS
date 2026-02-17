-- Migration 012: Operations View v2.54
-- Adds batch_id to rfis for direct batch-scoped queries,
-- backfills from linked patches, and adds indexes for Operations View performance.

-- 1. Add nullable batch_id column to rfis
ALTER TABLE rfis ADD COLUMN IF NOT EXISTS batch_id TEXT REFERENCES batches(id);

-- 2. Backfill rfis.batch_id from linked patches (deterministic linkage)
UPDATE rfis
SET batch_id = p.batch_id
FROM patches p
WHERE rfis.patch_id = p.id
  AND rfis.batch_id IS NULL
  AND p.batch_id IS NOT NULL;

-- 3. Indexes for Operations View performance
CREATE INDEX IF NOT EXISTS idx_rfis_batch ON rfis(workspace_id, batch_id);
CREATE INDEX IF NOT EXISTS idx_rfis_custody ON rfis(workspace_id, custody_status);
CREATE INDEX IF NOT EXISTS idx_patches_batch ON patches(workspace_id, batch_id);
CREATE INDEX IF NOT EXISTS idx_patches_record ON patches(workspace_id, record_id);
CREATE INDEX IF NOT EXISTS idx_corrections_ws_status ON corrections(workspace_id, status);
