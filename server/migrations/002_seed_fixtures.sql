-- V25-103: Seed Fixtures
-- Deterministic dev data — only applied when SEED_DATA=true env var is set
-- All seed IDs use _SEED prefix for easy identification
-- Safe to re-run: uses INSERT ... ON CONFLICT DO NOTHING

-- 1 workspace
INSERT INTO workspaces (id, name, mode) VALUES
    ('ws_SEED0100000000000000000000', 'Demo Workspace', 'sandbox')
ON CONFLICT DO NOTHING;

-- 4 users
INSERT INTO users (id, email, display_name) VALUES
    ('usr_SEED0100000000000000000000', 'analyst@demo.orchestrate.local', 'Demo Analyst'),
    ('usr_SEED0200000000000000000000', 'verifier@demo.orchestrate.local', 'Demo Verifier'),
    ('usr_SEED0300000000000000000000', 'admin@demo.orchestrate.local', 'Demo Admin'),
    ('usr_SEED0400000000000000000000', 'architect@demo.orchestrate.local', 'Demo Architect')
ON CONFLICT DO NOTHING;

-- 4 user_workspace_roles
INSERT INTO user_workspace_roles (user_id, workspace_id, role) VALUES
    ('usr_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'analyst'),
    ('usr_SEED0200000000000000000000', 'ws_SEED0100000000000000000000', 'verifier'),
    ('usr_SEED0300000000000000000000', 'ws_SEED0100000000000000000000', 'admin'),
    ('usr_SEED0400000000000000000000', 'ws_SEED0100000000000000000000', 'architect')
ON CONFLICT DO NOTHING;

-- 1 batch
INSERT INTO batches (id, workspace_id, name, source, batch_fingerprint, status, record_count) VALUES
    ('bat_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'Q1 2026 Renewals', 'upload', 'fp_batch_seed01', 'active', 42)
ON CONFLICT DO NOTHING;

-- 2 accounts
INSERT INTO accounts (id, batch_id, workspace_id, account_name, billing_country, billing_city, account_fingerprint) VALUES
    ('acc_SEED0100000000000000000000', 'bat_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'Acme Music Publishing', 'US', 'Nashville', 'fp_acc_seed01'),
    ('acc_SEED0200000000000000000000', 'bat_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'Global Sounds Ltd', 'UK', 'London', 'fp_acc_seed02')
ON CONFLICT DO NOTHING;

-- 2 contracts
INSERT INTO contracts (id, batch_id, account_id, workspace_id, contract_fingerprint, contract_id_source, file_name, status, health_score) VALUES
    ('ctr_SEED0100000000000000000000', 'bat_SEED0100000000000000000000', 'acc_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'fp_ctr_seed01', 'extracted', 'acme_renewal_2026.pdf', 'active', 85),
    ('ctr_SEED0200000000000000000000', 'bat_SEED0100000000000000000000', 'acc_SEED0200000000000000000000', 'ws_SEED0100000000000000000000', 'fp_ctr_seed02', 'url_hash', 'global_sounds_master.pdf', 'active', 72)
ON CONFLICT DO NOTHING;

-- 3 documents
INSERT INTO documents (id, contract_id, batch_id, workspace_id, document_fingerprint, file_name, section_name) VALUES
    ('doc_SEED0100000000000000000000', 'ctr_SEED0100000000000000000000', 'bat_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'fp_doc_seed01', 'acme_renewal_2026.pdf', 'Main Agreement'),
    ('doc_SEED0200000000000000000000', 'ctr_SEED0100000000000000000000', 'bat_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'fp_doc_seed02', 'acme_amendment_1.pdf', 'Amendment 1'),
    ('doc_SEED0300000000000000000000', 'ctr_SEED0200000000000000000000', 'bat_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'fp_doc_seed03', 'global_sounds_master.pdf', 'Master Agreement')
ON CONFLICT DO NOTHING;

-- 2 patches (Draft and Submitted)
INSERT INTO patches (id, workspace_id, batch_id, record_id, field_key, author_id, status, intent, because_clause, before_value, after_value, history) VALUES
    ('pat_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'bat_SEED0100000000000000000000', 'rec_001', 'billing_country', 'usr_SEED0100000000000000000000', 'Draft', 'correct', 'Country code mismatch in source data', 'USA', 'US', '[]'::jsonb),
    ('pat_SEED0200000000000000000000', 'ws_SEED0100000000000000000000', 'bat_SEED0100000000000000000000', 'rec_002', 'account_name', 'usr_SEED0100000000000000000000', 'Submitted', 'correct', 'Standardize entity name', 'Global Sounds Limited', 'Global Sounds Ltd', '[{"from_status":"Draft","to_status":"Submitted","actor_id":"usr_SEED0100000000000000000000","timestamp":"2026-01-15T10:00:00Z"}]'::jsonb)
ON CONFLICT DO NOTHING;

-- Update submitted_at for the submitted patch
UPDATE patches SET submitted_at = '2026-01-15T10:00:00Z' WHERE id = 'pat_SEED0200000000000000000000' AND submitted_at IS NULL;

-- 1 evidence pack
INSERT INTO evidence_packs (id, patch_id, workspace_id, author_id, blocks, status) VALUES
    ('evp_SEED0100000000000000000000', 'pat_SEED0200000000000000000000', 'ws_SEED0100000000000000000000', 'usr_SEED0100000000000000000000',
     '[{"type":"context","content":"Source file shows Limited not Ltd"},{"type":"rationale","content":"Standardizing to abbreviated form per company registry"}]'::jsonb,
     'complete')
ON CONFLICT DO NOTHING;

-- 2 triage items
INSERT INTO triage_items (id, workspace_id, batch_id, record_id, field_key, issue_type, severity, source, status) VALUES
    ('tri_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'bat_SEED0100000000000000000000', 'rec_003', 'billing_city', 'missing_value', 'warning', 'qa_rule', 'open'),
    ('tri_SEED0200000000000000000000', 'ws_SEED0100000000000000000000', 'bat_SEED0100000000000000000000', 'rec_004', 'contract_id', 'duplicate_detected', 'blocker', 'preflight', 'open')
ON CONFLICT DO NOTHING;

-- 1 API key (plaintext value: test_api_key_for_smoke_tests_only)
INSERT INTO api_keys (key_id, workspace_id, key_hash, key_prefix, scopes, created_by) VALUES
    ('apk_SEED0100000000000000000000', 'ws_SEED0100000000000000000000',
     '85753cb8b84efede6fb1419b161a8084e6758b6a6faaaa69ab0bf3e6957bf99a',
     'test_api', '["read", "write"]'::jsonb, 'usr_SEED0300000000000000000000')
ON CONFLICT DO NOTHING;

-- 2 signals
INSERT INTO signals (id, workspace_id, batch_id, record_id, field_key, signal_type, severity, rule_id, message) VALUES
    ('sig_SEED0100000000000000000000', 'ws_SEED0100000000000000000000', 'bat_SEED0100000000000000000000', 'rec_001', 'billing_country', 'format_mismatch', 'warning', 'QA_COUNTRY_ISO', 'Country code does not match ISO 3166-1 alpha-2'),
    ('sig_SEED0200000000000000000000', 'ws_SEED0100000000000000000000', 'bat_SEED0100000000000000000000', 'rec_005', 'amount', 'outlier', 'info', 'QA_AMOUNT_RANGE', 'Value exceeds 2 standard deviations from batch mean')
ON CONFLICT DO NOTHING;
