# 04 — Subtype–Schema Matrix (Canonical Expectations)

## Intended Audience
Operators and Analysts determining which fields should exist for each subtype.

## Purpose
Outline how subtypes map to canonical contract section fields so expectations are explicit and stable for rule authoring and preview.

## Outline
- Canonical Contract Sections (Examples)
  - accounts, catalog, contacts, opportunity, financials, schedule
- Field Expectations (Conceptual)
  - Required vs. recommended fields per contract section
  - Anchors preserved: file_name, file_url where applicable
- Subtype Alignment
  - Example: record_label vs. artist affects expectations for artist_name
- Governance Notes
  - Changes to subtype–schema mapping are handled via config patches and changelog entries
- Determinism & Joins
  - Align field usage with join strategy: contract_key → file_url → file_name
