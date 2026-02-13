-- V25-AUTH: Add Google OAuth support columns and seed real users
-- Adds status and google_sub to users table for OAuth login gating

-- Add status column (active/inactive) to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive'));

-- Add google_sub column for Google OIDC subject identifier matching
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub TEXT UNIQUE;

-- Seed 10 real createmusicgroup.com users
-- Using ULID-prefixed IDs per project convention
INSERT INTO users (id, email, display_name, status) VALUES
    ('usr_01KMCG0100000000000000KYLE', 'kylepatrick.go@createmusicgroup.com', 'Kyle Patrick', 'active'),
    ('usr_01KMCG0200000000000000AIVN', 'aivan.bolambao@createmusicgroup.com', 'Aivan Bolambao', 'active'),
    ('usr_01KMCG0300000000000000NOAH', 'noah.bender@createmusicgroup.com', 'Noah Bender', 'active'),
    ('usr_01KMCG0400000000000000FRAN', 'francisco.degrano@createmusicgroup.com', 'Francisco Degrano', 'active'),
    ('usr_01KMCG0500000000000000EDDI', 'eddie.jauregui@createmusicgroup.com', 'Eddie Jauregui', 'active'),
    ('usr_01KMCG0600000000000000ASWN', 'aswin.ravi@createmusicgroup.com', 'Aswin.Ravi', 'active'),
    ('usr_01KMCG0700000000000000ZACH', 'zachary.holwerda@createmusicgroup.com', 'Zachary Holwerda', 'active'),
    ('usr_01KMCG0800000000000000CEER', 'cyril@createmusicgroup.com', 'Cee Rouhana', 'active'),
    ('usr_01KMCG0900000000000000DIAN', 'diana.cuevas@createmusicgroup.com', 'Diana Cuevas', 'active')
ON CONFLICT (email) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    status = EXCLUDED.status;

-- Ensure the production workspace exists (independent of seed data)
INSERT INTO workspaces (id, name, mode) VALUES
    ('ws_SEED0100000000000000000000', 'Production', 'production')
ON CONFLICT (id) DO NOTHING;

-- Assign workspace roles
INSERT INTO user_workspace_roles (user_id, workspace_id, role) VALUES
    ('usr_01KMCG0100000000000000KYLE', 'ws_SEED0100000000000000000000', 'analyst'),
    ('usr_01KMCG0200000000000000AIVN', 'ws_SEED0100000000000000000000', 'analyst'),
    ('usr_01KMCG0300000000000000NOAH', 'ws_SEED0100000000000000000000', 'analyst'),
    ('usr_01KMCG0400000000000000FRAN', 'ws_SEED0100000000000000000000', 'analyst'),
    ('usr_01KMCG0500000000000000EDDI', 'ws_SEED0100000000000000000000', 'admin'),
    ('usr_01KMCG0600000000000000ASWN', 'ws_SEED0100000000000000000000', 'analyst'),
    ('usr_01KMCG0700000000000000ZACH', 'ws_SEED0100000000000000000000', 'admin'),
    ('usr_01KMCG0800000000000000CEER', 'ws_SEED0100000000000000000000', 'verifier'),
    ('usr_01KMCG0900000000000000DIAN', 'ws_SEED0100000000000000000000', 'verifier')
ON CONFLICT (user_id, workspace_id) DO UPDATE SET role = EXCLUDED.role;
