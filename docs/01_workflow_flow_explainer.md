# 01 — Workflow Flow Explainer (Conceptual)

## Intended Audience
Operators and Reviewers needing a conceptual map of how semantic artifacts align with the broader pipeline.

## Purpose
Describe, at a conceptual level, the sequence of semantic stages and handoffs that the control board anticipates. This document does not specify runtime logic; it clarifies where semantics matter and how artifacts relate.

## Outline
- Scope Lock
  - Governance-only; offline; no execution systems
- Conceptual Stage Order (from current ground truth)
  - Orchestrator → Loader → Packager → Standardizer → Resolver → Extractor → QA → Salesforce Rules → A&R → Review
- Where Semantics Apply
  - Standardizer: canonical sheets/headers
  - QA: quality signals and statuses
  - Salesforce Rules: field requirements and formatting actions
- Artifacts & Handoffs
  - standardized_dataset (sheeted)
  - contract_anchors (concept only)
  - sf_packet (preview for governance)
- Debug/Review Aids
  - Expect debug sections (e.g., loader/packager/standardizer/resolver) in envelopes conceptually
- Join Strategy Enforcement
  - contract_key → file_url → file_name
  - No silent joins; unmatched cases must surface as issues
- Determinism
  - All previews are offline and repeatable
