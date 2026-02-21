# 05 — Operator + Validator SOP

## Intended Audience
Operators and Verifiers performing day-to-day governance actions on rules.

## Purpose
Provide a deterministic, step-by-step procedure to propose, validate, preview, smoke-test, and review configuration changes.

## Outline
- Preparation
  - Read docs/INDEX.md and relevant governance docs
  - Confirm use of canonical fields and contract sections
- Drafting a Rule
  - State intent in plain English (WHEN/THEN)
  - Choose severity aligned with risk
- Patch Authoring
  - Use config_pack.patch.json changes[] format (add_rule, deprecate_rule)
  - Reference base_version exactly (must equal base.version)
- Validation & Preview
  - Run validate_config.py (shape + conflicts)
  - Run run_local.py (offline, deterministic) if needed for quick checks
- Smoke Gate (Required Before PR)
  - Run strict smoke test:
    ```
    bash scripts/replit_smoke.sh
    ```
    - Pass criteria: exit 0 and message "OK: preview output matches expected (normalized)."
    - On diff (exit 1): either fix determinism/schema in local_runner or update examples/expected_outputs and append a CHANGELOG entry with rationale, then re-run until strict pass.
    - Do not use `--allow-diff` for PRs (exploratory only).
  - Evidence to attach in PR:
    - Paste the final smoke log snippet showing strict pass, or
    - Reference an updated baseline hash in docs/replit_baseline.md (only when outputs intentionally change) plus a CHANGELOG entry.
- Review & Versioning
  - Use docs/REVIEW_CHECKLIST.md
  - Update CHANGELOG.md upon approval (why, not just what)
- Join Strategy Reminder
  - contract_key → file_url → file_name; no fabrication; surface join failures as issues
