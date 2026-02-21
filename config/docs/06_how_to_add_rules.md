# 06 — How to Add Rules (Governance Patch Format)

## Intended Audience
Analysts and Operators authoring or modifying rules.

## Purpose
Describe how to encode rule intent in the patch format so it can be validated and previewed offline.

## Outline
- Rule Intent
  - "When I see X, I expect Y" (plain English)
- Patch Structure (High Level)
  - base_version must equal base.version
  - changes[] entries: add_rule, deprecate_rule
- Rule Schema
  - rule_id, description, when{sheet, field, operator, value?}, then[action, sheet, field, severity, proposed_value?]
- Severity Guidance
  - info, warning, blocking; pick the lowest that protects quality
- Conflict Awareness
  - Avoid contradictory actions on same WHEN/target
  - Use validator to detect conflicts
- Determinism & Joins
  - Rules must respect canonical fields and join strategy
- Documentation
  - Update CHANGELOG.md with why the change is needed
