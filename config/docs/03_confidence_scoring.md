# 03 — Confidence Scoring (Concept Outline)

## Intended Audience
Operators and Verifiers who need a stable, human-readable approach to interpreting preview confidence and status.

## Purpose
Define a conceptual approach to confidence and status mapping for preview results without prescribing runtime implementation.

## Outline
- Determinism First
  - Scores and statuses in preview must be reproducible given the same inputs
- Signals (Conceptual)
  - Field presence vs. blanks
  - Consistency with subtype expectations
  - QA indications of content quality (conceptual reference only)
- Status Mapping (Preview)
  - READY: rules satisfied; no blocking/warning conditions
  - NEEDS_REVIEW: warnings present; operator should confirm
  - BLOCKED: blocking issues (e.g., failed joins, critical violations)
- Transparency
  - Show which fields and rules contributed to the outcome
  - Keep outputs stable and audit-friendly
