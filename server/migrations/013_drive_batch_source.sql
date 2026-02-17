-- Migration 013: Add 'drive' to batches source check constraint (VER2-08)
-- and partial unique index for drive dedupe concurrency safety (VER2-09)
ALTER TABLE batches DROP CONSTRAINT IF EXISTS batches_source_check;
ALTER TABLE batches ADD CONSTRAINT batches_source_check
  CHECK (source = ANY (ARRAY['upload'::text, 'merge'::text, 'import'::text, 'drive'::text]));

CREATE UNIQUE INDEX IF NOT EXISTS idx_batches_drive_dedupe
  ON batches (workspace_id, (metadata->>'drive_file_id'), (metadata->>'revision_marker'))
  WHERE source = 'drive' AND deleted_at IS NULL
    AND metadata->>'drive_file_id' IS NOT NULL
    AND metadata->>'revision_marker' IS NOT NULL;
