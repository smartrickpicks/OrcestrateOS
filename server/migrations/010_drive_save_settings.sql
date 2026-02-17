-- V25-DRV-SAVE: Workspace Drive save settings for role-based folder routing
-- Stores per-workspace folder IDs for Drive export routing

CREATE TABLE IF NOT EXISTS workspace_drive_settings (
    workspace_id TEXT PRIMARY KEY REFERENCES workspaces(id),
    root_folder_id TEXT,
    verifier_folder_id TEXT,
    admin_folder_id TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT REFERENCES users(id)
);

-- Drive export history — tracks every save-to-drive with role routing context
CREATE TABLE IF NOT EXISTS drive_export_history (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    batch_id TEXT,
    file_name TEXT NOT NULL,
    drive_file_id TEXT NOT NULL,
    folder_id TEXT,
    web_view_link TEXT,
    status TEXT NOT NULL,
    actor_id TEXT REFERENCES users(id),
    actor_role TEXT,
    note TEXT,
    size_bytes BIGINT,
    exported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_drive_export_ws ON drive_export_history(workspace_id);
CREATE INDEX IF NOT EXISTS idx_drive_export_batch ON drive_export_history(workspace_id, batch_id);
