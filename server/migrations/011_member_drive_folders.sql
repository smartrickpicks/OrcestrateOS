-- V25-DRV-MEMBER: Per-member Drive folder mapping
ALTER TABLE user_workspace_roles ADD COLUMN IF NOT EXISTS drive_folder_id TEXT;
ALTER TABLE user_workspace_roles ADD COLUMN IF NOT EXISTS drive_folder_updated_at TIMESTAMPTZ;
