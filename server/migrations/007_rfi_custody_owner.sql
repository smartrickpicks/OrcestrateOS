-- Migration 007: Add custody owner tracking to rfis
-- Feature: Evidence Inspector v2.51 Phase 3 (RFI Custody + Corrections)
-- Rollback: ALTER TABLE rfis DROP COLUMN IF EXISTS custody_owner_id;
--           ALTER TABLE rfis DROP COLUMN IF EXISTS custody_owner_role;

ALTER TABLE rfis ADD COLUMN IF NOT EXISTS custody_owner_id TEXT;
ALTER TABLE rfis ADD COLUMN IF NOT EXISTS custody_owner_role TEXT;

UPDATE rfis SET custody_owner_role = CASE
    WHEN custody_status IN ('open', 'returned_to_analyst') THEN 'analyst'
    WHEN custody_status IN ('awaiting_verifier') THEN 'verifier'
    WHEN custody_status IN ('resolved', 'dismissed') THEN NULL
    ELSE 'analyst'
END
WHERE custody_owner_role IS NULL AND custody_status IS NOT NULL;

UPDATE rfis SET custody_owner_id = author_id
WHERE custody_owner_id IS NULL AND custody_owner_role = 'analyst';
