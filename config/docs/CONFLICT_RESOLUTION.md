# CONFLICT_RESOLUTION

## Purpose
Define how conflicting rules are identified, evaluated, and resolved through explicit human judgment that is documented and auditable.

## Types of Conflicts
- Field-level conflict: Multiple rules target the same field with incompatible outcomes (e.g., REQUIRE_BLANK vs SET_VALUE).
- Rule-order conflict: Outcomes depend on evaluation order, leading to unstable or contradictory results.
- Severity mismatch: Overlapping rules assign different severities to the same condition (e.g., warning vs blocking).
- Scope overlap: Broad conditions unintentionally capture the same records as a narrower rule.
- Deprecation drift: A patch modifies a rule that is already deprecated, without acknowledging deprecation.

## Conflict Detection (Validator Expectations)
- Unique rule_id and clear description
- Canonical contract section/field names and valid operators/actions
- Overlap analysis for WHEN conditions on the same targets
- Contradiction analysis for THEN actions on the same targets
- Severity coherence checks across overlapping scenarios
- Base/version compatibility between patch and canonical state

## Decision Process (Operators + Verifiers)
- Clarify intent: Compare stated intent, examples, and rationale for each rule.
- Prefer precision: Favor narrower, well-scoped rules over broad patterns when both address the same issue.
- Prefer safety: When uncertain, select outcomes that minimize incorrect downstream population.
- Harmonize severity: Pick a single severity consistent with risk and operator workload.
- Re-scope as needed: Add exclusions or refine WHEN conditions to remove unintended overlap.
- Document the decision: Record reasoning, examples, and final changes in the changelog.

## Why Conflicts Are Never Auto-Resolved
- Human judgment preserves meaning and auditability.
- Auto-resolution can hide errors and undermine determinism.
- Explicit decisions ensure stable, explainable outcomes.

## Resolution Outcomes
- Accept one rule; remove or withdraw conflicting rules
- Merge rules into a single, clearer rule with consistent severity
- Defer pending more examples or clearer intent
- Quarantine a rule as draft until evidence is sufficient
- Explicitly deprecate a superseded rule

## Documentation Requirements
- Assign a conflict reference ID
- List the conflicting rules, their intents, and example records
- Record the selected outcome and rationale
- Update the patch and rerun offline preview
- Add a changelog entry linking to the decision
