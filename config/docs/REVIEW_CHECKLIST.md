# REVIEW_CHECKLIST

Use this checklist before approving any Patch Request. All items must be satisfied.

## Intent Clarity
- [ ] Plain-English description states the situation (Observation) and the expectation (Expected)
- [ ] Authoring aliases are understood: WHEN→Observation, THEN→Expected, BECAUSE→Justification
- [ ] rule_id follows naming conventions and is descriptive
- [ ] Scope boundaries are explicit (what is included and excluded)

## Schema Correctness
- [ ] Canonical contract section and field names (no deprecated aliases)
- [ ] Valid operators/actions for the data type
- [ ] Required attributes present (e.g., severity when applicable)
- [ ] Patch base_version matches the current canonical base

## Preview Validity (Offline Only)
- [ ] Preview uses repository examples (no external data, no network)
- [ ] Results are deterministic for the same inputs
- [ ] Triggered records and outcomes are understandable and expected
- [ ] Joins respect strategy: primary contract_key; fallback file_url; last resort file_name

## Conflict Assessment
- [ ] Validator reports no contradictory actions on the same target
- [ ] Severity levels are consistent with risk and workload
- [ ] Overlaps are resolved via exclusions or refined conditions

## Downstream Risk Awareness
- [ ] Operator workflow impact is described
- [ ] Transition or migration notes are included if needed
- [ ] Interactions with QA expectations and subtype/schema assumptions are acknowledged

## Smoke (Strict) Verification (Required)
- [ ] Strict smoke test passed without `--allow-diff`:
  ```
  bash scripts/replit_smoke.sh
  ```
  - Exit code 0 and message "OK: preview output matches expected (normalized)."
- [ ] Evidence attached:
  - Log snippet showing Smoke (Strict) pass, or
  - Reference to docs/replit_baseline.md with recorded SHA256 (only if outputs intentionally changed) AND a corresponding CHANGELOG entry explaining why.

## Versioning and Changelog
- [ ] Version increment included and consistent
- [ ] Changelog explains why, not just what changed
- [ ] Changelog references examples used in preview/smoke
- [ ] Related documentation updates are linked or included

## Evidence Pack Verification
- [ ] All 4 canonical blocks populated:
  - **Observation** (alias: WHEN) — What situation was observed
  - **Expected** (alias: THEN) — What behavior is expected
  - **Justification** (alias: BECAUSE) — Why this change is correct
  - **Repro** (no alias) — Steps to reproduce

## Approval Decision
- [ ] Approve (Patch Request meets all checks; becomes Approved Patch)
- [ ] Hold (needs clarifications or more examples)
- [ ] Reject (conflicts or risks not resolved)

Verifier:
- Name: ______________________  Date: ____________
- Notes: ____________________________________________________________

---

## Consistency Checks

Before finalizing any documentation changes, verify consistency across these authoritative files:

- [ ] `docs/INDEX.md` — links and section headings
- [ ] `docs/ui/ui_principles.md` — Canonical Language Rule, transition matrix
- [ ] `docs/ui/gate_view_mapping.md` — view names and gate labels
- [ ] `docs/AUDIT_LOG.md` — view examples and event origins
- [ ] `docs/overview.md` — Canonical Terms appendix
